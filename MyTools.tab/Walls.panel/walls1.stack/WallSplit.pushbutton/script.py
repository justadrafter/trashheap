"""
This script allows you to split selected walls vertically. It will ignore profile-edited walls and any walls with attachements.
To use this script:
1. Select one or more walls in the Revit project.
2. Run the script.
3. Select the desired levels from the provided list to define the split locations.
4. The selected walls will be copied and split vertically at the selected levels, creating new wall segments between the levels.
"""

from pyrevit import revit, DB, forms
from System.Collections.Generic import List

__title__ = "Level Split"
__author__ = "Adam Shaw"

def get_levels():
    levels = DB.FilteredElementCollector(revit.doc).OfClass(DB.Level).ToElements()
    return sorted(levels, key=lambda x: x.Elevation)

def split_walls_by_levels(walls, levels):
    counter = 0

    try:
        with forms.ProgressBar(title='Splitting Walls') as pb:    
            with revit.Transaction("Split Walls by Levels"):
                for wall in walls:
                    if wall.SketchId.IntegerValue==-1 and wall.get_Parameter(DB.BuiltInParameter.WALL_TOP_IS_ATTACHED).AsInteger() == 0 and wall.get_Parameter(DB.BuiltInParameter.WALL_BOTTOM_IS_ATTACHED).AsInteger() == 0:
                        wall_top_level_id = wall.get_Parameter(DB.BuiltInParameter.WALL_HEIGHT_TYPE).AsElementId()
                        wall_top_level = revit.doc.GetElement(wall_top_level_id)
                        wall_btm_level_id = wall.get_Parameter(DB.BuiltInParameter.WALL_BASE_CONSTRAINT).AsElementId()
                        wall_btm_level = revit.doc.GetElement(wall_btm_level_id)
                        wall_top_offset = wall.get_Parameter(DB.BuiltInParameter.WALL_TOP_OFFSET).AsDouble() 
                        wall.get_Parameter(DB.BuiltInParameter.WALL_TOP_OFFSET).Set(0)

                        if len(levels) < 1:
                            continue
                        
                        specific_levels = [level for level in levels if level.Elevation > wall_btm_level.Elevation and level.Elevation < wall_top_level.Elevation]
                        specific_levels.append(wall_top_level)

                        new_walls = []

                        # Create copies of the wall for each selected level
                        for i in range(1,len(specific_levels)):
                            bottom_level = specific_levels[i-1]
                            top_level = specific_levels[i]

                            wall_ids = List[DB.ElementId]([wall.Id])
                            new_wall_ids = DB.ElementTransformUtils.CopyElements(
                                revit.doc,
                                wall_ids,
                                revit.doc,
                                None,
                                None
                            )
                            new_wall = revit.doc.GetElement(new_wall_ids[0])
                            new_wall.get_Parameter(DB.BuiltInParameter.WALL_BASE_CONSTRAINT).Set(bottom_level.Id)
                            new_wall.get_Parameter(DB.BuiltInParameter.WALL_HEIGHT_TYPE).Set(top_level.Id)
                            new_wall.get_Parameter(DB.BuiltInParameter.WALL_TOP_OFFSET).Set(0)
                            new_walls.append(new_wall)

                        # Update the top constraint of the original wall to the first selected level
                        if new_walls:
                            first_level = specific_levels[0]
                            wall.get_Parameter(DB.BuiltInParameter.WALL_HEIGHT_TYPE).Set(first_level.Id)
                            new_walls[-1].get_Parameter(DB.BuiltInParameter.WALL_TOP_OFFSET).Set(wall_top_offset)
                        
                        counter += 1
                        pb.update_progress(counter, len(walls))

    except Exception as e:
        forms.alert("Failed to split walls. Error: {}".format(str(e)))

def main():
    selected_walls = [wall for wall in revit.get_selection() if isinstance(wall, DB.Wall)]
    selected_levels = [level for level in revit.get_selection() if isinstance(level, DB.Level)]
    sorted(selected_levels, key=lambda x: x.Elevation)

    if not selected_walls:
        forms.alert("Please select at least one wall.")
        return
    
    if not selected_levels:
        levels = get_levels()
        selected_levels = forms.SelectFromList.show(levels, title='Select Levels', width=500, button_name='Select',name_attr = 'Name', multiselect=True)

    if selected_levels:
        split_walls_by_levels(selected_walls, selected_levels)

if __name__ == "__main__":
    main()