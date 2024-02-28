from Autodesk.Revit.DB import *
from pyrevit import DB, revit
import math

doc = __revit__.ActiveUIDocument.Document

active_view = doc.ActiveView

all_schedule_cols = []

#calculate character worth for alphanumeric sorting
def characterworth(string):
    val = 0.0
    counter = 1.0
    for x in string:
        val = val + ord(x)/counter*x.isdigit() + ord(x)/(255*counter)*x.isalpha()
        counter = counter * 10
    return val

class ScheduleColumn:
    def __init__(self,name):
        self.name = name
        self.number = characterworth(name)
        self.columns = []
        self.boundingbox = None

    # print parameters of col
    def full(self):
        print('Name: {self.name}\nName: {self.number}'.format(self=self))
        print('Columns:')
        for i in self.columns:
            print('> {i.Id}'.format(i=i))
    
    # Create bounding box and expand to all columns
    def columnsboundingbox(self):  
        bb_primary = self.columns[0].get_BoundingBox(None)
        min_x = bb_primary.Min.X
        min_y = bb_primary.Min.Y
        min_z = bb_primary.Min.Z
        max_x = bb_primary.Max.X
        max_y = bb_primary.Max.Y
        max_z = bb_primary.Max.Z

        for elem in self.columns:
            bb_max = elem.get_BoundingBox(None).Max
            max_x = max(bb_max.X,max_x)
            max_y = max(bb_max.Y,max_y)
            max_z = max(bb_max.Z,max_z)
            bb_min = elem.get_BoundingBox(None).Min
            min_x = min(bb_min.X,min_x)
            min_y = min(bb_min.Y,min_y)
            min_z = min(bb_min.Z,min_z)
        
        bb_max = XYZ(max_x,max_y,max_z)
        bb_min = XYZ(min_x,min_y,min_z)
        bb_primary.Max = bb_max
        bb_primary.Min = bb_min
        self.boundingbox = bb_primary

#get every column family
fec_structuralcols = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_StructuralColumns).WhereElementIsNotElementType()

# Filter out non-concrete families
all_concrete_cols = []
for column in fec_structuralcols:
    if "Concrete" in doc.GetElement(column.GetTypeId()).Family.Name:
        all_concrete_cols.append(column)

# Get guid (for faster searching) to get column mark no
guid_columnmarkno = all_concrete_cols[0].LookupParameter("Column Mark No").GUID

unique_marks = set([col.get_Parameter(guid_columnmarkno).AsString() for col in all_concrete_cols])

# Create column objects
for i in unique_marks:
    all_schedule_cols.append(ScheduleColumn(i))

for k in all_schedule_cols:
    for j in all_concrete_cols:
        if k.name == j.get_Parameter(guid_columnmarkno).AsString():
            k.columns.append(j)
    k.columnsboundingbox()

# get column angle
def angle_column(_col):
    xval = _col.GetTransform().BasisX.X
    yval = _col.GetTransform().BasisX.Y
    rot = round(math.atan2(yval,xval)*180/math.pi,0)
    if rot > 90:
        rot = rot-90
    elif rot <= -90:
        rot = rot + 180
    elif rot < 0:
        rot = rot + 90
    return rot

# get mode angle of columns
def angle_mode(_colcol):
    angles = []
    for i in _colcol.columns:
        if "Rectangular" in doc.GetElement(i.GetTypeId()).Family.Name:
            angles.append(angle_column(i))
    if angles == []:
        modeangle = 0
    else:
        modeangle = max(set(angles), key=angles.count)
    return modeangle

# create section view of columns
def get_section_viewfamily():
    return revit.doc.GetDefaultElementTypeId(DB.ElementTypeGroup.ViewTypeSection)

# set parameter value
def set_parameter_by_name(element, parameterName, value):
    element.LookupParameter(parameterName).Set(value)

section_type = get_section_viewfamily()

tempbb = all_schedule_cols[0].boundingbox

colviewtemplate = [v for v in FilteredElementCollector(doc).OfClass(View).ToElements() if v.Name == "SEC-SL"][0]

# section XX
tf = DB.Transform.Identity
tf.Origin = XYZ(0,0,0)
tf.BasisX = DB.XYZ.BasisY
tf.BasisY = DB.XYZ.BasisZ
tf.BasisZ = DB.XYZ.BasisX

section_box1 = DB.BoundingBoxXYZ()
section_box1.Transform = tf
section_box1.Min = XYZ(tempbb.Min.Y,tempbb.Min.Z,tempbb.Min.X)
section_box1.Max = XYZ(tempbb.Max.Y,tempbb.Max.Z,tempbb.Max.X)

# section YY
tf.BasisX = DB.XYZ.BasisZ
tf.BasisY = DB.XYZ.BasisX
tf.BasisZ = DB.XYZ.BasisY

section_box2 = DB.BoundingBoxXYZ()
section_box2.Transform = tf
section_box2.Min = XYZ(tempbb.Min.Z,tempbb.Min.X,tempbb.Min.Y)
section_box2.Max = XYZ(tempbb.Max.Z,tempbb.Max.X,tempbb.Max.Y)

t = Transaction(doc, 'create section')
t.Start()
secty = DB.ViewSection.CreateSection(revit.doc, section_type, section_box1)
sectx = DB.ViewSection.CreateSection(revit.doc, section_type, section_box2)
set_parameter_by_name(sectx,"View Name","Section XX")
set_parameter_by_name(secty,"View Name","Section YY")
secty.ViewTemplateId = colviewtemplate.Id
t.Commit()


# Set 3D view to boundingbox
# t = Transaction(doc, 'cropping view')
# t.Start()
# active_view.SetSectionBox(section_box1)
# t.Commit()

# ***********************************************************
# # Get geometry with default options
# def getangledgeometry(_colcol):
#     originaltransform = _colcol.columns[0].GetTransform()
#     rotatedtransform = originaltransform.CreateRotation(originaltransform.BasisZ,angle_mode(_colcol))

#     transformedgeometry = []

#     for i in _colcol.columns:
#         temp_geom = i.get_Geometry(Options())
#         temp_rotated = temp_geom.GetTransformed(rotatedtransform)
#         transformedgeometry.append(temp_rotated)
    
#     bb_rotated = getboundingboxlimits(transformedgeometry)
#     bbox_min = bb_rotated.Min
#     bbox_min = originaltransform.Inverse.OfPoint(bbox_min)
#     bbox_max = bb_rotated.Max
#     bbox_max = originaltransform.Inverse.OfPoint(bbox_max)

#     section_box1 = DB.BoundingBoxXYZ()
#     section_box1.Transform = rotatedtransform
#     section_box1.Min = bbox_min
#     section_box1.Max = bbox_max

#     return section_box1
# ***********************************************************


#get all sheets
fec_sheets = list(DB.FilteredElementCollector(doc)
                 .OfCategory(DB.BuiltInCategory.OST_Sheets)
                 .WhereElementIsNotElementType())
colsheets = []

for i in fec_sheets:
    if "COLUMN SCHEDULE" in i.Name:
        colsheets.append(i)


t = Transaction(doc, 'put on sheets')
t.Start()
tempvp = Viewport.Create(doc,colsheets[0].Id,secty.Id,XYZ(0,0,0))
t.Commit()

fec_titleblocks = list(DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsNotElementType().ToElements())

coltitleblocks = {}

for i in fec_titleblocks:
    for j in colsheets:
        if i.OwnerViewId == j.Id:
            coltitleblocks[j]=i

temptitleblock = coltitleblocks[colsheets[0]]

temptitleblock.get_BoundingBox(colsheets[0]).Min
temptitleblock.get_BoundingBox(colsheets[0]).Max

# def drawlines(pt1, pt2, sheet):
#     pt1 = XYZ(pt1.X,pt1.Y,0)
#     pt2 = XYZ(pt2.X,pt2.Y,0)
#     t = Transaction(doc, 'Draw Line')
#     t.Start()
#     linebb = Line.CreateBound(pt1,pt2)
#     doc.Create.NewDetailCurve(sheet,linebb)
#     t.Commit()

# tempsheet = colsheets[0]

# linebbmin = tempvp.get_BoundingBox(tempsheet).Min
# linebbmax = tempvp.get_BoundingBox(tempsheet).Max

# drawlines(linebbmin,linebbmax,tempsheet)