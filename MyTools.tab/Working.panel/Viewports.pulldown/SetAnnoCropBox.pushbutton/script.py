# Importing necessary libraries
from pyrevit import script, forms, revit, DB
from Autodesk.Revit.DB import ViewType

# Get the offset value from the user
offset_value = float(forms.ask_for_string('Enter off in mm'))/304.8

# Get the current document
doc = revit.doc

# Define a custom filter function
def filter_by_view_type(view):
    # Check if the view type is StructuralPlan
    return view.ViewType == ViewType.EngineeringPlan

# Filter views to only show StructuralPlan views
filtered_views = forms.select_views(
    title='Select Views',
    button_name='Select',
    width=500,
    multiple=True,
    filterfunc=filter_by_view_type,  # Use the custom filter function
    doc=None
)

# Start a transaction in the Revit document
with DB.Transaction(doc, 'Set Annotation Crop Offset') as t:
    t.Start()
    
    # Iterate over all viewports
    for _views in filtered_views:
        regionMan = _views.GetCropRegionShapeManager()
        regionMan.BottomAnnotationCropOffset = offset_value
        regionMan.LeftAnnotationCropOffset = offset_value
        regionMan.RightAnnotationCropOffset = offset_value
        regionMan.TopAnnotationCropOffset = offset_value
        
    # Commit the transaction
    t.Commit()