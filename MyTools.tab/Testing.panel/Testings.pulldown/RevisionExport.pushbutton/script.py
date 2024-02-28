"""Exports List of Revisions"""

from Autodesk.Revit import DB


doc = __revit__.ActiveUIDocument.Document

VAL_RevisionsToExlcude = ["??","HOLD","XX"]


def get_parameter_value_by_name(element, parameterName):
	return element.LookupParameter(parameterName).AsValueString()


# Creating collector instance and collecting all the walls from the model
_collector = DB.FilteredElementCollector(doc)\
                   .OfCategory(DB.BuiltInCategory.OST_Sheets)\
                   .WhereElementIsNotElementType()

ARR_all = []

for ELE_viewsheet in _collector:
    temp = []
    for ELE_revID in ELE_viewsheet.GetAllRevisionIds():
        ELE_rev = doc.GetElement(ELE_revID)
        VAL_desc = ELE_rev.Description
        
        if not any(x in VAL_desc for x in VAL_RevisionsToExlcude):
            temp = ([ELE_viewsheet.Name,ELE_viewsheet.SheetNumber,VAL_desc,ELE_rev.RevisionDate,ELE_viewsheet.GetRevisionNumberOnSheet(ELE_revID)])
    if temp:
        ARR_all.append(temp)

for x in ARR_all:
    print("*********************")
    print(x)
print("*********************")