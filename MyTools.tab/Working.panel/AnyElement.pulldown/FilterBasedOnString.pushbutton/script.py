"""
Filters the current selection based on a text input for the name of the element.
- If the input string starts with "!", the script keeps elements whose name does not contain the subsequent text.
- If the input string does not start with "!", the script keeps elements whose name contains the input text.

Instructions:
1. Select elements in the Revit project.
2. Run this script.
3. Enter the desired element name or a part of the name in the input dialog.
   - To exclude elements containing the text, start the input with "!".
4. The script will filter the selection based on the input criteria.
"""

from pyrevit import revit, forms

__title__ = "Filter Selection by Name"
__author__ = "Adam Shaw"


def main():
    # Retrieve the current selection
    selection = revit.get_selection()
    
    if not selection:
        forms.alert("No elements selected. Please select elements and run the script again.")
        return
    
    # Prompt user for the element name filter
    element_name_filter = forms.ask_for_string(
        prompt="Enter the element name or a part of the name (start with '!' to exclude):",
        title="Filter Selection by Name"
    )
    
    if element_name_filter is None:
        forms.alert("No element name filter provided. Script cancelled.")
        return
    
    # Check if the filter starts with "!" for exclusion
    exclude_mode = element_name_filter.startswith("!")
    
    # Remove the "!" from the filter if in exclude mode
    if exclude_mode:
        element_name_filter = element_name_filter[1:]
    
    # Convert the element name filter to lowercase for case-insensitive comparison
    element_name_filter = element_name_filter.lower()
    
    # Filter the selection based on the element name
    filtered_selection = []
    for element in selection:
        element_name = element.Name
        if element_name:
            if exclude_mode and element_name_filter not in element_name.lower():
                filtered_selection.append(element.Id)
            elif not exclude_mode and element_name_filter in element_name.lower():
                filtered_selection.append(element.Id)
    
    # Set the filtered selection
    selection.set_to(filtered_selection)

if __name__ == "__main__":
    main()