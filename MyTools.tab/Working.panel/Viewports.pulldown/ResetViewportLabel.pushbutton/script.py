"""
Reset the label position of selected viewports.

Usage:
1. Select one or more viewports in the Revit project.
2. Run this script to reset the label position of the selected viewports.
"""

from pyrevit import revit, DB

__title__ = "Reset Viewport Label Position"
__author__ = "Adam Shaw"


def reset_viewport_label_position(viewport):
    """
    Reset the label position of the given viewport.
    
    Args:
        viewport (DB.Viewport): The viewport element to reset the label position for.
    """
    label_offset = DB.XYZ(1/304.8, 0, 0)
    viewport.LabelOffset = label_offset


def main():
    """
    Main function to execute the script logic.
    """
    selection = revit.get_selection()
    
    if not selection:
        forms.alert("No viewports selected. Please select viewports and run the script again.")
        return
    
    selected_viewports = [revit.doc.GetElement(elem_id) for elem_id in selection.element_ids]
    
    with revit.Transaction("Reset Viewport Label Position"):
        for viewport in selected_viewports:
            if isinstance(viewport, DB.Viewport):
                reset_viewport_label_position(viewport)
            else:
                logger.warning("Skipping non-viewport element: {}".format(viewport.Id))


if __name__ == "__main__":
    main()