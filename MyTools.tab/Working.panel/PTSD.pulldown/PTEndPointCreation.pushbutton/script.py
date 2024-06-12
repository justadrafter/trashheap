__title__ = "Create End Heights"
__author__ = "Adam Shaw"

from revitfunctions.PT_funcs import create_tendon_heights, revit, populate_family_symbols


def main():
    populate_family_symbols()

    selection = revit.get_selection()

    with revit.Transaction("Create End Tendon Heights"):
        for x in selection:
            create_tendon_heights(x)


if __name__ == "__main__":
    main()
