from rpw.ui.forms import TextInput
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Element, Transaction

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
t = Transaction(doc, 'Set Parameter by Name')

_startnew = 0
_endnew = 0
_texttop = ""
_textbtm = ""
_textloc = 10000

def set_parameter_by_name(element, parameterName, value):
    element.LookupParameter(parameterName).Set(value)

# convert units to mm coz revit retarded
def convertunits(number):
    return (number / 304.8)

# Select element from revit.
selection = [doc.GetElement(x) for x in uidoc.Selection.GetElementIds()]

# Start Transaction
t.Start()

for _detail in selection:
    set_parameter_by_name(_detail, "Text Location", convertunits(_textloc))

    try:
        set_parameter_by_name(_detail, "Start Rebar Area Extents", convertunits(_startnew))
        set_parameter_by_name(_detail, "End Rebar Area Extents", convertunits(_endnew))
        set_parameter_by_name(_detail, "Text TOP On/Off", 0)
        set_parameter_by_name(_detail, "Text BTM On/Off", 0)
        set_parameter_by_name(_detail, "Extent Line On/Off",0)

    except:
        set_parameter_by_name(_detail, "LEFT Extent", convertunits(_startnew))
        set_parameter_by_name(_detail, "RIGHT Extent", convertunits(_endnew))
        set_parameter_by_name(_detail, "Text TOP Vis", 0)
        set_parameter_by_name(_detail, "Text BTM Vis", 0)
        set_parameter_by_name(_detail, "Extent Line",0)

    set_parameter_by_name(_detail, "Text TOP", _texttop)
    set_parameter_by_name(_detail, "Text BTM", _textbtm)

# End Transaction
t.Commit()

# from rpw.ui.forms import TextInput
# from Autodesk.Revit import DB
# from Autodesk.Revit.DB import Element, Transaction
# import re
#
# uidoc = __revit__.ActiveUIDocument
# doc = __revit__.ActiveUIDocument.Document
# #t = Transaction(doc, 'Set Parameter by Name')
#
# # Select element from revit.
# selection = [doc.GetElement(x) for x in uidoc.Selection.GetElementIds()]
#
# for _detail in selection:
#     print(_detail)

#
# COLUMN_TAG_PARAMETER = "Column Mark No_RBG"  # Instance Parameter
# COLUMN_STRENGTH_PARAMETER = "Concrete Strength_RBG"  # Instance Parameter
# COLUMN_DEPTH_PARAMETER = "Column Width_RBG"  # Type Parameter
# COLUMN_BREADTH_PARAMETER = "Column Length_RBG"  # Type Parameter
# WALL_TAG_PARAMETER = "Wall Number_RBG"  # Instance Parameter
# BEAM_DEPTH_PARAMETER = "ConcreteBeamDepth_RBG"  # Type Parameter
# BEAM_WIDTH_PARAMETER = "ConcreteBeamWidth_RBG"  # Type Parameter
# BEAM_FAMILY_NAMES = ["Concrete Insitu Rectangular Beam_RBG"]
#
# # ======================================================================================================================================
# import clr
# import math
# import json
#
# clr.AddReference('RevitAPI')
# clr.AddReference('RevitAPIUI')
#
# # to access all the Name-spaces in the RevitAPI & UI, we import them all using *
# import Autodesk.Revit.DB as DB
# import Autodesk.Revit.DB.Structure as DBs
# import Autodesk.Revit.UI as UI
#
# # set the active Revit application and document
# uidoc = __revit__.ActiveUIDocument
# doc = __revit__.ActiveUIDocument.Document
#
# file_dialog = UI.FileSaveDialog("RDMP Files (*.rdmp)|*.rdmp")
# file_dialog.Show()
# OUTPUT_FILE = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(file_dialog.GetSelectedModelPath())
#
# to_mm = lambda x: round(DB.UnitUtils.ConvertFromInternalUnits(x, DB.UnitTypeId.Millimeters), 3)
#
#
# def curveloop_to_coords(loop):
#     coords = []
#
#     for n, curve in enumerate(loop.GetCurveLoopIterator()):
#         pts = curve.Tessellate() if n == 0 else list(curve.Tessellate())[1:]
#         xc = [to_mm(coord.X) for coord in pts]
#         yc = [to_mm(coord.Y) for coord in pts]
#         zc = [to_mm(coord.Z) for coord in pts]
#
#         coords.extend(zip(xc, yc, zc))
#
#     return coords
#
#
# def select_elements(el_list):
#     from System.Collections.Generic import List
#     elementIdList = List[ElementId]()
#     for g in el_list: elementIdList.Add(g.Id)
#     uidoc.Selection.SetElementIds(elementIdList)
#
#
# # Get levels
# print
# "Getting Levels..."
# level_list = []
# cnt = 0
# levels = DB.FilteredElementCollector(doc).OfClass(DB.Level)
# for n, lev in enumerate(levels.GetElementIterator()):
#     z = to_mm(lev.Elevation)
#     lev_data = {"rl": z, "name": lev.Name}
#     level_list.append(lev_data)
#     cnt += 1
# print
# "Found " + str(cnt) + " levels"
#
# # Get Columns
# print
# "Getting Columns..."
# column_list = []
# cnt = 0
# columns = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_StructuralColumns)
# for col in columns.GetElementIterator():
#     if col.GetType() == DB.FamilyInstance:
#         famtype = col.Symbol
#         an_col = col.GetAnalyticalModel()
#
#         params = col.GetParameters(COLUMN_TAG_PARAMETER)
#         tag = params[0].AsString() if len(params) > 0 else ""
#
#         params = col.GetParameters(COLUMN_STRENGTH_PARAMETER)
#         fc = params[0].AsString() if len(params) > 0 else ""
#
#         params = famtype.GetParameters(COLUMN_DEPTH_PARAMETER)
#         D = to_mm(params[0].AsDouble()) if len(params) > 0 else 0
#
#         params = famtype.GetParameters(COLUMN_BREADTH_PARAMETER)
#         B = to_mm(params[0].AsDouble()) if len(params) > 0 else 0
#
#         params = an_col.GetParameters("Cross-Section Rotation")
#         ang = params[0].AsDouble() * (180 / 3.141592) + 90 if len(params) > 0 else 0
#
#         an_line = an_col.GetCurve()
#         bot = an_line.GetEndPoint(0)
#         top = an_line.GetEndPoint(1)
#         p1 = (to_mm(bot.X), to_mm(bot.Y), to_mm(bot.Z))
#         p2 = (to_mm(top.X), to_mm(top.Y), to_mm(top.Z))
#
#         col_dict = {"bottom": p1, "top": p2, "D": D, "B": B, "fc": fc, "tag": tag, "angle": ang}
#         column_list.append(col_dict)
#         cnt += 1
# print
# "Found " + str(cnt) + " columns"
#
# # Get Slabs
# print
# "Getting Slabs..."
# slab_list = []
# cnt = 0
# floors = DB.FilteredElementCollector(doc).OfClass(DB.Floor)
# for floor in floors.GetElementIterator():
#     an_floor = floor.GetAnalyticalModel()
#     if an_floor is not None:
#         outer_loops = an_floor.GetLoops(DB.Structure.AnalyticalLoopType.External)
#         inner_loops = an_floor.GetLoops(DB.Structure.AnalyticalLoopType.Internal)
#
#         xyz_ext_loops = [curveloop_to_coords(c) for c in outer_loops]
#         xyz_int_loops = [curveloop_to_coords(c) for c in inner_loops]
#
#         eid = floor.GetParameters("Level")[0].AsElementId()
#         lev_name = doc.GetElement(eid).Name
#         t = to_mm(floor.GetParameters("Thickness")[0].AsDouble())
#
#         sdict = {}
#         sdict["exteriors"] = xyz_ext_loops
#         sdict["interiors"] = xyz_int_loops
#         sdict["thickness"] = t
#         slab_list.append(sdict)
#         cnt += 1
#     else:
#         print
#         "Floor has no analytical object"
# print
# "Found " + str(cnt) + " slabs"
#
# # Get Walls
# print
# "Getting Walls..."
# wall_list = []
# cnt = 0
# walls = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Walls)
# for wall in walls.GetElementIterator():
#     if wall.GetType() == DB.Wall:
#         famtype = wall.WallType
#         an_wall = wall.GetAnalyticalModel()
#
#         params = famtype.GetParameters("Width")
#         t = to_mm(params[0].AsDouble()) if len(params) > 0 else 0
#
#         params = wall.GetParameters(WALL_TAG_PARAMETER)
#         tag = params[0].AsString() if len(params) > 0 else ""
#
#         geom_loops = an_wall.GetLoops(DB.Structure.AnalyticalLoopType.External)
#         xyz_loops = [curveloop_to_coords(loop) for loop in geom_loops]
#
#         wall_dict = {"thickness": t, "points": xyz_loops, "tag": tag}
#
#         wall_list.append(wall_dict)
#         cnt += 1
# print
# "Found " + str(cnt) + " walls"
#
# # Get Beams
# print
# "Getting Beams..."
# beam_list = []
# cnt = 0
# beams = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_StructuralFraming)
# for beam in beams.GetElementIterator():
#     if beam.GetType() == DB.FamilyInstance:
#         famtype = beam.Symbol
#         if famtype.FamilyName in BEAM_FAMILY_NAMES:
#             opt = DB.Options()
#             opt.ComputeReferences = True
#             opt.IncludeNonVisibleObjects = False
#             g = beam.get_Geometry(opt)
#
#             loop_coords = []
#             for obj in g:
#                 if isinstance(obj, Solid):
#                     for pf in obj.Faces:
#                         if isinstance(pf, PlanarFace):
#                             if pf.FaceNormal[2] == 1.0:  # If face normal is pointing upwards
#                                 for cl in pf.GetEdgesAsCurveLoops(): loop_coords.append(curveloop_to_coords(cl))
#
#             an_beam = wall.GetAnalyticalModel()
#             # outer_loops=an_beam.GetLoops(DB.Structure.AnalyticalLoopType.External)
#             # inner_loops=an_beam.GetLoops(DB.Structure.AnalyticalLoopType.Internal)
#
#             xyz_ext_loops = []  # [curveloop_to_coords(c) for c in outer_loops]
#             xyz_int_loops = []  # [curveloop_to_coords(c) for c in inner_loops]
#
#             #			if lev is None: select_elements([beam])
#
#             params = famtype.GetParameters(BEAM_DEPTH_PARAMETER)
#             t = to_mm(params[0].AsDouble()) if len(params) > 0 else 0
#
#             params = famtype.GetParameters(BEAM_WIDTH_PARAMETER)
#             b = to_mm(params[0].AsDouble()) if len(params) > 0 else 0
#
#             bdict = {"unsorted loops": loop_coords, "analytical-extloops": xyz_ext_loops,
#                      "analytical-intloops": xyz_int_loops, "thickness": t, "width": b}
#             beam_list.append(bdict)
#             cnt += 1
# print
# "Found " + str(cnt) + " beams"
# master_dict = {"levels": level_list, "slabs": slab_list, "columns": column_list, "walls": wall_list, "beams": beam_list}
#
# outfile = open(OUTPUT_FILE, "wb")
# json.dump(master_dict, outfile)
# outfile.close()
#
# print
# "Execution finished!"