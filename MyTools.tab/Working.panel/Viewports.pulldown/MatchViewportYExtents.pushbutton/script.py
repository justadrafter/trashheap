"""
Match Z Extents of View Crop Boxes

This script allows you to match the Z extents of view crop boxes through viewports.
If a single viewport is selected, the script will prompt for target viewports to apply the Z extents.
If multiple viewports are selected, the script will prompt for a single source viewport to match the Z extents of the selected viewports.
"""

from pyrevit import revit, DB, forms
from Autodesk.Revit.DB import XYZ, Line, CurveLoop

__title__ = "Match Z Extents of View Crop Boxes"
__author__ = "Adam Shaw"


def get_selected_viewports():
    """Retrieve the selected viewports from the current selection."""
    selection = revit.get_selection()
    viewports = [el for el in selection if isinstance(el, DB.Viewport)]
    return viewports


def select_source_viewport():
    """Prompt the user to select a single source viewport."""
    source_viewport = revit.pick_element("Select a source viewport to match the Z extents.")
    if source_viewport and isinstance(source_viewport, DB.Viewport):
        return source_viewport
    else:
        forms.alert("Selected element is not a viewport. Please try again.")
        return None


def get_viewports_with_same_template(source_view_template_id):
    """Retrieve all viewports with the same view template as the source viewport."""
    all_viewports = DB.FilteredElementCollector(revit.doc).OfClass(DB.Viewport).ToElements()
    viewports_matching_templates = [revit.doc.GetElement(vp.ViewId) for vp in all_viewports if revit.doc.GetElement(vp.ViewId).ViewTemplateId == source_view_template_id]
    return viewports_matching_templates


def get_min_max_coordinates(crop_shape):
    """Calculate the minimum and maximum Z coordinates from the given crop shape."""
    min_z = float("inf")
    max_z = float("-inf")
    
    for loop in crop_shape:
        for line in loop:
            start_point = line.GetEndPoint(0)
            end_point = line.GetEndPoint(1)
            min_z = min(min_z, start_point.Z, end_point.Z)
            max_z = max(max_z, start_point.Z, end_point.Z)
    
    return min_z, max_z


def set_view_crop_shape(target_view, min_z, max_z,btmoffset,topoffset):
    threshold = 0.01
    target_crsm = target_view.GetCropRegionShapeManager()
    crop_shape = target_crsm.GetCropShape()
    start_points = [line.GetEndPoint(0) for loop in crop_shape for line in loop]

    target_crsm.BottomAnnotationCropOffset = btmoffset
    target_crsm.TopAnnotationCropOffset = topoffset

    # Find the minimum and maximum Z values in start_points
    z_values = [point.Z for point in start_points]
    smallest_z = min(z_values)
    largest_z = max(z_values)

    curve_loop = CurveLoop()
    for i in range(len(start_points)):
        start_point = start_points[i]
        end_point = start_points[(i + 1) % len(start_points)]

        start_point_new = start_point
        end_point_new = end_point

        if abs(start_point.Z - smallest_z) < threshold:
            start_point_new = XYZ(start_point.X, start_point.Y, min_z)
        elif abs(start_point.Z - largest_z) < threshold:
            start_point_new = XYZ(start_point.X, start_point.Y, max_z)

        if abs(end_point.Z - smallest_z) < threshold:
            end_point_new = XYZ(end_point.X, end_point.Y, min_z)
        elif abs(end_point.Z - largest_z) < threshold:
            end_point_new = XYZ(end_point.X, end_point.Y, max_z)

        curve_loop.Append(Line.CreateBound(start_point_new, end_point_new))

    return curve_loop

def main():
    """Main function to control the flow of the script."""
    selected_viewports = get_selected_viewports()
    
    if not selected_viewports:
        forms.alert("No viewports selected. Please select viewports and run the script again.")
        return
    
    if len(selected_viewports) == 1:
        source_viewport = selected_viewports[0]
        source_view = revit.doc.GetElement(source_viewport.ViewId)
        source_view_template = source_view.ViewTemplateId
        
        matching_vptemplate_views = get_viewports_with_same_template(source_view_template)
        sorted_views = sorted(matching_vptemplate_views,key=lambda x: x.Name)
        target_views = forms.SelectFromList.show(
            sorted_views,
            title="Select Target Views",
            name_attr="Name",  # Use the view name as the name attribute
            button_name="Apply Z Extents",
            multiselect=True
        )
        if not target_views:
            forms.alert("No target views selected.")
            return


    else:
        source_viewport = select_source_viewport()
        if not source_viewport:
            forms.alert("No source viewport selected or invalid selection.")
            return
        
        source_view = revit.doc.GetElement(source_viewport.ViewId)
        target_views = [revit.doc.GetElement(vp.ViewId) for vp in selected_viewports if vp.Id != source_viewport.Id]
    
    crsm = source_view.GetCropRegionShapeManager()
    crop_shape = crsm.GetCropShape()
    btmoffset = crsm.BottomAnnotationCropOffset
    topoffset = crsm.TopAnnotationCropOffset
    min_z, max_z = get_min_max_coordinates(crop_shape)
    with revit.Transaction("Matching Views Extents"):
        for target in target_views:
            curve_loop = set_view_crop_shape(target,min_z,max_z,btmoffset,topoffset)
            crsm = target.GetCropRegionShapeManager()
            crsm.SetCropShape(curve_loop)


if __name__ == "__main__":
    main()


