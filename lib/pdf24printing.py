#!python2
"""PDF24 printer submission and automatic-save handling for Revit views."""

import os
import uuid

from System.Drawing.Printing import PrinterSettings

from pyrevit import DB, revit
from pyrevit.compat import winreg

from pdfprintfiles import (
    wait_for_named_output, place_output
)


PDF24_PRINTER_NAME = "diroots.prosheets"
PDF24_SERVICE_NAME = "diroots.prosheets"
PDF24_SERVICE_KEY_TEMPLATES = (
    r"SOFTWARE\PDF24\Services\{}",
    r"SOFTWARE\WOW6432Node\PDF24\Services\{}",
)


def _to_text(value):
    if value is None:
        return ""
    if isinstance(value, basestring):
        return value
    return str(value)


class Pdf24Printer(object):
    """Use one configured PDF24 printer without storing a Revit document."""

    def __init__(self):
        self.printer_name = PDF24_PRINTER_NAME
        self.service_name = PDF24_SERVICE_NAME
        self.auto_save_dir = None

    def _require_installed(self):
        if self.printer_name not in PrinterSettings.InstalledPrinters:
            raise ValueError(
                'The required printer "{}" is not installed.'
                .format(self.printer_name)
            )

    def _get_auto_save_dir(self):
        service_key = None
        for template in PDF24_SERVICE_KEY_TEMPLATES:
            try:
                service_key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    template.format(self.service_name)
                )
                break
            except Exception:
                pass

        if service_key is None:
            raise ValueError(
                'Printer settings for "{}" could not be found.'
                .format(self.printer_name)
            )

        def read_value(name, default):
            try:
                return winreg.QueryValueEx(service_key, name)[0]
            except Exception:
                return default

        try:
            handler = _to_text(read_value("Handler", ""))
            output_dir = _to_text(read_value("AutoSaveDir", ""))
            output_name = _to_text(read_value("AutoSaveFilename", ""))
            use_file_chooser = read_value("AutoSaveUseFileChooser", 0)
            show_progress = read_value("AutoSaveShowProgress", 0)
            open_output_dir = read_value("AutoSaveOpenDir", 0)
        finally:
            winreg.CloseKey(service_key)

        if handler.lower() != "autosave":
            raise ValueError(
                'Automatic saving is not enabled for "{}".'
                .format(self.printer_name)
            )
        if int(use_file_chooser) != 0:
            raise ValueError(
                "PDF24's auto-save file chooser must be disabled."
            )
        if int(show_progress) != 0:
            raise ValueError("PDF24's auto-save progress window must be disabled.")
        if int(open_output_dir) != 0:
            raise ValueError("PDF24's open-output-folder option must be disabled.")
        if not output_dir:
            raise ValueError("PDF24 has no automatic-saving output directory.")
        if output_name.strip() != "$fileName":
            raise ValueError(
                'PDF24 auto-save filename for "{}" must be $fileName.'
                .format(self.printer_name)
            )

        return os.path.abspath(os.path.expandvars(output_dir))

    def prepare_silent_save(self):
        self._require_installed()
        self.auto_save_dir = self._get_auto_save_dir()
        if not os.path.isdir(self.auto_save_dir):
            os.makedirs(self.auto_save_dir)

    def submit_view(self, doc, view, output_path, configure=None):
        """Submit a printable view; the PDF24 handler decides how to save it."""
        if view is None or not view.CanBePrinted:
            raise ValueError("The view cannot be printed.")

        self._require_installed()
        print_manager = doc.PrintManager
        print_manager.SelectNewPrintDriver(self.printer_name)
        if configure is not None:
            configure(print_manager, view, self.printer_name)
        print_manager.PrintRange = DB.PrintRange.Current
        print_manager.PrintToFile = True
        print_manager.PrintToFileName = output_path
        print_manager.Apply()

        if not print_manager.SubmitPrint(view):
            raise RuntimeError(
                'Revit did not submit the view to "{}".'
                .format(self.printer_name)
            )

    def save_view(self, doc, view, output_path, configure=None):
        """Submit one view, wait for auto-save, and place the resulting PDF."""
        if self.auto_save_dir is None:
            self.prepare_silent_save()

        job_name = "{}.pdf".format(uuid.uuid4().hex)
        print_path = os.path.join(os.path.dirname(output_path), job_name)
        source_path = os.path.join(self.auto_save_dir, job_name)

        if configure is None:
            self.submit_view(doc, view, print_path)
            generated_path = wait_for_named_output(source_path, None)
        else:
            with revit.DryTransaction("Set Single PDF Print Settings", doc=doc):
                self.submit_view(doc, view, print_path, configure=configure)
                generated_path = wait_for_named_output(source_path, None)
        place_output(generated_path, output_path)

    def print_current_view(self, doc, view, output_path):
        """Finish the single-view command after the saved PDF is placed."""
        from revitpdfsettings import configure_single_view
        self.save_view(doc, view, output_path, configure=configure_single_view)
