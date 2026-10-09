import csv
import datetime
import logging
from pyrevit import revit, DB, forms, script

__title__ = "Import PT CSV"
__author__ = "Adam Shaw"

logger = script.get_logger()
file_logger = logging.Logger("PTImport", logging.INFO)
file_logger.propagate = False
file_logger.addHandler(logging.NullHandler())
log_handler = None
log_path = None
log_path_shown = False


def log_message(level, message, exc_info=False):
    global log_path_shown
    file_logger.log(level, message, exc_info=exc_info)
    if level >= logging.WARNING and log_handler is not None and not log_path_shown:
        print("PT import log: {}".format(log_path))
        log_path_shown = True
    if level >= logging.ERROR:
        logger.error(message, exc_info=exc_info)
    elif level >= logging.WARNING:
        logger.warning(message)
    else:
        logger.info(message)


def close_log():
    if log_handler is not None:
        file_logger.removeHandler(log_handler)
        log_handler.close()


try:
    log_path = script.get_data_file(
        "PTImport_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f"), "log"
    )
    log_handler = logging.FileHandler(log_path, encoding="utf-8")
    log_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    file_logger.addHandler(log_handler)
except Exception as error:
    logger.warning(
        "Could not create the PT import log file {!r}: {}. "
        "Logging to pyRevit output only.".format(log_path, error)
    )

try:
    from revitfunctions.PT_funcs import get_family_symbol, rotate_detail_component
    uidoc = revit.uidoc
    doc = uidoc.Document
    view = doc.ActiveView
except Exception:
    log_message(logging.ERROR, "PT import startup failed.", exc_info=True)
    close_log()
    raise


def import_context(context):
    return (
        "CSV={!r} | record={} | line={} | type={!r} | operation={} | "
        "view={!r} ({}) | tendon start={} | tendon end={} | row={!r}"
    ).format(
        context["file"], context["record"], context["line"], context["type"],
        context["operation"], view.Name, view.Id,
        context["start"], context["end"], context["row"],
    )


def log_warning(context, message):
    context["warnings"] += 1
    log_message(logging.WARNING, "{} | {}".format(message, import_context(context)))


def finish_transaction(action, commit, name, exception, context):
    """Keep pyRevit's exit behaviour while logging commit errors before disposal."""
    if exception:
        action.RollBack()
        log_message(logging.INFO, "Rolled back transaction: {}".format(name))
    else:
        try:
            status = commit()
        except Exception:
            context["transaction_errors"] += 1
            log_message(
                logging.ERROR,
                "Transaction commit failed: {} | {}".format(name, import_context(context)),
                exc_info=True,
            )
            action.RollBack()
        else:
            if status != DB.TransactionStatus.Committed:
                context["transaction_errors"] += 1
                log_message(
                    logging.ERROR,
                    "Transaction {} ended with status {} | {}".format(
                        name, status, import_context(context)
                    ),
                )
    action.Dispose()


class ImportTransaction(revit.Transaction):
    def __init__(self, name, context):
        revit.Transaction.__init__(self, name, doc=doc)
        self.context = context

    def __exit__(self, exception, exception_value, traceback):
        finish_transaction(
            self._rvtxn, self._rvtxn.Commit, self.name, exception, self.context
        )


class ImportTransactionGroup(revit.TransactionGroup):
    def __init__(self, name, context):
        revit.TransactionGroup.__init__(self, name, doc=doc)
        self.context = context

    def __exit__(self, exception, exception_value, traceback):
        commit = self._rvtxn_grp.Assimilate if self.assimilate else self._rvtxn_grp.Commit
        finish_transaction(
            self._rvtxn_grp, commit, self.name, exception, self.context
        )


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
    context = {
        "file": file_path, "record": None, "line": None, "row": None,
        "type": None, "operation": "Start transaction group",
        "start": None, "end": None, "warnings": 0, "transaction_errors": 0,
    }
    csv_reader = None
    records_read = 0
    log_message(logging.INFO, "Starting PT import | {}".format(import_context(context)))
    try:
        with ImportTransactionGroup("Import PT CSV", context):
            context["operation"] = "Open CSV file"
            with open(file_path, "r") as csvfile:
                csv_reader = csv.reader(csvfile)
                current_start_point = None
                current_end_point = None

                context["operation"] = "Find PT Tendon_HERA family"
                pt_tendon_family_symbol = get_family_symbol("PT Tendon_HERA")
                if not pt_tendon_family_symbol:
                    log_warning(context, "PT Tendon_HERA was not found; all tendon placement will be skipped.")
                context["operation"] = "Find PT Height_HERA family"
                pt_height_family_symbol = get_family_symbol("PT Height_HERA")
                if not pt_height_family_symbol:
                    log_warning(context, "PT Height_HERA was not found; all height placement will be skipped.")
                context["operation"] = "Find T30 text note type"
                text_note_family_symbol = get_text_note_type_by_partial_name("T30")

                context["operation"] = "Read CSV record"
                context["record"] = 1
                for row_number, row in enumerate(csv_reader, 1):
                    records_read = row_number
                    context.update({
                        "record": row_number, "line": csv_reader.line_num,
                        "row": row, "type": None, "operation": "Read element type",
                    })
                    element_type = row[0]
                    context["type"] = element_type

                    if element_type == "Tendon":
                        context["start"] = None
                        context["end"] = None
                        context["operation"] = "Parse tendon coordinates"
                        current_start_point = prXYZ(row[1], row[2])
                        context["start"] = current_start_point
                        current_end_point = prXYZ(row[3], row[4])
                        context["end"] = current_end_point

                        if pt_tendon_family_symbol:
                            comment = row[5]
                            context["operation"] = "Start tendon transaction"
                            with ImportTransaction("Create Line-Based Detail Component", context):
                                context["operation"] = "Create tendon line"
                                line = DB.Line.CreateBound(
                                    current_start_point, current_end_point
                                )
                                context["operation"] = "Create PT Tendon_HERA detail component"
                                detail_component = doc.Create.NewFamilyInstance(
                                    line, pt_tendon_family_symbol, view
                                )
                                context["operation"] = "Set PT Strand # parameter"
                                detail_component.LookupParameter("PT Strand #").Set(comment)
                                context["operation"] = "Commit tendon transaction"

                    elif element_type == "End" or element_type == "Start":
                        context["operation"] = "Parse text note coordinates"
                        point = prXYZ(row[1], row[2])
                        text = row[3]

                        context["operation"] = "Start text note transaction"
                        with ImportTransaction("Create Text Note", context):
                            if text_note_family_symbol:
                                context["operation"] = "Create T30 text note"
                                text_note = DB.TextNote.Create(
                                    doc, view.Id, point, text, text_note_family_symbol.Id
                                )
                                context["operation"] = "Rotate text note"
                                rotate_detail_component(
                                    text_note, current_start_point, current_end_point, point
                                )
                            else:
                                log_warning(context, "T30 text note type was not found; text note creation skipped.")
                            context["operation"] = "Commit text note transaction"

                    elif element_type == "Point":
                        if pt_height_family_symbol:
                            context["operation"] = "Parse PT height coordinates"
                            point = prXYZ(row[1], row[2])
                            height = str(row[3])
                            low_high = row[5]

                            context["operation"] = "Start PT height transaction"
                            with ImportTransaction("Create PT_Height Family Instance", context):
                                context["operation"] = "Create PT Height_HERA family instance"
                                pt_height = doc.Create.NewFamilyInstance(point, pt_height_family_symbol, view)
                                context["operation"] = "Set Height parameter"
                                pt_height.LookupParameter("Height").Set(height)
                                if pt_height:
                                    context["operation"] = "Rotate PT height"
                                    rotate_detail_component(
                                        pt_height, current_start_point, current_end_point, point
                                    )
                                    context["operation"] = "Set LOW parameter"
                                    pt_height.LookupParameter("LOW").Set(
                                        1 if low_high == "Low" else 0
                                    )
                                    context["operation"] = "Set HIGH parameter"
                                    pt_height.LookupParameter("HIGH").Set(
                                        1 if low_high == "High" else 0
                                    )
                                context["operation"] = "Commit PT height transaction"
                    else:
                        log_warning(context, "Unrecognized record type; record ignored. Check the selected CSV file.")

                    context.update({
                        "record": row_number + 1, "row": None, "type": None,
                        "operation": "Read CSV record",
                    })
                context.update({
                    "record": None, "row": None, "type": None,
                    "operation": "Commit import transaction group",
                })
    except Exception:
        if csv_reader is not None:
            context["line"] = csv_reader.line_num
        log_message(logging.ERROR, "PT import failed | {}".format(import_context(context)), exc_info=True)
        raise
    else:
        summary = "PT import finished reading {} records; {} warnings; {} transaction failures.".format(
            records_read, context["warnings"], context["transaction_errors"]
        )
        log_message(logging.WARNING if context["transaction_errors"] else logging.INFO, summary)
        print(summary)


def main():
    try:
        file_path = forms.pick_file(file_ext="csv")
    except Exception:
        log_message(logging.ERROR, "PT import failed while selecting the CSV file.", exc_info=True)
        raise
    if file_path:
        process_csv_file(file_path)
    else:
        log_message(logging.INFO, "PT import cancelled: no CSV file selected.")
        forms.alert("No CSV file selected. Please try again.")


if __name__ == "__main__":
    try:
        main()
    finally:
        close_log()
