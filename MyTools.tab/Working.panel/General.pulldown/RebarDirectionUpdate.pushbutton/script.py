"""
Returns the XY direction vector of each selected structural Rebar.
Sets instance parameter "Reinforcement Direction (Instance)" to "X" or "Y".
Assumes the active view is a structural plan.
"""

__title__ = "Set the Reinforcement Direction (Instance) parameter of selected Rebars"

from pyrevit import revit, DB, forms
import math

doc = revit.doc

def get_xy_direction(rebar):
    """
    Given a Rebar element, return the normalized direction vector (X, Y) 
    of its first centerline segment.
    """
    if not isinstance(rebar, DB.Structure.Rebar):
        return None

    curves = rebar.GetCenterlineCurves(
        True,   # adjustForSelfIntersection
        False,  # suppressHooks
        False,  # suppressBendRadius
        DB.Structure.MultiplanarOption.IncludeOnlyPlanarCurves,
        0       # barPositionIndex
    )

    if not curves or curves.Count == 0:
        return None

    curve = curves[0]
    try:
        start = curve.GetEndPoint(0)
        end = curve.GetEndPoint(1)
    except:
        return None

    dx = end.X - start.X
    dy = end.Y - start.Y
    length = math.sqrt(dx**2 + dy**2)
    if length == 0:
        return None

    return (dx/length, dy/length)

def set_direction_parameter(rebar, direction):
    """
    Sets the instance parameter "Reinforcement Direction (Instance)" to "X" or "Y".
    """
    param = rebar.LookupParameter("Reinforcement Direction (Instance)")
    if param and param.StorageType == DB.StorageType.String and not param.IsReadOnly:
        param.Set(direction)

def main():
    selection = revit.get_selection()

    if not selection:
        forms.alert("No elements selected. Please select rebar elements.", exitscript=True)

    updated = []

    with revit.Transaction("Set Reinforcement Direction"):
        for i, elem in enumerate(selection):
            vec = get_xy_direction(elem)
            if vec:
                dominant = "X" if abs(vec[0]) >= abs(vec[1]) else "Y"
                set_direction_parameter(elem, dominant)
                updated.append((i + 1, dominant))
    
    if not updated:
        print("No valid Rebar directions found or parameters not set.")

if __name__ == "__main__":
    main()
