import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.UI.Selection import *
 # get the active document and transaction
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
tx = Transaction(doc, 'Match Wall Points')
tx.Start()
 # get the selected walls
wall_ids = uidoc.Selection.GetElementIds()
walls = [doc.GetElement(id) for id in wall_ids]
 # get the target wall
target_id = uidoc.Selection.PickObject(ObjectType.Element, 'Select target wall').ElementId
target_wall = doc.GetElement(target_id)
 # get the start and end points of the target wall
start_pt = target_wall.Location.Curve.GetEndPoint(0)
end_pt = target_wall.Location.Curve.GetEndPoint(1)
 # update the start and end points of each selected wall
for wall in walls:
    start_z = wall.Location.Curve.GetEndPoint(0).Z
    end_z = wall.Location.Curve.GetEndPoint(1).Z
    start_pt = XYZ(start_pt.X, start_pt.Y, start_z)
    end_pt = XYZ(end_pt.X, end_pt.Y, end_z)
    wall.Location.Curve = Line.CreateBound(start_pt, end_pt)
 # commit the changes
tx.Commit()