"""
This script selects all tags in the current view that are related to the selected elements in Revit.
"""

from pyrevit import revit, DB
from System.Collections.Generic import List

__title__ = "Select Related Tags in Current View"
__author__ = "Adam Shaw"


def get_related_tags(doc, view_id, selected_ids, revit_version):
    """
    Retrieve tags related to the selected elements in the current view.

    Args:
        doc (DB.Document): The active Revit document.
        view_id (DB.ElementId): The ID of the current view.
        selected_ids (List[DB.ElementId]): The IDs of the selected elements.
        revit_version (str): The version of Revit (e.g., "2022", "2024").

    Returns:
        set: A set of related tags.
    """
    tags = DB.FilteredElementCollector(doc, view_id).OfClass(DB.IndependentTag)

    related_tags = set()
    if revit_version.startswith("2022"):
        related_tags = {tag for tag in tags if tag.TaggedLocalElementId in selected_ids}
    elif revit_version.startswith("2024"):
        related_tags = {
            tag for tag in tags
            if any(tag_id in selected_ids for tag_id in tag.GetTaggedLocalElementIds())
        }

    return related_tags


def main():
    """
    Main function to execute the script logic.
    """
    doc = revit.doc
    uidoc = revit.uidoc
    app = doc.Application

    revit_version = app.VersionNumber

    selected_ids = uidoc.Selection.GetElementIds()

    if not selected_ids:
        forms.alert("No elements selected. Please select elements and run the script again.")
        return

    view_id = doc.ActiveView.Id
    related_tags = get_related_tags(doc, view_id, selected_ids, revit_version)

    with revit.Transaction("Select Related Tags in Current View"):
        tag_ids = List[DB.ElementId]([tag.Id for tag in related_tags])
        uidoc.Selection.SetElementIds(tag_ids)


if __name__ == "__main__":
    main()