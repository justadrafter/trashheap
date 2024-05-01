"""
Duplicate Floor Type with New Thickness

This script asks for a number input and duplicates the selected floor type.
It retrieves the current floor type, duplicates the element type, updates the thickness
of the first layer in the compound structure to the input value, and renames the type name.

Usage:
1. Select one or more floor elements in the Revit project.
2. Run this script.
3. Enter the desired thickness for the duplicated floor type.
4. The script will create a new floor type with the specified thickness.
"""

from pyrevit import revit, DB, forms
from pyrevit.revit.db import query

__title__ = "Duplicate Floor Type"
__author__ = "Adam Shaw"


def get_selected_floors():
    """
    Retrieve the selected floor elements.
    
    Returns:
        list[DB.Floor]: The selected floor elements.
    """
    doc = revit.doc
    uidoc = revit.uidoc
    
    selected_floors = [doc.GetElement(elId) for elId in uidoc.Selection.GetElementIds()
                       if isinstance(doc.GetElement(elId), DB.Floor)]
    
    if not selected_floors:
        forms.alert("No floor elements selected. Please select one or more floors and run the script again.")
    
    return selected_floors


def duplicate_floor_type(floor, new_thickness):
    """
    Duplicate the floor type with the specified thickness.
    
    Args:
        floor (DB.Floor): The floor element to duplicate the type from.
        new_thickness (float): The thickness for the duplicated floor type.
    """
    floor_type = floor.FloorType
    floor_name = floor.Name
    thickness_param = floor.get_Parameter(DB.BuiltInParameter.FLOOR_ATTR_THICKNESS_PARAM)

    floor_thickness = round(thickness_param.AsDouble() * 304.8, 0)
    thickness_str = str(int(floor_thickness))
    thickness_index = floor_name.find(thickness_str)

    if thickness_index != -1:
        new_floor_name = floor_name[:thickness_index] + str(int(new_thickness)) + \
            floor_name[thickness_index + len(thickness_str):]
    else:
        new_floor_name = floor_name + " - " + str(int(new_thickness))

    existing_floor_types = query.get_family_symbol("Floor", new_floor_name)

    if existing_floor_types:
        return existing_floor_types[0]
    else:
        new_floor_type = floor_type.Duplicate(new_floor_name)
        compound_structure = new_floor_type.GetCompoundStructure()
        if compound_structure and compound_structure.LayerCount > 0:
            compound_structure.SetLayerWidth(0, new_thickness / 304.8)
            new_floor_type.SetCompoundStructure(compound_structure)
        return new_floor_type


def main():
    """
    Main function to execute the script logic.
    """
    selected_floors = get_selected_floors()
    
    if selected_floors:
        new_thickness = forms.ask_for_string(default='', prompt='Enter the desired thickness for the duplicated floor type:', title='Duplicate Floor Type')
        
        if new_thickness:
            try:
                new_thickness = float(new_thickness)
                with revit.Transaction("Duplicate Floor Types"):
                    for floor in selected_floors:
                        floor.FloorType = duplicate_floor_type(floor, new_thickness)
            except ValueError:
                forms.alert("Invalid thickness value. Please enter a valid number.")


if __name__ == "__main__":
    main()