"""
Copy Grid Curves from Selected Viewport to Other Views

This script uses the view of the selected viewport as the source view, retrieves its grid curves, and copies them to other views selected through a form.

Usage:
1. Select a viewport in the active view.
2. Run the script.
3. In the form that appears, select the target views to copy the grid curves to.
4. Click "OK" to perform the copy operation.

Note: The script will copy the view-specific curves of all grids in the view of the selected viewport to the selected target views.
"""

from pyrevit import revit, DB, forms
from Autodesk.Revit.DB import DatumExtentType, FilteredElementCollector

__title__ = "Propagate 2D grids extents from viewport to views"
__author__ = "Adam Shaw"


def get_viewport_view(viewport):
    """
    Retrieve the view associated with the given viewport.
    
    Args:
        viewport (DB.Viewport): The viewport element.
        
    Returns:
        DB.View: The view associated with the viewport.
    """
    return revit.doc.GetElement(viewport.ViewId)


def get_grid_curves(view):
    """
    Retrieve the view-specific curves of all grids in a specific view.
    
    Args:
        view (DB.View): The view to retrieve the grid curves from.
        
    Returns:
        dict: A dictionary with grid elements as keys and their corresponding curves as values.
    """
    grids = FilteredElementCollector(revit.doc, view.Id).OfClass(DB.Grid).ToElements()
    grid_curves_dict = {}
    for grid in grids:
        curves = grid.GetCurvesInView(DatumExtentType.ViewSpecific, view)
        grid_curves_dict[grid] = curves
    return grid_curves_dict


def copy_curves_to_views(grid_curves_dict, views):
    """
    Copy the curves to the specified views.
    
    Args:
        grid_curves_dict (dict): A dictionary with grid elements as keys and their corresponding curves as values.
        views (list): List of DB.View objects to copy curves to.
    """
    with revit.Transaction("Copy Grid Curves"):
        for view in views:
            for grid, curves in grid_curves_dict.items():
                for curve in curves:
                    grid.SetCurveInView(DatumExtentType.ViewSpecific, view, curve)


def get_scope_box_value(view):
    """
    Get the value of the "Scope Box" parameter of the view.
    
    Args:
        view (DB.View): The view to retrieve the "Scope Box" parameter value from.
        
    Returns:
        str: The value of the "Scope Box" parameter.
    """
    scope_box_param = view.Parameter[DB.BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP]
    return scope_box_param.AsValueString() if scope_box_param else None


def filter_views_by_scale_and_scope_box(source_view, all_views):
    """
    Filter the list of views based on the scale and scope box parameter value of the source view.
    
    Args:
        source_view (DB.View): The source view to match the scale and scope box parameter value.
        all_views (list): List of all views in the model.
        
    Returns:
        list: Filtered list of views matching the scale and scope box parameter value of the source view.
    """
    filtered_views = []
    source_view_scale = source_view.Scale
    source_scope_box_value = get_scope_box_value(source_view)
    
    for view in all_views:
        if view.ViewType == source_view.ViewType and view.Scale == source_view_scale:
            view_scope_box_value = get_scope_box_value(view)
            if source_scope_box_value == view_scope_box_value:
                filtered_views.append(view)
    
    return filtered_views


def main():
    """
    Main function to execute the script logic.
    """
    selection = revit.get_selection()
    
    viewport = None
    for elem in selection:
        if isinstance(elem, DB.Viewport):
            viewport = elem
            break
    
    if not viewport:
        forms.alert("No viewport selected. Please select a viewport and run the script again.")
        return
        
    source_view = get_viewport_view(viewport)
    
    grid_curves_dict = get_grid_curves(source_view)
    
    if not grid_curves_dict:
        forms.alert("No grid curves found in the selected viewport's view.")
        return
        
    all_views = FilteredElementCollector(revit.doc).OfClass(DB.View).ToElements()
    filtered_views = filter_views_by_scale_and_scope_box(source_view, all_views)
    
    sorted_views = sorted(filtered_views, key=lambda view: view.GenLevel.Elevation)
    
    target_views = forms.SelectFromList.show(sorted_views, 
                                             multiselect=True, 
                                             name_attr="Name", 
                                             title="Select Target Views")
    
    if not target_views:
        forms.alert("No target views selected. Please select at least one view.")
        return
        
    copy_curves_to_views(grid_curves_dict, target_views)


if __name__ == "__main__":
    main()