#!python2
import os
import clr

from pyrevit import revit, DB, forms

from System.Collections.Generic import List
from System.Drawing.Printing import PrinterSettings

__title__ = "Print PDF/DWG"
__author__ = "Adam Shaw"

INVALID_CHARS = '<>:"/\\|?*'

doc = revit.doc


class SheetOption(object):
    def __init__(self, sheet):
        self.sheet = sheet
        self.name = "{} - {}".format(sheet.SheetNumber, sheet.Name)


def to_text(value):
    if value is None:
        return ""
    if isinstance(value, basestring):
        return value
    return str(value)


def sanitize_filename(name):
    name = name.replace("\r", " ").replace("\n", " ").strip()
    for ch in INVALID_CHARS:
        name = name.replace(ch, "_")
    return name


def load_conventions(path):
    pdf_pattern = None
    dwg_pattern = None
    default_pattern = None

    with open(path, "r") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip().upper()
                value = value.strip()
                if key == "PDF":
                    pdf_pattern = value
                elif key == "DWG":
                    dwg_pattern = value
                elif key == "DEFAULT":
                    default_pattern = value
            else:
                default_pattern = line

    if not default_pattern:
        default_pattern = "{SheetNumber}_{SheetName}"

    return pdf_pattern or default_pattern, dwg_pattern or default_pattern


def build_filename(pattern, sheet):
    tokens = {
        "SheetNumber": to_text(sheet.SheetNumber),
        "SheetName": to_text(sheet.Name),
        "ViewName": to_text(sheet.Name),
        "ProjectName": to_text(doc.Title),
    }

    name = to_text(pattern)
    for key, value in tokens.items():
        name = name.replace("{" + key + "}", value)

    if not name.strip():
        name = tokens["SheetNumber"]

    return sanitize_filename(name)


def pick_sheets():
    sheets = [
        sheet for sheet in DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet)
        if not sheet.IsPlaceholder
    ]

    if not sheets:
        forms.alert("No sheets found in this model.", title="Print PDF/DWG")
        return None

    sheets = sorted(sheets, key=lambda s: s.SheetNumber)
    options = [SheetOption(sheet) for sheet in sheets]

    selected = forms.SelectFromList.show(
        options,
        title="Select Sheets",
        multiselect=True,
        name_attr="name"
    )

    if not selected:
        return None

    if isinstance(selected, list):
        return [item.sheet for item in selected]

    return [selected.sheet]


def pick_outputs():
    choices = forms.SelectFromList.show(
        ["PDF", "DWG"],
        title="Select Output Types",
        multiselect=True
    )

    if not choices:
        return None, None

    return "PDF" in choices, "DWG" in choices


def pick_printer(default_name):
    printers = [printer for printer in PrinterSettings.InstalledPrinters]
    if not printers:
        forms.alert("No printers found on this machine.", title="Print PDF/DWG")
        return None

    if default_name in printers:
        printers.remove(default_name)
        printers.insert(0, default_name)

    return forms.SelectFromList.show(printers, title="Select PDF Printer")


def print_pdf(sheet, printer_name, output_path):
    print_manager = doc.PrintManager
    print_manager.SelectNewPrintDriver(printer_name)
    print_manager.PrintRange = DB.PrintRange.Select
    print_manager.PrintToFile = True
    print_manager.CombinedFile = False
    print_manager.PrintToFileName = output_path

    view_set = DB.ViewSet()
    view_set.Insert(sheet)

    transaction = DB.Transaction(doc, "Configure Print")
    transaction.Start()
    print_manager.ViewSheetSetting.CurrentViewSheetSet.Views = view_set
    print_manager.Apply()
    transaction.Commit()

    print_manager.SubmitPrint()


def export_dwg(sheet, output_dir, base_name):
    options = DB.DWGExportOptions()
    view_ids = List[DB.ElementId]()
    view_ids.Add(sheet.Id)
    doc.Export(output_dir, base_name, view_ids, options)


def main():
    sheets = pick_sheets()
    if not sheets:
        return

    naming_path = forms.pick_file(file_ext="txt", title="Select naming convention file")
    if not naming_path:
        forms.alert("No naming convention file selected.", title="Print PDF/DWG")
        return

    output_dir = forms.pick_folder(title="Select output folder")
    if not output_dir:
        forms.alert("No output folder selected.", title="Print PDF/DWG")
        return

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    do_pdf, do_dwg = pick_outputs()
    if not do_pdf and not do_dwg:
        forms.alert("No output type selected.", title="Print PDF/DWG")
        return

    printer_name = None
    if do_pdf:
        printer_name = pick_printer(doc.PrintManager.PrinterName)
        if not printer_name:
            forms.alert("No printer selected.", title="Print PDF/DWG")
            return

    pdf_pattern, dwg_pattern = load_conventions(naming_path)
    errors = []

    for sheet in sheets:
        if do_pdf:
            try:
                base_name = build_filename(pdf_pattern, sheet)
                pdf_path = os.path.join(output_dir, base_name + ".pdf")
                print_pdf(sheet, printer_name, pdf_path)
            except Exception as ex:
                errors.append("PDF {}: {}".format(sheet.SheetNumber, ex))

        if do_dwg:
            try:
                base_name = build_filename(dwg_pattern, sheet)
                export_dwg(sheet, output_dir, base_name)
            except Exception as ex:
                errors.append("DWG {}: {}".format(sheet.SheetNumber, ex))

    if errors:
        forms.alert(
            "Finished with errors:\n{}".format("\n".join(errors)),
            title="Print PDF/DWG"
        )
    else:
        forms.alert("Finished.", title="Print PDF/DWG")


if __name__ == "__main__":
    main()
