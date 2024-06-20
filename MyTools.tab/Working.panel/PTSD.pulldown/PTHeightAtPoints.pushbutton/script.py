__title__ = "Get Height at Point"
__author__ = "Adam Shaw"

from revitfunctions.PT_funcs import revit,populate_family_symbols,get_bottom_and_top_RL
from revitfunctions.PT_funcs import POINT_TYPE


def main():
    populate_family_symbols()

    selection = revit.get_selection()

    filtered_selection = [element for element in selection if POINT_TYPE in element.Name]
    if filtered_selection:
        for elem in filtered_selection:
            heightRL = int(elem.LookupParameter("Height").AsValueString())
            print("***** Height Element {} *****".format(heightRL))
            btmahd,topahd = get_bottom_and_top_RL(elem.Location.Point)
            if btmahd is None or topahd is None:
                print("Error with heights")
            else:
                print("Height RL:    {:0.0f}".format(heightRL+btmahd))
                print("Bottom AHD:   {:0.0f}".format(btmahd))
                print("Top AHD:      {:0.0f}".format(topahd))
                print("Difference of {:0.0f}".format(topahd-btmahd))

if __name__ == "__main__":
    main()
