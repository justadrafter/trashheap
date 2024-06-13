"""
This script groups the CurveArrays in the sketch of selected slab elements based on containment.
Select one or more slab elements and run the script.
The script will process each slab element, group the CurveArrays in its sketch, and display the grouped CurveArrays.
"""

from System.Collections.Generic import List
from pyrevit import revit, DB, forms
from Autodesk.Revit.DB import GeometryCreationUtilities, ElementCategoryFilter, ElementClassFilter, LogicalAndFilter, BuiltInCategory, Sketch, SketchPlane

__title__ = "Split Slabs"
__author__ = "Adam Shaw"

DOC = revit.doc
UIDOC = revit.uidoc


def create_face_from_curve_array(curve_array):
    # Create a curve loop from the curve array
    curve_loop = DB.CurveLoop.Create(curve_array)

    # Create an IList of CurveLoop objects
    curve_loops = List[DB.CurveLoop]()
    curve_loops.Add(curve_loop)

    # Define the extrusion direction and distance
    extrusion_dir = DB.XYZ(0, 0, 1)  # Extrude in the positive Z direction
    extrusion_dist = 10 / 304.8  # 10 mm converted to feet

    solid = None
    with revit.Transaction("Create Extrusion"):
        try:
            # Create a solid by extruding the curve loops
            solid = GeometryCreationUtilities.CreateExtrusionGeometry(
                curve_loops, extrusion_dir, extrusion_dist
            )
        except Exception as ex:
            raise Exception("Failed to create extrusion. " + str(ex))

    bottom_face = None
    z_vector = DB.XYZ(0, 0, -1)

    for face in solid.Faces:
        if face.FaceNormal.IsAlmostEqualTo(z_vector):
            bottom_face = face
            break

    return bottom_face


def validate_selection(selection):
    if not selection:
        forms.alert("Please select at least one slab element.")
        return False
    return True


def get_slab_elements(selection):
    slab_elements = [element for element in selection if isinstance(element, DB.Floor)]
    if not slab_elements:
        forms.alert("No slab elements found in the selection.")
    return slab_elements


def group_curve_arrays_by_containment(slab_element):
    # Retrieve the sketch ID from the slab
    sketch_id = slab_element.SketchId

    # Get the sketch element from the sketch ID
    sketch_element = DOC.GetElement(sketch_id)

    # Get the profile of the sketch
    profile = sketch_element.Profile

    # Create a dictionary to store curve arrays and their corresponding faces
    curve_array_faces = {}

    # Iterate through the curves in the profile
    for curve_array in profile:
        if isinstance(curve_array, DB.CurveArray):
            # Convert the CurveArray to a list of curves
            curves = []
            for curve in curve_array:
                curves.append(curve)

            # Create a face from the list of curves
            face = create_face_from_curve_array(curves)
            curve_array_faces[curve_array] = face

    # Sort the curve arrays based on the area of their faces (largest to smallest)
    sorted_curve_arrays = sorted(
        curve_array_faces.items(), key=lambda x: x[1].Area, reverse=True
    )

    # Create a list to store the grouped curve arrays
    grouped_curve_arrays = []

    # Iterate through the sorted curve arrays, popping off the largest one each time
    while sorted_curve_arrays:
        (current_curve_array, current_face) = sorted_curve_arrays.pop(
            0
        )  # Pop the largest curve array
        current_group = [current_curve_array]  # Start a new group with the largest

        # Iterate through the remaining curve arrays
        i = 0
        while i < len(sorted_curve_arrays):
            (other_curve_array, other_face) = sorted_curve_arrays[i]
            points_on_face = False

            # Check if any points from the other curve array are inside the current face
            for curve in other_curve_array:
                start_point = curve.GetEndPoint(0)
                start_point_2d = DB.XYZ(start_point.X, start_point.Y, 0)
                try:
                    temp_UV = current_face.Project(start_point_2d).UVPoint
                    if current_face.IsInside(temp_UV):
                        points_on_face = True
                    break
                except:
                    continue

            # If points are inside, add to the current group and remove from the sorted list
            if points_on_face:
                current_group.append(other_curve_array)
                sorted_curve_arrays.pop(i)
            else:
                i += 1  # Move to the next curve array if not inside

        grouped_curve_arrays.append(current_group)  # Add the completed group

    return grouped_curve_arrays


def create_floors_from_curve_groups(
    curve_loops, level, floor_type
):  # Added level and floor_type as arguments
    floors = []
    with revit.Transaction("Create Floors"):
        try:
            new_floor = DB.Floor.Create(
                DOC, curve_loops, floor_type, level, True, None, 0.0
            )
            floors.append(new_floor)
        except Exception as ex:
            print("Failed to create floor. " + str(ex))
    return floors


def process_slab_elements(slab_elements):
    deleted_ids = []
    for slab_element in slab_elements:
        # Get level and floor type from each slab element
        level = slab_element.LevelId
        floor_type = slab_element.FloorType.Id

        grouped_curve_arrays = group_curve_arrays_by_containment(slab_element)
        cl_list = []
        for group in grouped_curve_arrays:
            c_list = []
            for curvearr in group:
                templist = []
                for lines in curvearr:
                    templist.append(lines)
                c_list.append(DB.CurveLoop.Create(templist))
            cl_list.append(c_list)
        with revit.Transaction("Deleting Old Floors"):
            deleted_ids.append(DOC.Delete(slab_element.Id))

        for curveloops in cl_list:
            create_floors_from_curve_groups(curveloops, level, floor_type)
    return deleted_ids

def main():
    selection = revit.get_selection()

    # Create filters
    category_filter1 = ElementCategoryFilter(BuiltInCategory.OST_WeakDims, inverted=True)
    category_filter2 = ElementCategoryFilter(BuiltInCategory.OST_SketchLines, inverted=True)
    sketch_filter = ElementClassFilter(Sketch, inverted=True)
    sketch_plane_filter = ElementClassFilter(SketchPlane, inverted=True)

    # Combine filters
    combined_filter = LogicalAndFilter([category_filter1, category_filter2, sketch_filter, sketch_plane_filter])

    try:
        with revit.TransactionGroup("Split Slabs"):
            slab_elements = get_slab_elements(selection)
            for x in slab_elements:
                dependent_elements = x.GetDependentElements(combined_filter)
                for item in [DOC.GetElement(y) for y in dependent_elements]:
                    if item.Name != "":
                        try:
                            print("Deleted: "+item.Name+" ("+item.Category.Name+")         from view: "+ DOC.GetElement(item.OwnerViewId).Name)
                        except:
                            print("Deleted: "+item.Name+" ("+item.Category.Name+")")
            process_slab_elements(slab_elements)

    except Exception as e:
        print("An error occurred:", str(e))


if __name__ == "__main__":
    main()
