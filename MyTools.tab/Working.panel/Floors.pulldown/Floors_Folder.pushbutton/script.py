# -*- coding: utf-8 -*-
"""
Create folds for all selected floors that overlap

Usage:
1. Select all the non-fold floors to process.
2. Run the script.
"""

from System.Collections.Generic import List

from pyrevit import DB, forms, revit
from pyrevit.revit.db import query
from revitfunctions.basics import mm_to_feet, feet_to_mm


__title__ = "Folder"
__author__ = "Adam Shaw"


doc = revit.doc

PROXY_HEIGHT = 1.0
TOLERANCE = 1e-9


class ContinueFailuresPreprocessor(DB.IFailuresPreprocessor):
    def PreprocessFailures(self, failures_accessor):
        return DB.FailureProcessingResult.Continue


def get_selected_floors():
    floors = []
    for element_id in revit.uidoc.Selection.GetElementIds():
        element = doc.GetElement(element_id)
        if isinstance(element, DB.Floor):
            floors.append(element)

    if len(floors) < 2:
        forms.alert(
            "Select at least two floors",
            exitscript=True
        )

    return floors


def get_floor_extents(floor):
    top_z = floor.get_Parameter(
        DB.BuiltInParameter.STRUCTURAL_ELEVATION_AT_TOP
    ).AsDouble()

    bottom_z = floor.get_Parameter(
        DB.BuiltInParameter.STRUCTURAL_ELEVATION_AT_BOTTOM
    ).AsDouble()

    return top_z, bottom_z


def get_flat_sketch_loops(floor):
    sketch = doc.GetElement(floor.SketchId)

    first_curve = next(
        curve
        for curve_array in sketch.Profile
        for curve in curve_array
    )

    sketch_z = first_curve.GetEndPoint(0).Z

    transform = DB.Transform.CreateTranslation(
        DB.XYZ(0, 0, -sketch_z)
    )

    loops = List[DB.CurveLoop]()

    for curve_array in sketch.Profile:
        loop = DB.CurveLoop()

        for curve in curve_array:
            loop.Append(
                curve.CreateTransformed(transform)
            )

        loops.Add(loop)

    return loops


def create_proxy_solid(floor):
    return DB.GeometryCreationUtilities.CreateExtrusionGeometry(
        get_flat_sketch_loops(floor),
        DB.XYZ.BasisZ,
        PROXY_HEIGHT
    )


def execute_boolean(first_solid, second_solid, operation_type):
    return DB.BooleanOperationsUtils.ExecuteBooleanOperation(
        first_solid,
        second_solid,
        operation_type
    )


def bounding_boxes_overlap_xy(first_solid, second_solid):
    first_box = first_solid.GetBoundingBox()
    second_box = second_solid.GetBoundingBox()

    return not (
        first_box.Max.X <= second_box.Min.X + TOLERANCE
        or second_box.Max.X <= first_box.Min.X + TOLERANCE
        or first_box.Max.Y <= second_box.Min.Y + TOLERANCE
        or second_box.Max.Y <= first_box.Min.Y + TOLERANCE
    )


def get_volume_intersection(first_solid, second_solid):
    if not bounding_boxes_overlap_xy(first_solid, second_solid):
        return None

    try:
        intersection = execute_boolean(
            first_solid,
            second_solid,
            DB.BooleanOperationsType.Intersect
        )
        if intersection.Volume > TOLERANCE:
            return intersection
    except Exception:
        pass

    return None


def get_proxy_profile(solid):
    for face in solid.Faces:
        if (
            isinstance(face, DB.PlanarFace)
            and face.FaceNormal.Z < -0.999999
        ):
            loops = List[DB.CurveLoop]()

            for loop in face.GetEdgesAsCurveLoops():
                loops.Add(loop)

            return loops

    return None


def get_result_profiles(result_solid):
    profiles = []

    for solid in DB.SolidUtils.SplitVolumes(result_solid):
        if solid.Volume <= TOLERANCE:
            continue

        profile = get_proxy_profile(solid)

        if profile:
            profiles.append(profile)

    return profiles


def get_sketch_z(sketch):
    first_curve = next(
        curve
        for curve_array in sketch.Profile
        for curve in curve_array
    )

    return first_curve.GetEndPoint(0).Z


def get_transformed_result_loops(result_proxies, sketch_z):
    transform = DB.Transform.CreateTranslation(
        DB.XYZ(0, 0, sketch_z)
    )
    transformed_loops = List[DB.CurveLoop]()

    for proxy in result_proxies:
        for profile in get_result_profiles(proxy["solid"]):
            for loop in profile:
                transformed_loop = DB.CurveLoop()

                for curve in loop:
                    transformed_loop.Append(
                        curve.CreateTransformed(transform)
                    )

                transformed_loops.Add(transformed_loop)

    return transformed_loops


def get_profile_element_ids(sketch):
    element_ids = List[DB.ElementId]()

    for curve_array in sketch.Profile:
        for curve in curve_array:
            element_id = curve.Reference.ElementId

            if not any(
                existing_id == element_id
                for existing_id in element_ids
            ):
                element_ids.Add(element_id)

    return element_ids


def update_original_floor_sketch(floor, result_proxies):
    sketch = doc.GetElement(floor.SketchId)
    sketch_z = get_sketch_z(sketch)
    structural_parameter = floor.get_Parameter(
        DB.BuiltInParameter.FLOOR_PARAM_IS_STRUCTURAL
    )
    is_structural = (
        structural_parameter
        and structural_parameter.AsInteger() == 1
    )

    result_loops = get_transformed_result_loops(
        result_proxies,
        sketch_z
    )

    if result_loops.Count == 0:
        raise Exception(
            "No valid remainder profile was found for floor {}.".format(
                floor.Id
            )
        )

    if not DB.BoundaryValidation.IsValidBoundaryOnSketchPlane(
        sketch.SketchPlane,
        result_loops
    ):
        raise Exception(
            "The remainder profile is not a valid sketch for floor {}.".format(
                floor.Id
            )
        )

    edit_scope = DB.SketchEditScope(
        doc,
        "Update Original Floor Sketch"
    )
    elements_to_delete = get_profile_element_ids(sketch)

    try:
        edit_scope.Start(sketch.Id)

        if is_structural:
            with revit.Transaction("Prepare Floor Span Direction"):
                floor.SpanDirectionAngle = (
                    floor.SpanDirectionAngle + 1.0
                )
                doc.Regenerate()

        with revit.Transaction("Replace Original Floor Boundary"):
            if elements_to_delete.Count > 0:
                doc.Delete(elements_to_delete)

            for loop in result_loops:
                for curve in loop:
                    doc.Create.NewModelCurve(
                        curve,
                        sketch.SketchPlane
                    )

        if is_structural:
            with revit.Transaction("Set Horizontal Floor Span Direction"):
                floor.SpanDirectionAngle = 0.0
                doc.Regenerate()

        edit_scope.Commit(
            ContinueFailuresPreprocessor()
        )
    except Exception:
        if edit_scope.IsActive:
            edit_scope.Cancel()
        raise
    finally:
        edit_scope.Dispose()


def duplicate_fold_floor_type(creation_data, new_thickness, type_cache):
    floor_type = creation_data["floor_type"]
    new_floor_name = "{}_SLAB-FOLD_HERA".format(
        format(new_thickness, ".0f")
    )

    if new_floor_name in type_cache:
        return type_cache[new_floor_name]

    existing_types = query.get_family_symbol("Floor", new_floor_name)

    if existing_types:
        type_cache[new_floor_name] = existing_types[0]
        return type_cache[new_floor_name]

    new_floor_type = floor_type.Duplicate(
        new_floor_name
    )

    compound = new_floor_type.GetCompoundStructure()

    compound.SetLayerWidth(
        0,
        mm_to_feet(new_thickness)
    )

    new_floor_type.SetCompoundStructure(
        compound
    )

    type_cache[new_floor_name] = new_floor_type
    return type_cache[new_floor_name]


def create_floors_from_result(
    result_solid,
    creation_data,
    top_z,
    bottom_z,
    type_cache
):
    thickness_mm = feet_to_mm(top_z - bottom_z)
    new_type = duplicate_fold_floor_type(
        creation_data,
        thickness_mm,
        type_cache
    )

    level = doc.GetElement(creation_data["level_id"])
    offset = top_z - level.Elevation
    is_structural = creation_data["is_structural"]

    new_floors = []

    for solid in DB.SolidUtils.SplitVolumes(result_solid):
        if solid.Volume <= TOLERANCE:
            continue

        profile = get_proxy_profile(solid)

        if not profile:
            continue

        new_floor = DB.Floor.Create(
            doc,
            profile,
            new_type.Id,
            level.Id,
            is_structural,
            None,
            0.0
        )

        new_floor.get_Parameter(
            DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM
        ).Set(offset)

        new_floors.append(new_floor)

    return new_floors


def make_union_proxy(first_proxy, second_proxy, intersection):
    top_z = max(first_proxy["top_z"], second_proxy["top_z"])
    bottom_z = min(
        first_proxy["bottom_z"],
        second_proxy["bottom_z"]
    )
    return {
        "solid": intersection,
        "creation_data": first_proxy["creation_data"],
        "original_floor_id": None,
        "needs_sketch_update": True,
        "top_z": top_z,
        "bottom_z": bottom_z,
    }


def subtract_union_from_sources(union_proxy, first_proxy, second_proxy):
    remaining = []

    for source_proxy in (first_proxy, second_proxy):
        remainder = execute_boolean(
            source_proxy["solid"],
            union_proxy["solid"],
            DB.BooleanOperationsType.Difference
        )

        if remainder.Volume > TOLERANCE:
            remaining.append({
                "solid": remainder,
                "creation_data": source_proxy["creation_data"],
                "original_floor_id": source_proxy["original_floor_id"],
                "needs_sketch_update": True,
                "top_z": source_proxy["top_z"],
                "bottom_z": source_proxy["bottom_z"],
            })

    return remaining


def get_floor_creation_data(floor):
    structural_param = floor.get_Parameter(
        DB.BuiltInParameter.FLOOR_PARAM_IS_STRUCTURAL
    )

    return {
        "floor_type": floor.FloorType,
        "level_id": floor.LevelId,
        "is_structural": structural_param and structural_param.AsInteger() == 1,
    }


def process_floor_proxies(floors):
    proxies = []

    for floor in floors:
        top_z, bottom_z = get_floor_extents(floor)
        proxies.append({
            "solid": create_proxy_solid(floor),
            "creation_data": get_floor_creation_data(floor),
            "original_floor_id": floor.Id,
            "needs_sketch_update": False,
            "top_z": top_z,
            "bottom_z": bottom_z,
        })

    index = 0
    while index < len(proxies):
        first_proxy = proxies[index]
        compare_index = index + 1

        while compare_index < len(proxies):
            second_proxy = proxies[compare_index]

            intersection = get_volume_intersection(
                first_proxy["solid"],
                second_proxy["solid"]
            )

            if intersection:
                union_proxy = make_union_proxy(
                    first_proxy,
                    second_proxy,
                    intersection
                )

                if not union_proxy:
                    compare_index += 1
                    continue

                proxies.pop(compare_index)
                proxies.pop(index)
                proxies[index:index] = (
                    subtract_union_from_sources(
                        union_proxy,
                        first_proxy,
                        second_proxy
                    )
                    + [union_proxy]
                )
                index = 0
                break

            compare_index += 1
        else:
            index += 1

    return proxies


def group_result_proxies(proxies):
    original_results = {}
    new_results = []

    for proxy in proxies:
        original_floor_id = proxy["original_floor_id"]

        if original_floor_id is None:
            new_results.append(proxy)
        else:
            if original_floor_id not in original_results:
                original_results[original_floor_id] = []

            original_results[original_floor_id].append(proxy)

    return original_results, new_results


def main():
    floors = get_selected_floors()
    proxies = process_floor_proxies(floors)
    original_results, new_results = group_result_proxies(proxies)

    with revit.TransactionGroup("Create Floor Boolean Result"):
        for floor in floors:
            result_proxies = original_results.get(floor.Id, [])

            if (
                result_proxies
                and any(
                    proxy["needs_sketch_update"]
                    for proxy in result_proxies
                )
            ):
                update_original_floor_sketch(
                    floor,
                    result_proxies
                )

        with revit.Transaction("Create New Floor Results"):
            type_cache = {}
            new_floors = []

            for proxy in new_results:
                new_floors.extend(create_floors_from_result(
                    proxy["solid"],
                    proxy["creation_data"],
                    proxy["top_z"],
                    proxy["bottom_z"],
                    type_cache
                ))

            consumed_floor_ids = List[DB.ElementId]()

            for floor in floors:
                if floor.Id not in original_results:
                    consumed_floor_ids.Add(floor.Id)

            if consumed_floor_ids.Count > 0:
                doc.Delete(consumed_floor_ids)


if __name__ == "__main__":
    main()
