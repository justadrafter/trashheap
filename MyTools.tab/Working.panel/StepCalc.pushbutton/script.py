from pyrevit import revit, DB

doc = __revit__.ActiveUIDocument.Document

def get_parameter_value_by_name(element, parameterName):
	return element.LookupParameter(parameterName).AsValueString()

selection = revit.get_selection()

slaba_ssl = float(get_parameter_value_by_name(selection[0],"Elevation at Top"))
slaba_thk = float(get_parameter_value_by_name(selection[0],"Thickness"))
slabb_ssl = float(get_parameter_value_by_name(selection[1],"Elevation at Top"))
slabb_thk = float(get_parameter_value_by_name(selection[1],"Thickness"))

if slaba_ssl > slabb_ssl:
	overalldepth = slaba_ssl - slabb_ssl + slabb_thk
	totopsoffit = overalldepth - slaba_thk
	totoplower = slaba_ssl - slabb_ssl
else:
	overalldepth = slabb_ssl - slaba_ssl + slaba_thk
	totopsoffit = overalldepth - slabb_thk
	totoplower = slabb_ssl - slaba_ssl

print('{0}{1:>5.0f}'.format('Overall Depth:',overalldepth))
print('{0}{1:>5.0f}'.format('To Top Soffit:',totopsoffit))
print('{0}{1:>5.0f}'.format('To Top Lower:',totoplower))

# import clr

# # Import Revit API
# clr.AddReference('RevitAPI')
# from Autodesk.Revit.DB import *

# # Import Revit UI API
# clr.AddReference('RevitAPIUI')
# from Autodesk.Revit.UI.Selection import ObjectType

# uidoc = __revit__.ActiveUIDocument
# doc = uidoc.Document

# # Prompt the user to select a floor
# try:
#     reference = uidoc.Selection.PickObject(ObjectType.Element, "Select a floor.")
#     floor = doc.GetElement(reference.ElementId)
# except:
#     print("Selection canceled or no valid floor was selected.")
#     exit()

# # Retrieve the sketch for the floor
# collector = FilteredElementCollector(doc).OfClass(Sketch).WhereElementIsNotElementType()
# sketches = list(collector)
# floor_sketch = None
# for sk in sketches:
#     if sk.OwnerId == floor.Id:
#         floor_sketch = sk
#         break

# # Assuming the floor has a planar face, let's get a sketch plane from it
# levelId = floor.LevelId

# with Transaction(doc, 'Draw Model Lines') as t:
#     t.Start()
#     sketchPlane = SketchPlane.Create(doc, levelId)
#     # Access the Creation class
#     creation = doc.Create
#     # Iterate through curves and create model lines
#     for curve_loop in floor_sketch.Profile:
#         for curve in curve_loop:
#             # Create a model line from each curve, using our new sketchPlane
#             creation.NewModelCurve(curve, sketchPlane)
#     t.Commit()