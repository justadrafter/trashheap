# Necessary Imports:
import Autodesk.Revit.DB as DB

# Initialization:
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# Function to find a view by its name
def find_view_by_name(view_name):
    view_collector = DB.FilteredElementCollector(doc).OfClass(DB.View).WhereElementIsNotElementType()
    for view in view_collector:
        if view.Name == view_name:
            return view
    return None

# Function to create a new sheet
def create_new_sheet(sheet_name="New Sheet"):
    sheet = None
    sheet_collector = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet).WhereElementIsNotElementType()
    for sht in sheet_collector:
        if sht.Name == sheet_name:
            sheet = sht
            break
    if not sheet:
        title_block_types = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_TitleBlocks)
        title_block_type = title_block_types.FirstElement()
        sheet = DB.ViewSheet.Create(doc, title_block_type.Id)
        sheet.Name = sheet_name
    return sheet

# Function to place view on sheet corrected for 2D sheet space
def place_view_on_sheet(views, sheet):
    new_x = 24.5/304.8
    new_y = 0
    viewports = []
    
    for view in views:    
        # Create a new viewport at the specified location. 
        viewport = DB.Viewport.Create(doc, sheet.Id, view.Id, DB.XYZ(new_x, new_y, 0))

        # Get current box center
        box_center = viewport.GetBoxCenter()

        # Use GetBoxOutline to get the 2D boundary of the viewport
        outline = viewport.GetBoxOutline()
        min_point = outline.MinimumPoint
        max_point = outline.MaximumPoint

        # Calculate the width and height from the outline
        width = max_point.X - min_point.X
        height = max_point.Y - min_point.Y

        crop_box = view.CropBox
        width = (crop_box.Max.X - crop_box.Min.X)/100
        height = (crop_box.Max.Y - crop_box.Min.Y)/100

        #Set init values
        new_x = width + new_x
        new_y = height/2

        # Calculate new box center based on desired position
        new_box_center = DB.XYZ(new_x, new_y, box_center.Z)

        # Update the viewport's BoxCenter to move it
        viewport.SetBoxCenter(new_box_center) 
        viewports.append(viewport)

    return viewports

# Function to get the CropBox of a view and calculate dimensions
def get_cropbox_dimensions(view):
    # Ensure the view has a CropBox
    if view is None or not view.CropBoxActive:
        print("View is None or does not have an active CropBox.")
        return None, None, None

    # Get the CropBox as BoundingBoxXYZ
    crop_box = view.CropBox
    
    # Calculate width, depth, and height
    width = crop_box.Max.X - crop_box.Min.X
    depth = crop_box.Max.Y - crop_box.Min.Y
    height = crop_box.Max.Z - crop_box.Min.Z
    
    return width, depth, height

# Main
view_x_name = "C04_x"
view_y_name = "C04_y"

# Find views
view_x = find_view_by_name(view_x_name)
view_y = find_view_by_name(view_y_name)

with DB.Transaction(doc, "Create Column Schedule") as t:
    t.Start()
    # Create a new sheet
    new_sheet = create_new_sheet("New Sheet with Views")
    # Place view C01_x
    #place_view_on_sheet(view_x, new_sheet, X0+x_offset/100, Y0+y_offset/200)
    place_view_on_sheet([view_x,view_y], new_sheet)
    # Place view C01_y to the right of view C01_x
    #place_view_on_sheet(view_y, new_sheet, X0 + width_x, Y0)
    t.Commit()