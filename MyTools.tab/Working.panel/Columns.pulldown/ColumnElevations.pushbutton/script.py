from Autodesk.Revit.DB import Transaction, XYZ, BuiltInCategory, ElementId, BuiltInParameter, ParameterValueProvider, ElementFilter, FilterStringContains, FilterStringRule, ElementParameterFilter, LogicalOrFilter, FilteredElementCollector, ViewFamilyType
from pyrevit import revit, DB
from collections import defaultdict
from System.Collections.Generic import List

# Initialization:
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
app = __revit__.Application
rvt_year = int(app.VersionNumber)

# Variables:
view_offset = 1200/304.8
column_family_types = ["Concrete", "PRECAST", "FRC"]

# Get SEC-COL viewtype:
section_types = FilteredElementCollector(revit.doc).OfClass(ViewFamilyType).ToElements()
section_type = next((st.Id for st in section_types if st.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString() == "SEC-COL"),None)

def create_secs(in_bb,mark):
    # Get the bounding box of the column
    min_point = in_bb.Min
    max_point = in_bb.Max
    
    # Determine the mid-point and height of the column
    midpoint = XYZ((min_point.X + max_point.X) / 2, (min_point.Y + max_point.Y) / 2, (min_point.Z + max_point.Z)/2)
    height = max_point.Z - min_point.Z

    # Determine lengths to decide directions and adjust for longest and shortest faces
    length_x = max_point.X - min_point.X
    length_y = max_point.Y - min_point.Y
 
    up = XYZ.BasisZ
    
    direction_x = XYZ.BasisX
    viewdir_x = direction_x.CrossProduct(up).Normalize()
    transform_x = DB.Transform.Identity
    transform_x.Origin = midpoint
    transform_x.BasisX = direction_x
    transform_x.BasisY = up
    transform_x.BasisZ = viewdir_x
    
    direction_y = XYZ.BasisY
    viewdir_y = direction_y.CrossProduct(up).Normalize()
    transform_y = DB.Transform.Identity
    transform_y.Origin = midpoint
    transform_y.BasisX = direction_y
    transform_y.BasisY = up
    transform_y.BasisZ = viewdir_y

    # Define the section box size
    bbox_min_x = XYZ(-length_x/2-view_offset,-height/2-view_offset,-length_y/2)
    bbox_max_x = XYZ(length_x/2+view_offset,height/2+view_offset,length_y/2)

    bbox_min_y = XYZ(-length_y/2-view_offset,-height/2-view_offset,-length_x/2)
    bbox_max_y = XYZ(length_y/2+view_offset,height/2+view_offset,length_x/2)

    section_box_x = DB.BoundingBoxXYZ()
    section_box_x.Transform = transform_x
    section_box_x.Min = bbox_min_x
    section_box_x.Max = bbox_max_x

    section_box_y = DB.BoundingBoxXYZ()
    section_box_y.Transform = transform_y
    section_box_y.Min = bbox_min_y
    section_box_y.Max = bbox_max_y
    
    # Create section view
    secn_x = DB.ViewSection.CreateSection(revit.doc, section_type, section_box_x)
    secn_x.Name = "{}_x".format(mark)
    secn_y = DB.ViewSection.CreateSection(revit.doc, section_type, section_box_y)
    secn_y.Name = "{}_y".format(mark)

def get_combined_bb(selection):
    # Initialize the min and max points
    element_init = selection[0]
    bb_init = element_init.get_BoundingBox(None)
    min_point = bb_init.Min
    max_point = bb_init.Max

    for id in selection:
        # Get the element's bounding box
        bb = id.get_BoundingBox(None)
        if bb:  # If the element has a bounding box
            # Update min and max points directly without cloning or comparing each time
            min_point = XYZ(min(min_point.X, bb.Min.X), min(min_point.Y, bb.Min.Y), min(min_point.Z, bb.Min.Z))
            max_point = XYZ(max(max_point.X, bb.Max.X), max(max_point.Y, bb.Max.Y), max(max_point.Z, bb.Max.Z))
    bb.Min = min_point
    bb.Max = max_point
    return (bb)

def create_family_name_filter(keywords):
    """Creates a filter to find elements whose family names contain any of the specified keywords."""
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
concretecols_collection = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_StructuralColumns).WhereElementIsNotElementType().WherePasses(family_name_filter)

#Main:
selected_ids = uidoc.Selection.GetElementIds()
selected_columns = [doc.GetElement(id) for id in selected_ids if doc.GetElement(id).Category.Id.IntegerValue == int(BuiltInCategory.OST_StructuralColumns)]
if len(selected_columns) == 0:
    selected_columns = concretecols_collection

# Grouping columns by 'Column Mark No'
columns_by_mark = defaultdict(list)
for column in selected_columns:
    mark_no = column.LookupParameter('Column Mark No').AsString()
    columns_by_mark[mark_no].append(column)

# Running get_combined_bb for each group
t = Transaction(revit.doc, 'Create Column XY Sections')
t.Start()

for mark_no, columns in columns_by_mark.items():
    cbb = get_combined_bb(columns)
    create_secs(cbb,mark_no)

t.Commit()