__title__ = "Filter HIGHs"
__author__ = "Adam Shaw"

from pyrevit import revit


def filter_elements(selection):
    high_elements = []
    for element in selection:
        if (
            element.LookupParameter("HIGH").AsInteger() == 1
            and element.LookupParameter("LOW").AsInteger() == 0
            and element.LookupParameter("END").AsInteger() == 0
        ):
            high_elements.append(element)
    return high_elements


def main():
    selection = revit.get_selection()
    if not selection:
        print("No elements selected. Please select elements and run the script again.")
        return

    elements = filter_elements(selection)
    if elements:
        revit.get_selection().set_to([elem.Id for elem in elements])
    else:
        print("No elements with 'HIGH' parameter equal to 1 found.")


if __name__ == "__main__":
    main()
