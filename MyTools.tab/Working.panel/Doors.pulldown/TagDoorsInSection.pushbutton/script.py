"""
Find all door elements in the active section or elevation view, filter out doors not parallel with the view's plane,
tag the parallel doors, and move the tags to 200mm from the top of each door.
"""

from pyrevit import revit, DB, forms

__title__ = "Tag Doors in \'Elevation\'"
__author__ = "Adam Shaw"


def is_door_parallel_to_view(door, view):
    """Check if a door is parallel to the given view's plane."""
    door_normal = door.FacingOrientation.Normalize()
    view_normal = view.ViewDirection.CrossProduct(DB.XYZ.BasisZ).Normalize()
    return abs(door_normal.DotProduct(view_normal)) < 1e-6


def tag_parallel_doors(doors, view):
    """Tag the given doors in the specified view and move the tags."""
    tag_type_id = next((t.Id for t in DB.FilteredElementCollector(revit.doc)
                        .OfCategory(DB.BuiltInCategory.OST_DoorTags)
                        .WhereElementIsElementType()), None)

    if not tag_type_id:
        forms.alert("No door tag types found in the project.")
        return

    with revit.Transaction("Tag Parallel Doors"):
        for door in doors:
            bbox = door.get_BoundingBox(view)
            offset = 250 / 304.8
            door_loc_pt = door.Location.Point
            tag_pt = DB.XYZ(door_loc_pt.X, door_loc_pt.Y, bbox.Max.Z - offset)
            DB.IndependentTag.Create(revit.doc, tag_type_id, view.Id,
                                     DB.Reference(door), False,
                                     DB.TagOrientation.Horizontal, tag_pt)


def main():
    """Main function to execute the script logic."""
    active_view = revit.active_view

    if not isinstance(active_view, DB.ViewSection):
        forms.alert("The active view must be a section or elevation view.")
        return

    doors = [d for d in DB.FilteredElementCollector(revit.doc, active_view.Id)
             .OfCategory(DB.BuiltInCategory.OST_Doors)
             .WhereElementIsNotElementType()
             if is_door_parallel_to_view(d, active_view)]

    if not doors:
        forms.alert("No parallel doors found in the active view.")
        return

    tag_parallel_doors(doors, active_view)


if __name__ == "__main__":
    main()