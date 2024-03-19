from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, XYZ

doc = revit.doc

def get_parameter_value_by_name(element, parameter_name):
    """
    Retrieves the value of a parameter from an element as a string.
    
    :param element: Revit element
    :param parameter_name: Name of the parameter
    :return: Parameter value as a string
    """
    return element.LookupParameter(parameter_name).AsValueString()

def is_point_close(point_a, point_b, tolerance=2):
    """
    Checks if two points are close to each other within a specified tolerance.
    
    :param point_a: First point (XYZ)
    :param point_b: Second point (XYZ)
    :param tolerance: Tolerance value (default: 2)
    :return: True if points are close, False otherwise
    """
    return abs(point_a.X - point_b.X) < tolerance and abs(point_a.Y - point_b.Y) < tolerance

def get_bounding_box_center(element):
    """
    Calculates the center point of an element's bounding box.
    
    :param element: Revit element
    :return: Center point of the bounding box (XYZ)
    """
    bounding_box = element.get_BoundingBox(None)
    return (bounding_box.Max + bounding_box.Min) / 2

selected_elements = revit.get_selection()

if not selected_elements:
    forms.alert("Please select at least one element.")
    script.exit()

base_locations = [get_bounding_box_center(element) for element in selected_elements]

collector = FilteredElementCollector(doc) \
    .OfCategory(BuiltInCategory.OST_StructuralColumns) \
    .WhereElementIsNotElementType()

selected_columns = []

for column in collector:
    column_center = get_bounding_box_center(column)
    if any(is_point_close(column_center, base_location) for base_location in base_locations):
        selected_columns.append(column)

revit.get_selection().set_to(selected_columns)