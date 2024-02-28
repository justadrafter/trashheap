"""Select all columns with similar X,Y"""

from pyrevit import revit, DB
from Autodesk.Revit.DB import LocationCurve, LocationPoint

doc = __revit__.ActiveUIDocument.Document

def get_parameter_value_by_name(element, parameterName):
	return element.LookupParameter(parameterName).AsValueString()

def point_close(_pointA,_pointB):
    return abs(_pointA.X-_pointB.X) < 2 and abs(_pointA.Y-_pointB.Y) < 2

def bbmid(_col):
    _bb = _col.get_BoundingBox(None)
    return (_bb.Max + _bb.Min)/2

selection = revit.get_selection()

baselocation = bbmid(selection[0])

_collector = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_StructuralColumns).WhereElementIsNotElementType()

selSet = []

for _col in _collector:
    if point_close(bbmid(_col),baselocation):
        selSet.append(_col)

revit.get_selection().set_to(selSet)