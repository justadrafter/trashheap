# -*- coding: utf-8 -*-
"""
This script exports the selected structural column elements with a structural material containing 'insitu', 'precast', 'concrete', or 'steel' into a CSV file.

To use this script, follow these steps:

Select one or more structural column elements in the Revit project.
Run the script.
Select the location to save the CSV file.
The script will create a CSV file with the following information:

GUID
Column Mark No
X coordinate
Y coordinate
Z coordinate
Type name
B value
H value
"""

import csv
import os
from pyrevit import revit, DB, forms

title = "Export CSV"
author = "Adam Shaw"

doc = revit.doc


def get_column_info(column):
    """
    Get the information for the given structural column element.
    Args:    column (DB.FamilyInstance): The structural column element.
    Returns:    dict: A dictionary containing the column information.
    """
    info = {
        "GUID": column.UniqueId,
        "ID": column.Id,
        "Column Mark No": column.LookupParameter("Column Mark No").AsString(),
        "X": round(column.Location.Point.X * 304.8, 2),
        "Y": round(column.Location.Point.Y * 304.8, 2),
        "Z Base": round(
            (
                column.Document.GetElement(
                    column.LookupParameter("Base Level").AsElementId()
                ).ProjectElevation
                + column.LookupParameter("Base Offset").AsDouble()
            )
            * 304.8,
            2,
        ),
        "Z Top": round(
            (
                column.Document.GetElement(
                    column.LookupParameter("Top Level").AsElementId()
                ).ProjectElevation
                + column.LookupParameter("Top Offset").AsDouble()
            )
            * 304.8,
            2,
        ),
        "Type Name": column.Symbol.Family.Name,
        "Shape": "Rectangle"
        if "rectangular" in column.Symbol.Family.Name.lower()
        else "Circular"
        if "circular" in column.Symbol.Family.Name.lower()
        else "Custom",
    }
    try:
        info["B"] = round(column.Symbol.LookupParameter("b").AsDouble() * 304.8, 0)
    except Exception:
        try:
            info["B"] = round(column.Symbol.LookupParameter("Width / Ø (Type)").AsDouble() * 304.8, 0)
        except Exception:
            info["B"] = "0"

    try:
        info["H"] = round(column.Symbol.LookupParameter("h").AsDouble() * 304.8, 0)
    except Exception:
        try:
            info["H"] = round(column.Symbol.LookupParameter("Length (Type)").AsDouble() * 304.8, 0)
        except Exception:
            info["H"] = "0"

    return info


def main():
    selection = revit.get_selection()

    if not selection:
        # Select all structural columns if nothing is selected
        all_columns = (
            DB.FilteredElementCollector(doc)
            .OfClass(DB.FamilyInstance)
            .OfCategory(DB.BuiltInCategory.OST_StructuralColumns)
            .ToElements()
        )
        selection = [
            elem
            for elem in all_columns
            if elem.StructuralType == DB.Structure.StructuralType.Column
        ]

    if not selection:
        forms.alert("No structural column elements found in the project.")
        return

    filtered_columns = [
        column
        for column in selection
        if any(
            keyword in column.Symbol.Family.Name.lower()
            for keyword in ["insitu", "precast", "concrete", "steel"]
        )
    ]

    if not filtered_columns:
        forms.alert(
            "No structural column elements with a structural material containing 'insitu', 'precast', 'concrete', or 'steel' found. Please ensure appropriate structural column elements are present in the project."
        )
        return

    csv_file_path = forms.save_file(file_ext="csv")

    if not csv_file_path:
        return

    with open(csv_file_path, "wb") as csv_file:
        fieldnames = [
            "GUID",
            "ID",
            "Column Mark No",
            "X",
            "Y",
            "Z Base",
            "Z Top",
            "Type Name",
            "Shape",
            "B",
            "H",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for column in filtered_columns:
            info = get_column_info(column)
            writer.writerow(info)

    forms.alert("CSV file saved to: " + csv_file_path)

    # Open the CSV file
    os.startfile(csv_file_path)


if __name__ == "__main__":
    main()
