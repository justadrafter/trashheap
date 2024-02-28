import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.UI.Selection import ObjectSnapTypes, ObjectType
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Transaction
from Autodesk.Revit.UI import TaskDialog
 # Get the current Revit document
doc = __revit__.ActiveUIDocument.Document
 # Get the mouse location
mouse_point = __revit__.ActiveUIDocument.Selection.PickPoint(ObjectSnapTypes.Endpoints | ObjectSnapTypes.Midpoints)
 # Get the floor element at the mouse location
floor_filter = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Floors).ToElements()
floor = None
for f in floor_filter:
    if f.Location is not None and f.Location.Point.DistanceTo(mouse_point) < 0.001:
        floor = f
        break
 # Create the floor tag
if floor:
    tag = doc.Create.NewTag(doc.ActiveView, floor, True, 0)
    tag.ChangeTypeId(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_FloorTags).FirstElementId())
    TaskDialog.Show("Success", "Floor tag created.")
else:
    TaskDialog.Show("Error", "No floor found at mouse location.")