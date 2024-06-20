from Autodesk.Revit.DB import (
    FilteredElementCollector,
    CADLinkType,
)
from pyrevit import forms, revit, script

__title__ = "Update DWG paths"
__author__ = "Adam Shaw"


def select_cadlinktypes():
    # Collect all CADLinkType elements in the project
    cadlinktypes = FilteredElementCollector(revit.doc).OfClass(CADLinkType).ToElements()

    # Create a dictionary with CADLinkType names and their corresponding elements
    cadlinktype_dict = {
        cadlinktype.Category.Name: cadlinktype for cadlinktype in cadlinktypes
    }

    # Prompt the user to select the CADLinkTypes to load
    selected_cadlinktypes = forms.SelectFromList.show(
        sorted(cadlinktype_dict.keys()),
        title="Select CADLinkTypes to Load",
        multiselect=True,
    )

    # Return the selected CADLinkType elements
    return (
        [cadlinktype_dict[name] for name in selected_cadlinktypes]
        if selected_cadlinktypes
        else []
    )


def main():
    # Get the selected CADLinkTypes
    selected_link_instances = select_cadlinktypes()

    if not selected_link_instances:
        script.exit("No CADLinkTypes selected. Exiting script.")

    # Prompt the user to select the new folder for linked DWG files
    new_folder = forms.pick_folder(title="Select the new folder for linked DWG files")

    if not new_folder:
        script.exit("No folder selected. Exiting script.")

    print("Repathing to " + new_folder+"\\...")

    # Iterate over each linked DWG instance
    with revit.Transaction("Update Linked DWG Locations"):
        for instance in selected_link_instances:
            filename = instance.Category.Name
            fullfilepath = new_folder + "\\" + filename
            try:
                instance.LoadFrom(fullfilepath)
                print(filename + " SUCCEEDED")
            except:
                print(filename + " FAILED")


if __name__ == "__main__":
    main()
