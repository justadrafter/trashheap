import csv
from pyrevit import revit, DB, forms
from pyrevit.revit.db import query
from revitfunctions.PT_funcs import create_detail_component, rotate_detail_component

__title__ = "Import PT CSV"
__author__ = "Adam Shaw"

uidoc = revit.uidoc
doc = uidoc.Document
view = doc.ActiveView

# Get Revit version
revit_version = doc.Application.VersionNumber

def prXYZ(x, y, z=None):
    if z is None:
        z = view.GenLevel.ProjectElevation
    return DB.XYZ(float(x) / 304.8, float(y) / 304.8, z)

def process_csv_file(file_path):
    with revit.TransactionGroup("Import PT CSV"):
        with open(file_path, "r") as csvfile:
            csv_reader = csv.reader(csvfile)
            current_start_point = None
            current_end_point = None

            for row in csv_reader:
                element_type = row[0]

                if element_type == "Tendon":
                    current_start_point = prXYZ(row[1], row[2])
                    current_end_point = prXYZ(row[3], row[4])
                    comment = row[5]

                    with revit.Transaction("Create Line-Based Detail Component"):
                        line = DB.Line.CreateBound(
                            current_start_point, current_end_point
                        )
                        family_symbol = query.get_family_symbol(
                            "PT Tendon_HERA", "PT Tendon_HERA", doc
                        )
                        if family_symbol:
                            if revit_version.startswith('2022'):
                                detail_component = doc.Create.NewFamilyInstance(
                                    line, family_symbol[0], view
                                )
                            else:
                                detail_component = doc.Create.NewFamilyInstance(
                                    line, family_symbol[0], view, DB.Structure.StructuralType.NonStructural
                                )
                            detail_component.LookupParameter("Comments").Set(comment)

                elif element_type == "End" or element_type == "Start":
                    point = prXYZ(row[1], row[2])
                    text = row[3]

                    with revit.Transaction("Create Text Note"):
                        text_note_type = query.get_family_symbol(
                            "T3.5 Transparent", "T3.5 Transparent", doc
                        )
                        if text_note_type:
                            text_note = DB.TextNote.Create(
                                doc, view.Id, point, text, text_note_type[0].Id
                            )
                            rotate_detail_component(
                                text_note,
                                current_start_point,
                                current_end_point,
                                point,
                                adjust_rotation=True,
                            )

                elif element_type == "Point":
                    point = prXYZ(row[1], row[2])
                    height = float(row[3])
                    low_high = row[5]

                    with revit.Transaction("Create PT_Height Family Instance"):
                        pt_height = create_detail_component(
                            point, height, "PT Height_HERA", doc, view
                        )
                        if pt_height:
                            rotate_detail_component(
                                pt_height,
                                current_start_point,
                                current_end_point,
                                point,
                                adjust_rotation=True,
                            )
                            pt_height.LookupParameter("LOW").Set(
                                1 if low_high == "Low" else 0
                            )
                            pt_height.LookupParameter("HIGH").Set(
                                1 if low_high == "High" else 0
                            )


def main():
    file_path = forms.pick_file(file_ext="csv")
    if file_path:
        process_csv_file(file_path)
    else:
        forms.alert("No CSV file selected. Please try again.")


if __name__ == "__main__":
    main()
