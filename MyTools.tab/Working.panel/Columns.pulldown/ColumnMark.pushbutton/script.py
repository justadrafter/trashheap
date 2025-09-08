# Necessary Imports:
from Autodesk.Revit.DB import Outline, XYZ, Outline, BoundingBoxIntersectsFilter, BuiltInParameter, ElementParameterFilter, ParameterValueProvider, FilterStringRule, FilterStringContains, ElementId, LogicalOrFilter, ElementFilter
from pyrevit import revit, DB, forms
from System.Collections.Generic import List

# Initialization:
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
app = __revit__.Application
rvt_year = int(app.VersionNumber)

# Variables:
bb_z_fuzz = 2000/304.8  #Z search radius for overlapping cols
col_xy_fuzz = 1000/304.8 #X Y search radius for similar coordinates
column_family_types = ["Concrete", "PRECAST", "FRC"]
colprefix = "C"

class GCol:
    def __init__(self):
        self.columns = []
        self.elevations = []
        self.x_positions = []
        self.y_positions = []
        # Initialize sort orders for X, Y, Z with None
        self.xSortOrder = None
        self.ySortOrder = None
        self.zSortOrder = None
    
    def add_column(self, colId, elevation, x, y):
        self.columns.append(colId)
        self.elevations.append(elevation)
        self.x_positions.append(x)
        self.y_positions.append(y)

    @property
    def lowestElevation(self):
        return min(self.elevations) if self.elevations else 999999999

    @property
    def avgX(self):
        return sum(self.x_positions) / len(self.x_positions) if self.x_positions else 0
    
    @property
    def avgY(self):
        return sum(self.y_positions) / len(self.y_positions) if self.y_positions else 0

    # Methods to set sort orders
    def set_x_sort_order(self, order):
        self.xSortOrder = order

    def set_y_sort_order(self, order):
        self.ySortOrder = order

    def set_z_sort_order(self, order):
        self.zSortOrder = order

    def print_all_parameters(self):
        # Print the list parameters by looping through each
        for (cols,eles,x,y) in zip(self.columns,self.elevations,self.x_positions,self.y_positions):
            print("Columns: {} Elevations: {} X Positions: {} Y Positions: {}".format(cols,eles,x,y))
        # Print sort orders directly since they are single values
        print("X Sort Order: ", self.xSortOrder)
        print("Y Sort Order: ", self.ySortOrder)
        print("Z Sort Order: ", self.zSortOrder)

#Return columns intersecting the input col boundingbox 
def bbox_extends_and_intersects(element_id):
    element = doc.GetElement(element_id)
    bbox = element.get_BoundingBox(None)
    
    # Assuming 'extension' is defined elsewhere, adjust as necessary
    min_point = XYZ(bbox.Min.X, bbox.Min.Y, bbox.Min.Z - bb_z_fuzz)
    max_point = XYZ(bbox.Max.X, bbox.Max.Y, bbox.Max.Z + bb_z_fuzz)
    outline = Outline(min_point, max_point)
    bbox_filter = BoundingBoxIntersectsFilter(outline)

    collector = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_StructuralColumns).WhereElementIsNotElementType().WherePasses(family_name_filter).WherePasses(bbox_filter).ToElements()

    # Return only elements not already processed
    return [element for element in collector]

#Loop through columns to return a list of connected columns per input column
def find_connected_elements(start_element_id):
    processed_ids = set([start_element_id])
    to_process = [start_element_id]
    while to_process:
        current_id = to_process.pop()
        connectedall = bbox_extends_and_intersects(current_id)
        connected = [elem for elem in connectedall if elem not in processed_ids]
        for element in connected:
            if element.Id not in processed_ids:
                processed_ids.add(element.Id)
                to_process.append(element.Id)
    return processed_ids

def create_family_name_filter(keywords):
    param_id = ElementId(BuiltInParameter.ALL_MODEL_FAMILY_NAME)
    f_param = ParameterValueProvider(param_id)
    rules = List[ElementFilter]()  # Specify the list type as ElementFilter

    for keyword in keywords:
        filter_contains = FilterStringContains()
        if rvt_year < 2023:
            f_rule = FilterStringRule(f_param, filter_contains, keyword, True)
        else:
            f_rule = FilterStringRule(f_param, filter_contains, keyword)
        epf = ElementParameterFilter(f_rule)
        rules.Add(epf)  # Add the ElementParameterFilter, which is an ElementFilter

    # Combine filter rules into a single filter using a logical OR
    return LogicalOrFilter(rules)

family_name_filter = create_family_name_filter(column_family_types)

sel_ids = uidoc.Selection.GetElementIds()

base = (DB.FilteredElementCollector(doc, List[DB.ElementId](sel_ids)) if sel_ids else DB.FilteredElementCollector(doc))

concretecols_collection = (base.OfCategory(DB.BuiltInCategory.OST_StructuralColumns).WhereElementIsNotElementType().WherePasses(family_name_filter).ToElements())

# Preprocess columns for efficient access
columnData = {}
levelElevations = {}
cols_to_process = set()
for col in concretecols_collection:
    levelId = col.LevelId
    if levelId not in levelElevations:
        level = doc.GetElement(levelId)
        levelElevations[levelId] = level.Elevation
    bbox = col.get_BoundingBox(None)
    minPoint = bbox.Min
    maxPoint = bbox.Max
    cols_to_process.add(col.Id)
    columnData[col.Id] = (levelElevations[levelId], (minPoint.X + maxPoint.X) / 2, (minPoint.Y + maxPoint.Y) / 2)

# Create Gcols and populate all the properties. Loop through and find all intersection columns
gcols = []
totallen = len(cols_to_process)
with forms.ProgressBar(title='Grouping & Marking Columns') as pb:
    while cols_to_process:
        current_col_id = cols_to_process.pop()
        gcol = GCol()
        cols_processed = find_connected_elements(current_col_id)
        for col in cols_processed:
            elevation, x, y = columnData[col]
            gcol.add_column(col, elevation, x, y)
        cols_to_process.difference_update(cols_processed) 
        gcols.append(gcol)
        pb.update_progress(totallen-len(cols_to_process), totallen)

# Sort GCol instances by their lowest elevation
gcols_sorted_by_elevation = sorted(gcols, key=lambda gcol: gcol.lowestElevation)

# Use a dictionary to remember the zSortOrder assigned to each elevation
elevation_to_z_sort_order = {}
z_sort_order = 0

for gcol in gcols_sorted_by_elevation:
    # Assign zSortOrder based on elevation, reusing the same zSortOrder for identical elevations
    if gcol.lowestElevation not in elevation_to_z_sort_order:
        elevation_to_z_sort_order[gcol.lowestElevation] = z_sort_order
        z_sort_order += 1
    gcol.set_z_sort_order(elevation_to_z_sort_order[gcol.lowestElevation])


# First, sort GCol instances by their average Y-coordinate
gcols_sorted_by_avgY = sorted(gcols, key=lambda gcol: gcol.avgY)

# Initialize variables for tracking the current group's base Y value and the next ySortOrder value
base_y_value = gcols_sorted_by_avgY[0].avgY
y_sort_order = 0

for gcol in gcols_sorted_by_avgY:
    # Check if this GCol's avgY is within 1 meter (3.28084 feet) of the base_y_value
    if abs(gcol.avgY - base_y_value) >= col_xy_fuzz:
        base_y_value = gcol.avgY
        y_sort_order += 1
    
    # Assign the current ySortOrder to the GCol
    gcol.set_y_sort_order(y_sort_order)

# Sort GCol instances by their average X-coordinate
gcols_sorted_by_avgX = sorted(gcols, key=lambda gcol: gcol.avgX)

# Initialize variables for tracking the current group's base Y value and the next ySortOrder value
base_x_value = gcols_sorted_by_avgX[0].avgX
x_sort_order = 0

for gcol in gcols_sorted_by_avgX:
    # Check if this GCol's avgX is within the base_x_value
    if abs(gcol.avgX - base_x_value) >= col_xy_fuzz:
        base_x_value = gcol.avgX
        x_sort_order += 1

    # Assign the current xSortOrder to the GCol
    gcol.set_x_sort_order(x_sort_order)

gcols_sorted = sorted(gcols, key=lambda gcol: (gcol.zSortOrder, gcol.ySortOrder, gcol.xSortOrder))
with revit.Transaction("Renumber Column Groups"):
    markNo = 1
    paddingnum = len(str(len(gcols_sorted)+20))
    pmarkNo = colprefix + str(markNo).zfill(paddingnum)
    for gcol in gcols_sorted:
        for colId in gcol.columns:
            col = doc.GetElement(colId)
            param = col.LookupParameter("Column Mark No")
            if param and not param.IsReadOnly:
                param.Set(str(pmarkNo))
        markNo += 1
        pmarkNo = colprefix + str(markNo).zfill(paddingnum)