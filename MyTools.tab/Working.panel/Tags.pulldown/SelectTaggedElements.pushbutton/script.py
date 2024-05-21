"""
Select Elements from Tags

This script selects all elements that the currently selected tags belong to.

Instructions:
1. Select one or more tags in the Revit model.
2. Run this script.
3. The script will select the corresponding elements that the selected tags are associated with.

Note: If no tags are selected, an alert will be displayed.
"""

from pyrevit import revit, DB, forms

__title__ = "Select Elements from Tags"
__author__ = "Adam Shaw"


def select_elements_from_tags(tags):
    elements_to_select = []
    for tag in tags:
        if isinstance(tag, DB.IndependentTag):
            tagged_element = tag.GetTaggedLocalElement()
            if tagged_element:
                elements_to_select.append(tagged_element)
    return elements_to_select


def main():
    selection = revit.get_selection()
    selected_tags = [elem for elem in selection if isinstance(elem, DB.IndependentTag)]

    if not selected_tags:
        forms.alert("No tags selected. Please select tags and run the script again.")
        return

    elements = select_elements_from_tags(selected_tags)

    if elements:
        revit.get_selection().set_to(elements)
    else:
        forms.alert("No elements found for the selected tags.")


if __name__ == "__main__":
    main()