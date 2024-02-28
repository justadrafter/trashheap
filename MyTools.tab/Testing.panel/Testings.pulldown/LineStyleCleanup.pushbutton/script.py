from Autodesk.Revit.DB import *
from pyrevit import DB, revit
import math

doc = __revit__.ActiveUIDocument.Document

active_view = doc.ActiveView

_selection = revit.get_selection()

view_cols = [v for v in DB.FilteredElementCollector(doc, _selection[0].ViewId).OfCategory(DB.BuiltInCategory.OST_StructuralColumns).WhereElementIsNotElementType()]

# _tagtype = [v for v in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_StructuralColumnTags).WhereElementIsElementType() if v.Family.Name == "Conc Column Tag_HERA"][0].Id


t = Transaction(doc, 'tagging')
t.Start()

_temppoint = []
for _col in view_cols:
    _colcurve = _col.GetAnalyticalModel().GetCurve()
    _midpoint = (_colcurve.GetEndPoint(0)+_colcurve.GetEndPoint(1))/2
    _temppoint.append(_midpoint.X)

_pointX = max(_temppoint)+5




for _col in view_cols:
    _colcurve = _col.GetAnalyticalModel().GetCurve()
    _point = (_colcurve.GetEndPoint(0)+_colcurve.GetEndPoint(1))/2
    _point = XYZ(_pointX,_point.Y,_point.Z)
    _view = _selection[0].ViewId
    _col2tag = Reference(_col)

    tag = IndependentTag.Create(doc,_view,_col2tag,False,TagMode.TM_ADDBY_CATEGORY, TagOrientation.Horizontal,_point)

t.Commit()