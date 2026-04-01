"""
Select Elements from Tags

This script selects all elements that the currently selected tags belong to.

Instructions:
1. Select one or more tags in the Revit model.
2. Run this script.
3. The script will select the corresponding elements that the selected tags are associated with.

Note: If no tags are selected, an alert will be displayed.
Works with Revit 2022+ (handles API changes for subelements and 2024+).
"""

from pyrevit import revit, DB, forms

__title__ = "Select Elements from Tags"
__author__ = "Adam Shaw"

def get_tagged_elements(tag, revit_ver):
    """Get tagged elements based on Revit version."""
    if revit_ver >= "2024.0":  # 2024, 2025, 2026+
        # Use plural methods for subelements (most robust)
        try:
            return list(tag.GetTaggedLocalElements())
        except AttributeError:
            # Fallback to IDs method
            element_ids = list(tag.GetTaggedLocalElementIds())
            return [revit.doc.GetElement(eid) for eid in element_ids if eid != DB.ElementId.InvalidElementId]
    elif revit_ver >= "2022.0":
        # 2022-2023: GetTaggedLocalElements available
        return list(tag.GetTaggedLocalElements())
    else:
        # Pre-2022: Legacy single element
        tagged_element = tag.GetTaggedLocalElement()
        return [tagged_element] if tagged_element else []

def select_elements_from_tags(tags, revit_ver):
    elements_to_select = []
    seen_ids = set()
    
    for tag in tags:
        if isinstance(tag, DB.IndependentTag):
            tagged_elements = get_tagged_elements(tag, revit_ver)
            for elem in tagged_elements:
                if elem and elem.Id not in seen_ids:
                    elements_to_select.append(elem)
                    seen_ids.add(elem.Id)
    
    return elements_to_select

def main():
    doc = revit.doc
    revit_ver = doc.Application.VersionNumber
    
    selection = revit.get_selection()
    selected_tags = [elem for elem in selection if isinstance(elem, DB.IndependentTag)]

    if not selected_tags:
        forms.alert("No tags selected. Please select tags and run the script again.")
        return

    elements = select_elements_from_tags(selected_tags, revit_ver)

    if elements:
        revit.get_selection().set_to(elements)
    else:
        forms.alert("No elements found for the selected tags.")

if __name__ == "__main__":
    main()
