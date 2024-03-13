from pyrevit import revit, forms
from revitfunctions.basics import get_element_bottom_z, get_element_top_z, move_elements

# Initialization
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
selected_ids = uidoc.Selection.GetElementIds()

if not selected_ids or len(selected_ids) < 2:
    forms.alert('Please select at least two elements.', exitscript=True)

elements = [doc.GetElement(id) for id in selected_ids]

def move_lowest_under_highest():
    top_z_values = [get_element_top_z(el) for el in elements]
    highest_element_index = top_z_values.index(max(top_z_values))
    bottom_z_values = [get_element_bottom_z(el) for el in elements]
    offset = bottom_z_values[highest_element_index] - max(top_z_values)
    move_elements(doc, elements, top_z_values, highest_element_index, offset)

with revit.Transaction("Moved elements to underside"):
    move_lowest_under_highest()