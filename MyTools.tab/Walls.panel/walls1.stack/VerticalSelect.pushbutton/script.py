"""Select nearby walls by overlap with the original wall's vertical footprint."""

import math
import traceback

from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List


__title__ = "Vertical Select"
__author__ = "Adam Shaw"

# Revit lengths are in feet. Angle tolerance is independent of wall direction.
MAX_VERTICAL_GAP = 1000.0 / 304.8
PARALLEL_TOLERANCE_DEGREES = 0.1
MIN_VOLUME_FRACTION = 0.10
EXTRUSION_PADDING = 1.0 / 304.8
LENGTH_EPSILON = 1e-9
VOLUME_EPSILON = 1e-9
NORMAL_TOLERANCE = 1e-6


def get_straight_direction(wall):
    """Return a straight location curve's unit direction in XY, else None."""
    location = wall.Location
    if not isinstance(location, DB.LocationCurve):
        return None
    curve = location.Curve
    if not isinstance(curve, DB.Line):
        return None
    direction = curve.Direction
    length = math.hypot(direction.X, direction.Y)
    if length <= LENGTH_EPSILON:
        raise ValueError("Straight wall has no usable direction in plan.")
    return direction.X / length, direction.Y / length


def directions_match(reference, candidate):
    """Check parallelism only for straight pairs; ignore endpoint direction."""
    if reference is None or candidate is None:
        return True
    cross = reference[0] * candidate[1] - reference[1] * candidate[0]
    dot = reference[0] * candidate[0] + reference[1] * candidate[1]
    angle = math.atan2(abs(cross), abs(dot))
    return angle <= math.radians(PARALLEL_TOLERANCE_DEGREES) + 1e-12


def vertical_gap(reference_box, candidate_box):
    """Return the Z interval gap; touching or overlapping boxes have zero gap."""
    return max(
        0.0,
        candidate_box.Min.Z - reference_box.Max.Z,
        reference_box.Min.Z - candidate_box.Max.Z,
    )


def boxes_overlap_xy(first, second):
    """Cheap rejection before extracting candidate solids."""
    return not (
        first.Max.X <= second.Min.X + LENGTH_EPSILON
        or second.Max.X <= first.Min.X + LENGTH_EPSILON
        or first.Max.Y <= second.Min.Y + LENGTH_EPSILON
        or second.Max.Y <= first.Min.Y + LENGTH_EPSILON
    )


def get_model_solids(element):
    """Extract positive-volume solids in model coordinates, including instances."""
    options = DB.Options()
    options.DetailLevel = DB.ViewDetailLevel.Fine
    solids = []

    def collect(geometry, transform):
        if geometry is None:
            return
        for item in geometry:
            if isinstance(item, DB.Solid):
                if abs(item.Volume) > VOLUME_EPSILON:
                    solids.append(DB.SolidUtils.CreateTransformed(item, transform))
            elif isinstance(item, DB.GeometryInstance):
                collect(
                    item.GetSymbolGeometry(),
                    transform.Multiply(item.Transform),
                )

    collect(element.get_Geometry(options), DB.Transform.Identity)
    if not solids:
        raise ValueError("Wall has no measurable solid geometry.")
    return solids


def check_vertical_curved_face(face):
    """Reject nonvertical curved reference faces rather than guess a footprint."""
    mesh = face.Triangulate()
    for index in range(mesh.NumTriangles):
        triangle = mesh.get_Triangle(index)
        first = triangle.get_Vertex(0)
        normal = (triangle.get_Vertex(1) - first).CrossProduct(
            triangle.get_Vertex(2) - first
        )
        if abs(normal.Z) > NORMAL_TOLERANCE * normal.GetLength():
            raise ValueError(
                "The selected wall has nonvertical curved faces. "
                "Only planar underside faces and vertical curved faces "
                "are supported for the reference footprint."
            )


def create_reference_prism(solids, reference_box, bottom_z, top_z):
    """Union underside extrusions, with all end caps beyond candidate heights."""
    # Keep the native planar loops, including arcs/splines and inner holes.
    # Lower even the highest underside below every candidate before extrusion.
    offset = bottom_z - reference_box.Max.Z - EXTRUSION_PADDING
    height = (
        top_z - bottom_z
        + reference_box.Max.Z - reference_box.Min.Z
        + 2.0 * EXTRUSION_PADDING
    )
    translation = DB.Transform.CreateTranslation(DB.XYZ(0, 0, offset))
    prism = None
    for solid in solids:
        for face in solid.Faces:
            if not isinstance(face, DB.PlanarFace):
                check_vertical_curved_face(face)
                continue
            if face.FaceNormal.Z >= -NORMAL_TOLERANCE:
                continue
            loops = List[DB.CurveLoop]()
            for loop in face.GetEdgesAsCurveLoops():
                loops.Add(DB.CurveLoop.CreateViaTransform(loop, translation))
            extrusion = DB.GeometryCreationUtilities.CreateExtrusionGeometry(
                loops, DB.XYZ.BasisZ, height
            )
            if prism is None:
                prism = extrusion
            else:
                # Overlapping underside projections must not count twice.
                prism = DB.BooleanOperationsUtils.ExecuteBooleanOperation(
                    prism, extrusion, DB.BooleanOperationsType.Union
                )
    if prism is None:
        raise ValueError("The selected wall has no usable planar underside faces.")
    return prism


def has_volume_overlap(prism, candidate_solids):
    """More than 10% of the candidate's complete solid volume must intersect."""
    candidate_volume = sum(abs(solid.Volume) for solid in candidate_solids)
    if candidate_volume <= VOLUME_EPSILON:
        raise ValueError("Candidate wall has no measurable solid volume.")
    intersection_volume = 0.0
    for solid in candidate_solids:
        intersection = DB.BooleanOperationsUtils.ExecuteBooleanOperation(
            prism, solid, DB.BooleanOperationsType.Intersect
        )
        intersection_volume += abs(intersection.Volume)
    return intersection_volume / candidate_volume > MIN_VOLUME_FRACTION + 1e-9


def main():
    uidoc = revit.uidoc
    doc = uidoc.Document
    selected_ids = list(uidoc.Selection.GetElementIds())
    if len(selected_ids) != 1:
        forms.alert("Please select exactly one wall first.")
        return

    reference_wall = doc.GetElement(selected_ids[0])
    if not isinstance(reference_wall, DB.Wall):
        forms.alert("Please select exactly one wall first.")
        return

    logger = script.get_logger()
    try:
        reference_box = reference_wall.get_BoundingBox(None)
        if reference_box is None:
            raise ValueError("The selected wall has no model bounding box.")
        reference_direction = get_straight_direction(reference_wall)
    except Exception as error:
        logger.error(
            "Wall %s: reading reference bounds/direction failed.\n%s",
            reference_wall.Id, traceback.format_exc(),
        )
        forms.alert("Could not read the selected wall.\n\n{}".format(error))
        return

    matching_ids = List[DB.ElementId]()
    matching_ids.Add(reference_wall.Id)
    candidates = []
    failed_ids = []
    walls = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.Wall)
        .WhereElementIsNotElementType()
    )
    for wall in walls:
        if wall.Id == reference_wall.Id:
            continue
        try:
            candidate_box = wall.get_BoundingBox(None)
            if candidate_box is None:
                raise ValueError("Wall has no model bounding box.")
            # Fixed original bounds: neither bigger nor taller matches extend it.
            if vertical_gap(reference_box, candidate_box) > MAX_VERTICAL_GAP + LENGTH_EPSILON:
                continue
            if not boxes_overlap_xy(reference_box, candidate_box):
                continue
            if not directions_match(reference_direction, get_straight_direction(wall)):
                continue
            candidates.append((wall, candidate_box))
        except Exception:
            failed_ids.append(wall.Id)
            logger.warning(
                "Wall %s: candidate bounds/direction check failed; not selected.\n%s",
                wall.Id, traceback.format_exc(),
            )

    if candidates:
        try:
            # Extending the temporary solid covers complete candidate volumes;
            # eligibility still uses only the original wall's bounds above.
            bottom_z = min(box.Min.Z for wall, box in candidates)
            top_z = max(box.Max.Z for wall, box in candidates)
            prism = create_reference_prism(
                get_model_solids(reference_wall), reference_box, bottom_z, top_z
            )
        except Exception as error:
            logger.error(
                "Wall %s: reference footprint extrusion failed; selection unchanged.\n%s",
                reference_wall.Id, traceback.format_exc(),
            )
            forms.alert(
                "Could not build the selected wall's vertical footprint. "
                "Selection has not changed.\n\n{}".format(error)
            )
            return

        for wall, candidate_box in candidates:
            try:
                if has_volume_overlap(prism, get_model_solids(wall)):
                    matching_ids.Add(wall.Id)
            except Exception:
                failed_ids.append(wall.Id)
                logger.warning(
                    "Wall %s against reference wall %s: solid extraction/intersection "
                    "failed; not selected.\n%s",
                    wall.Id, reference_wall.Id, traceback.format_exc(),
                )

    uidoc.Selection.SetElementIds(matching_ids)
    if failed_ids:
        forms.alert(
            "Selection is incomplete: {} wall(s) could not be evaluated and "
            "were left out. Other matching walls and the original wall are "
            "selected. See the pyRevit output for wall IDs and error details."
            .format(len(failed_ids))
        )


if __name__ == "__main__":
    main()
