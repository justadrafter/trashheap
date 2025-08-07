"""
This script selects all tags in Engineering Plan views that are related to the selected elements in Revit.
"""

from pyrevit import revit, DB, forms
from System.Collections.Generic import List

__title__ = "Select Related Tags in Engineering Plans"
__author__ = "Adam Shaw"


def get_related_tags_in_engineering_plans(doc, selected_ids, revit_version):
    """
    Retrieve tags related to the selected elements in Engineering Plan views.

    Args:
        doc (DB.Document): The active Revit document.
        selected_ids (List[DB.ElementId]): The IDs of the selected elements.
        revit_version (str): The version of Revit (e.g., "2022", "2024").

    Returns:
        set: A set of related tags in Engineering Plan views.
    """
    all_tags = DB.FilteredElementCollector(doc).OfClass(DB.IndependentTag)

    def is_tag_valid(tag):
        """Check if a tag is related and in an Engineering Plan view."""
        # Check if tag is in an Engineering Plan view
        view = doc.GetElement(tag.OwnerViewId)
        if not (view and isinstance(view, DB.ViewPlan)):
            return False

        if view.ViewType != DB.ViewType.EngineeringPlan:
            return False

        # Check if tag is related to selected elements
        if revit_version.startswith("2022"):
            return tag.TaggedLocalElementId in selected_ids
        elif revit_version.startswith("2024"):
            return any(
                tag_id in selected_ids for tag_id in tag.GetTaggedLocalElementIds()
            )

        return False

    return {tag for tag in all_tags if is_tag_valid(tag)}


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
        forms.alert(
            "No elements selected. Please select elements and run the script again."
        )
        return

    related_tags = get_related_tags_in_engineering_plans(doc, selected_ids, revit_version)

    with revit.Transaction("Select Related Tags in Engineering Plans"):
        tag_ids = List[DB.ElementId]([tag.Id for tag in related_tags])
        uidoc.Selection.SetElementIds(tag_ids)


if __name__ == "__main__":
    main()