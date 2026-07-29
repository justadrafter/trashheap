# -*- coding: utf-8 -*-
"""
Disallow framing joins at both ends of selected structural framing elements.

Usage:
1. Select one or more structural framing elements.
2. Run the script.
"""

from Autodesk.Revit import DB
from pyrevit import revit

__title__ = "Unjoin Ends"
__author__ = "Adam Shaw"

framing_category = int(
    DB.BuiltInCategory.OST_StructuralFraming
)

framing_elements = [
    element for element in revit.get_selection()
    if element.Category
    and element.Category.Id.Value == framing_category
]

with revit.Transaction("Disallow Framing Joins at Both Ends"):
    for element in framing_elements:
        DB.Structure.StructuralFramingUtils.DisallowJoinAtEnd(
            element,
            0
        )
        DB.Structure.StructuralFramingUtils.DisallowJoinAtEnd(
            element,
            1
        )