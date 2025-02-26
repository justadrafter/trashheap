__title__ = "Group & Create Point Heights"
__author__ = "Adam Shaw"

from revitfunctions.PT_funcs import (
    renumber_all_tendons,
    create_all_intermediate_points,
    populate_family_symbols,
    revit,
)

def main():
    populate_family_symbols()

    selection = revit.get_selection()

    with revit.Transaction("Create Intermediate Tendon Heights"):
        tendon_group = renumber_all_tendons(selection)
        create_all_intermediate_points(tendon_group)


if __name__ == "__main__":
    main()
