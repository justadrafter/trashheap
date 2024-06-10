"""
This script moves the selected foundations to the origin point of their nearest selected column,
considering only the X and Y coordinates. The Z coordinate remains unchanged.

Usage:
1. Select the foundations and columns in the Revit model.
2. Ensure the number of columns is >= the number of foundations.
2. Run this script.
"""

from Autodesk.Revit.DB import BuiltInCategory, Transaction, XYZ
from System.Collections.Generic import List

from pyrevit import revit, DB, forms

__title__ = "Align to Cols"
__author__ = "Adam Shaw"


def get_origin_point(element):
    """
    Get the origin point of an element.
    
    Args:
        element (DB.Element): The element to get the origin point of.
        
    Returns:
        DB.XYZ: The origin point of the element.
    """
    return element.Location.Point


def find_nearest_column(foundation_origin, columns):
    """
    Find the nearest column to the given foundation origin point.
    
    Args:
        foundation_origin (DB.XYZ): The origin point of the foundation.
        columns (List[DB.Element]): The list of column elements.
        
    Returns:
        DB.Element: The nearest column element to the foundation origin point.
    """
    nearest_column = None
    min_distance = float('inf')
    
    for column in columns:
        column_origin = get_origin_point(column)
        distance = XYZ(foundation_origin.X - column_origin.X, foundation_origin.Y - column_origin.Y, 0).GetLength()
        if distance < min_distance:
            min_distance = distance
            nearest_column = column
            
    return nearest_column


def main():
    """
    Main function to execute the script logic.
    """
    doc = revit.doc
    uidoc = revit.uidoc
    
    selected_ids = uidoc.Selection.GetElementIds()
    
    foundations = [doc.GetElement(elem_id) for elem_id in selected_ids 
                   if doc.GetElement(elem_id).Category.Id.IntegerValue == int(BuiltInCategory.OST_StructuralFoundation)]
    columns = [doc.GetElement(elem_id) for elem_id in selected_ids 
               if doc.GetElement(elem_id).Category.Id.IntegerValue == int(BuiltInCategory.OST_StructuralColumns)]
    
    if not foundations:
        forms.alert("No foundations selected. Please select foundations and columns, then run the script again.")
        return
    
    if not columns:
        forms.alert("No columns selected. Please select foundations and columns, then run the script again.")
        return
    
    with revit.Transaction("Align Foundations to Columns"):
        for foundation in foundations:
            foundation_origin = get_origin_point(foundation)
            nearest_column = find_nearest_column(foundation_origin, columns)
            if nearest_column:
                nearest_column_origin = get_origin_point(nearest_column)
                move_vector = XYZ(nearest_column_origin.X - foundation_origin.X, 
                                  nearest_column_origin.Y - foundation_origin.Y, 
                                  0)
                foundation.Location.Move(move_vector)


if __name__ == "__main__":
    main()