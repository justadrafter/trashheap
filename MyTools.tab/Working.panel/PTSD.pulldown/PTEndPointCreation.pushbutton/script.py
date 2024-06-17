__title__ = "Create End Heights"
__author__ = "Adam Shaw"

from revitfunctions.PT_funcs import create_tendon_heights, revit, populate_family_symbols, TENDON_TYPE


def main():
    populate_family_symbols()

    selection = revit.get_selection()

    filtered_selection = [element for element in selection if TENDON_TYPE in element.Name]

    with revit.Transaction("Create End Tendon Heights"):
        for elem in filtered_selection:
            create_tendon_heights(elem)


if __name__ == "__main__":
    main()
