from pyrevit import revit, DB, forms

# Initialization
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# Retrieve all line styles using PyRevit's built-in function
lineStyles = revit.query.get_line_styles()

# Find the "Invisible Lines" GraphicsStyle
for gs in DB.FilteredElementCollector(doc).OfClass(DB.GraphicsStyle).WhereElementIsNotElementType():
    if gs.GraphicsStyleCategory.Id == DB.ElementId(DB.BuiltInCategory.OST_InvisibleLines):
        lineStyles.append(gs)

# Prepare a dictionary for user selection, mapping style names to GraphicsStyle elements
lineStyleDict = {style.Name: style for style in lineStyles}

selectedStyleName = forms.SelectFromList.show(sorted(lineStyleDict.keys()),"Select Line Style",600, 300,button_name='Select Line Style')

# Check if the user didn't select a style or cancelled the form
if not selectedStyleName:
    # User cancelled the form or didn't select anything
    forms.alert('No line style selected. Operation cancelled.', exitscript=True)

selectedStyle = lineStyleDict[selectedStyleName].Id

# Get the selected filled regions
selectedElements = [doc.GetElement(id) for id in uidoc.Selection.GetElementIds()]

with revit.Transaction("Set Lines to Invisible"):
    for filledRegion in selectedElements:                      
        # Iterate through sketch lines and set their style to "Invisible Lines"
        # Set the line style to Invisible Lines using SetLineStyleId method
        filledRegion.SetLineStyleId(selectedStyle)