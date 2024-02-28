import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document

# get all the importinstances in a revit file
importInstances = FilteredElementCollector(doc).OfClass(ImportInstance).ToElements()

# get name of category of importinstance
for importInstance in importInstances:
    print(importInstance.Category.Name)

#change the importinstance colours in a view template
for importInstance in importInstances:
    importInstance.SetCategoryColor(Color(255, 0, 0))
