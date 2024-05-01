"""
This script creates a floor tag at the selected point on a slab element in the active Revit view.
To use this script, run it and then click on a point on a slab element in the Revit view.
"""

from pyrevit import revit, DB, UI
from Autodesk.Revit import Exceptions

__title__ = "Create Floor Tag at Selected Point (Slab Only)"
__author__ = "Adam Shaw"


class SlabSelectionFilter(UI.Selection.ISelectionFilter):
    def AllowElement(self, elem):
        return elem.Category.Id == DB.ElementId(DB.BuiltInCategory.OST_Floors)

    def AllowReference(self, ref, point):
        return True


def create_floor_tag(doc, view, floor, point):
    tag_type_id = DB.FilteredElementCollector(doc).OfCategory(
        DB.BuiltInCategory.OST_FloorTags).FirstElementId()

    if tag_type_id != DB.ElementId.InvalidElementId:
        tag = DB.IndependentTag.Create(doc, tag_type_id, view.Id, DB.Reference(floor), False,
                                 DB.TagOrientation.Horizontal, point)
        return tag
    return False


def main():
    uidoc = revit.uidoc
    doc = uidoc.Document
    view = doc.ActiveView

    try:
        slab_filter = SlabSelectionFilter()
        ref = uidoc.Selection.PickObject(UI.Selection.ObjectType.PointOnElement, slab_filter,
                                         "Select a point on a slab element")
        floor = doc.GetElement(ref.ElementId)
        point = ref.GlobalPoint

        with revit.Transaction("Create Floor Tag"):
            if not create_floor_tag(doc, view, floor, point):
                UI.TaskDialog.Show("Error", "Failed to create floor tag.")

    except Exceptions.OperationCanceledException:
        UI.TaskDialog.Show("Cancelled", "Floor tag creation cancelled.")


if __name__ == "__main__":
    main()