import clr 
clr.AddReference('RevitAPI') 
from Autodesk.Revit.DB import * 
clr.AddReference('RevitAPIUI') 
from Autodesk.Revit.UI.Selection import * 
 # get the active document and transaction
doc = __revit__.ActiveUIDocument.Document 
uidoc = __revit__.ActiveUIDocument 
tx = Transaction(doc, 'Match Points') 
tx.Start()
 # get the selected elements
ids = uidoc.Selection.GetElementIds() 
selected_elements = [doc.GetElement(id) for id in ids] 
 # select the target element
target_id = uidoc.Selection.PickObject(ObjectType.Element, 'Select target element').ElementId
target_element = doc.GetElement(target_id)
 # get the location point of the target element
target_location = target_element.Location.Point
 # update the location of each selected element
for elem in selected_elements:
    location = elem.Location.Point
    updated_location = XYZ(target_location.X, target_location.Y, location.Z)
    elem.Location.Move(updated_location - location)
 # commit the changes
tx.Commit()