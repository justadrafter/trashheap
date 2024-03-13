from pyrevit import revit, forms
from revitfunctions.basics import get_element_bottom_z, get_element_top_z, move_elements

# Initialization
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
selected_ids = uidoc.Selection.GetElementIds()

if not selected_ids or len(selected_ids) < 2:
    forms.alert('Please select at least two elements.', exitscript=True)

elements = [doc.GetElement(id) for id in selected_ids]

def move_highest_above_lowest():
    top_z_values = [get_element_top_z(el) for el in elements]
    lowest_element_index = top_z_values.index(min(top_z_values))
    bottom_z_values = [get_element_bottom_z(el) for el in elements]
    offset = min(top_z_values) - bottom_z_values[lowest_element_index]
    move_elements(doc, elements, bottom_z_values, lowest_element_index, offset)

with revit.Transaction("Moved elements to topside"):
    move_highest_above_lowest()