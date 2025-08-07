# -*- coding: utf-8 -*-
"""Disallows framing joins at both ends of selected framing elements."""

__title__ = "Unjoins both ends of selected framing elements"
__author__ = "Adam"

from Autodesk.Revit import DB
from pyrevit import revit, forms, script

doc = revit.doc
uidoc = revit.uidoc

# Get selected elements
selection = [doc.GetElement(id) for id in uidoc.Selection.GetElementIds()]

# Filter for structural framing elements
framing_elements = [elem for elem in selection 
                    if elem.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_StructuralFraming)]

# Start a transaction
with revit.Transaction("Disallow Framing Joins at Both Ends"):
    # Iterate through selected framing elements
    for element in framing_elements:
        # Disallow join at start
        DB.Structure.StructuralFramingUtils.DisallowJoinAtEnd(element, 0)
        
        # Disallow join at end
        DB.Structure.StructuralFramingUtils.DisallowJoinAtEnd(element, 1)