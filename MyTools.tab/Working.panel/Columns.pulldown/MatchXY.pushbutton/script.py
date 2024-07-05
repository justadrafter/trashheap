# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import XYZ
from Autodesk.Revit.UI.Selection import ObjectType
from pyrevit import revit

"""
Match XY coordinates of selected elements to a target element.

Instructions:
1. Select one or more elements to be moved.
2. Run the script.
3. Select the target element to match XY coordinates.
"""


__title__ = "Match XY"
__author__ = "Adam Shaw"

DOC = revit.doc
UIDOC = revit.uidoc

def get_selected_elements():
    """Get the currently selected elements."""
    return [DOC.GetElement(id) for id in UIDOC.Selection.GetElementIds()]

def pick_target_element():
    """Prompt user to pick a target element."""
    try:
        target_ref = UIDOC.Selection.PickObject(ObjectType.Element, 'Select target element')
        return DOC.GetElement(target_ref.ElementId)
    except:
        return None

def update_element_location(element, target_location):
    """Update the XY location of an element to match the target location."""
    if hasattr(element.Location, 'Point'):
        current_location = element.Location.Point
        new_location = XYZ(target_location.X, target_location.Y, current_location.Z)
        element.Location.Move(new_location - current_location)

def main():
    selected_elements = get_selected_elements()
    if not selected_elements:
        revit.forms.alert("No elements selected. Please select elements and run the script again.")
        return

    target_element = pick_target_element()
    if not target_element:
        revit.forms.alert("No target element selected. Operation cancelled.")
        return

    target_location = target_element.Location.Point

    with revit.Transaction("Match XY Coordinates"):
        for elem in selected_elements:
            update_element_location(elem, target_location)

if __name__ == "__main__":
    main()
