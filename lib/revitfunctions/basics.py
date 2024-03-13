from Autodesk.Revit.DB import ElementTransformUtils, XYZ
from pyrevit import revit, forms
import Autodesk.Revit.Exceptions as RevitExceptions

def get_element_bottom_z(element):
    """
    Get the Z coordinate of the bottom of the element's bounding box.

    Args:
        element (Autodesk.Revit.DB.Element): The Revit element.

    Returns:
        float: The Z coordinate of the bottom of the element's bounding box, or None if the bounding box is not available.
    """
    bbox = element.get_BoundingBox(None)  # Get bounding box in the default view
    if bbox:
        return bbox.Min.Z  # Return the minimum Z value (bottom)
    else:
        return None


def get_element_top_z(element):
    """
    Get the Z coordinate of the top of the element's bounding box.

    Args:
        element (Autodesk.Revit.DB.Element): The Revit element.

    Returns:
        float: The Z coordinate of the top of the element's bounding box, or None if the bounding box is not available.
    """
    bbox = element.get_BoundingBox(None)  # Get bounding box in the default view
    if bbox:
        return bbox.Max.Z  # Return the maximum Z value (top)
    else:
        return None
    
def move_elements(doc, elements, z_values, reference_index, offset=0.0):
    """
    Moves the elements based on the provided Z values, reference index, and offset.

    Args:
        doc (Autodesk.Revit.DB.Document): The Revit document.
        elements (list): List of Revit elements.
        z_values (list): List of Z values for the elements.
        reference_index (int): Index of the reference element.
        offset (float, optional): Offset value for moving the elements. Defaults to 0.0.
    """
    for i, element in enumerate(elements):
        if i != reference_index:
            reference_z_value = z_values[reference_index]
            current_z_value = z_values[i]
            distance_to_move = reference_z_value - current_z_value + offset
            translation_vector = XYZ(0, 0, distance_to_move)
            try:
                ElementTransformUtils.MoveElement(doc, element.Id, translation_vector)
            except RevitExceptions.ArgumentException as e:
                forms.alert("Error moving element: " + str(e), exitscript=True)