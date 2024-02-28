'''Split Selected Columns by all structural levels unless selected'''

from pyrevit import revit, DB
from Autodesk.Revit.DB import Transaction
import math

doc = __revit__.ActiveUIDocument.Document


# Variables
_selection = revit.get_selection()

_levels = []
_cols = []

t = Transaction(doc, 'Split Cols')

# Functions
def get_parameter_value_by_name(element, parameterName):
	return element.LookupParameter(parameterName).AsValueString()

def get_scol_vert(element):
    extents = [round(element.GetSweptProfile().GetDrivingCurve().GetEndPoint(0).Z,3), round(element.GetSweptProfile().GetDrivingCurve().GetEndPoint(1).Z,3)]
    extents.sort()
    return extents


# Split selection into cols & levels
for _elem in _selection:
    if _elem.Category.Name == "Levels":
         _levels.append(_elem)
    elif _elem.Category.Name == "Structural Columns":
         _cols.append(_elem)

# if no levels selected use all structural levels
if not _levels:
    coll_levels = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Levels).WhereElementIsNotElementType()
    for x in coll_levels:
        if get_parameter_value_by_name(x,"Structural") == "Yes":
            _levels.append(x) 

_levels.sort(key=lambda level: level.Elevation)
_cols.sort(key=lambda col: get_scol_vert(col)[0])

# Transaction 
t.Start()

for _level in _levels:
    temp_levelev = _level.Elevation
    for _col in _cols:
        temp_colbtm = get_scol_vert(_col)[0]
        temp_coltop = get_scol_vert(_col)[1]
        if (temp_colbtm + 100/304.8)< temp_levelev < (temp_coltop - 100/304.8):
            temp_levelev = round(temp_levelev,3)
            temp_splitval = (temp_levelev - temp_colbtm)/(temp_coltop- temp_colbtm)
            _cols.append(doc.GetElement(_col.Split(temp_splitval)))
t.Commit()