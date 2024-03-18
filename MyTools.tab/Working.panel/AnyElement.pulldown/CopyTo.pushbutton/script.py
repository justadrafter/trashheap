import clr
import sys

# Add Revit API references
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

from Autodesk.Revit.DB import (
    ElementTransformUtils, XYZ, CopyPasteOptions
)
from Autodesk.Revit.UI.Selection import ObjectType
from pyrevit import revit

# Get the active UIDocument and Document
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
opts = CopyPasteOptions()

def copy_elements_with_transform(doc, element_ids, transform):
    """
    Copy elements with the given transform.

    Args:
        doc (Document): The Revit document.
        element_ids (ICollection<ElementId>): The IDs of the elements to copy.
        transform (Transform): The transform to apply to the copied elements.
    """
    new_element_ids = ElementTransformUtils.CopyElements(doc, element_ids, doc, transform, opts)
    new_elements = [doc.GetElement(id) for id in new_element_ids]
      
    return new_elements

# Get the objects to copy (assumes pre-selection)
selection = uidoc.Selection
objects_to_copy = selection.GetElementIds()

if not objects_to_copy:
    print('Please pre-select the object(s) to copy.')
    sys.exit()

# Ask user to select the single 'objectfrom'
object_from_ref = selection.PickObject(
    ObjectType.Element, 'Please select the source object to copy from'
)
object_from = doc.GetElement(object_from_ref.ElementId)
source_transform = object_from.GetTransform()

# Ask user to select multiple 'objectsto'
object_to_refs = selection.PickObjects(
    ObjectType.Element, 'Please select target objects to copy to'
)
object_tos = [doc.GetElement(ref.ElementId) for ref in object_to_refs]

# Use 'with' statement for transaction management
with revit.Transaction('Copy Elements'):
    for object_to in object_tos:
        target_transform = object_to.GetTransform()
        transform_diff = target_transform.Multiply(source_transform.Inverse)
        new_elements = copy_elements_with_transform(doc, objects_to_copy, transform_diff)