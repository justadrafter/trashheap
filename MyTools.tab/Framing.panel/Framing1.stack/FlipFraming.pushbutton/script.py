from pyrevit import revit, DB, script

__title__ = "Flip Framing"
__author__ = "Adam Shaw"

SCRIPT_OUTPUT = script.get_output()
doc = revit.doc


def flip_framing_ends():
    # Get the current selection
    selection = revit.get_selection()
    failed_elements = []

    # Start a transaction
    with revit.Transaction("Flip Framing Ends"):
        for element in selection:
            # Check if the element is a structural framing
            if isinstance(
                element, DB.FamilyInstance
            ) and element.Category.Id == DB.ElementId(
                DB.BuiltInCategory.OST_StructuralFraming
            ):
                try:
                    # Check if ends can be flipped
                    if DB.Structure.StructuralFramingUtils.CanFlipEnds(element):
                        DB.Structure.StructuralFramingUtils.FlipEnds(element)
                    else:
                        failed_elements.append(element)
                except Exception as e:
                    failed_elements.append(element)

    if failed_elements:
        print("Failed to flip framing members: {}".format(
            ", ".join([SCRIPT_OUTPUT.linkify(elem.Id) for elem in failed_elements])
        ))


if __name__ == "__main__":
    flip_framing_ends()
