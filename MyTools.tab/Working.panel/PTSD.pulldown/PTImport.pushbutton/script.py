import csv
from pyrevit import revit, DB, forms
from revitfunctions.PT_funcs import get_family_symbol, rotate_detail_component

__title__ = "Import PT CSV"
__author__ = "Adam Shaw"

uidoc = revit.uidoc
doc = uidoc.Document
view = doc.ActiveView


def prXYZ(x, y, z=None):
    if z is None:
        z = view.GenLevel.ProjectElevation
    return DB.XYZ(float(x) / 304.8, float(y) / 304.8, z)

def get_text_note_type_by_partial_name(partial_name):
    text_note_types = DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType).ToElements()
    for text_note_type in text_note_types:
        if partial_name in text_note_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString():
            return text_note_type
    return None


def process_csv_file(file_path):
    with revit.TransactionGroup("Import PT CSV"):
        with open(file_path, "r") as csvfile:
            csv_reader = csv.reader(csvfile)
            # current_tendon = None
            current_start_point = None
            current_end_point = None

            pt_tendon_family_symbol = get_family_symbol("PT Tendon_HERA")
            pt_height_family_symbol = get_family_symbol("PT Height_HERA")
            text_note_family_symbol = get_text_note_type_by_partial_name("T30")

            for row in csv_reader:
                element_type = row[0]

                if element_type == "Tendon":
                    # current_tendon = row
                    current_start_point = prXYZ(row[1], row[2])
                    current_end_point = prXYZ(row[3], row[4])
                    comment = row[5]

                    with revit.Transaction("Create Line-Based Detail Component"):
                        line = DB.Line.CreateBound(
                            current_start_point, current_end_point
                        )
                        
                        if pt_tendon_family_symbol:
                            detail_component = doc.Create.NewFamilyInstance(
                                line, pt_tendon_family_symbol, view
                            )
                            detail_component.LookupParameter("PT Strand #").Set(comment)

                elif element_type == "End" or element_type == "Start":
                    point = prXYZ(row[1], row[2])
                    text = row[3]

                    with revit.Transaction("Create Text Note"):
                        if text_note_family_symbol:
                            text_note = DB.TextNote.Create(
                                doc, view.Id, point, text, text_note_family_symbol.Id
                            )
                            rotate_detail_component(
                                text_note,
                                current_start_point,
                                current_end_point,
                                point,
                                # adjust_rotation=True,
                            )

                elif element_type == "Point":
                    point = prXYZ(row[1], row[2])
                    height = str(row[3])
                    low_high = row[5]

                    with revit.Transaction("Create PT_Height Family Instance"):
                        
                        pt_height = doc.Create.NewFamilyInstance(point, pt_height_family_symbol, view)
                        pt_height.LookupParameter("Height").Set(height)
                        if pt_height:
                            rotate_detail_component(
                                pt_height,
                                current_start_point,
                                current_end_point,
                                point,
                                # adjust_rotation=True,
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
