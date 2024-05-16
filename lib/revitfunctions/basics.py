from Autodesk.Revit.DB import ElementTransformUtils, XYZ, BuiltInCategory, ElementId, ColumnAttachment, UnitUtils, UnitTypeId
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


def get_selected_columns(doc):
    """
    Retrieve the selected structural columns from the active Revit document.
    
    Args:
        doc (Autodesk.Revit.DB.Document): The Revit document.
        
    Returns:
        list: Selected structural column elements.
    """
    selected_ids = revit.uidoc.Selection.GetElementIds()
    return [doc.GetElement(id) for id in selected_ids
            if doc.GetElement(id).Category.Id == ElementId(BuiltInCategory.OST_StructuralColumns)]


def remove_column_attachments(column):
    """
    Dettach the column from top & btm

    Args:
        column (DB.FamilyInstance): The column element to dettach.
        top_or_bottom (int): 0 for bottom attachment, 1 for top attachment.
    """
    ColumnAttachment.RemoveColumnAttachment(column,0)
    ColumnAttachment.RemoveColumnAttachment(column,1)


def mm_to_feet(mm):
    """
    Convert millimeters to feet using Revit's UnitUtils.

    Args:
        mm (float): The length in millimeters.

    Returns:
        float: The length in feet.
    """
    feet = UnitUtils.Convert(mm, UnitTypeId.Millimeters, UnitTypeId.Feet)
    return feet

def feet_to_mm(feet):
    """
    Convert feet to millimeters using Revit's UnitUtils.

    Args:
        feet (float): The length in feet.

    Returns:
        float: The length in millimeters.
    """
    mm = UnitUtils.Convert(feet, UnitTypeId.Feet, UnitTypeId.Millimeters)
    return mm