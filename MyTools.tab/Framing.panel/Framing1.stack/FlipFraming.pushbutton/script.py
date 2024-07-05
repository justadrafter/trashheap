from pyrevit import revit, DB, script

__title__ = "Flip Framing"
__author__ = "Adam Shaw"

SCRIPT_OUTPUT = script.get_output()

doc = revit.doc

def flip_framing_ends():
    # Get the current selection
    selection = revit.get_selection()
    results = []
    # Start a transaction
    with revit.Transaction("Flip Framing Ends"):
        for element in selection:
            # Check if the element is a structural framing
            if isinstance(element, DB.FamilyInstance) and element.Category.Id == DB.ElementId(DB.BuiltInCategory.OST_StructuralFraming):
                results.append(element.flipFacing())
        if False in results:
            print("Failed to flip these members: ")
            for result in results:
                if not result:
                    print(SCRIPT_OUTPUT.linkify(element.Id))

if __name__ == "__main__":
    flip_framing_ends()