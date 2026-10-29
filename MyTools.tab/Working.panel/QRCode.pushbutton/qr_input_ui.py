"""GeometryJoin-style QR input, loaded directly through WPF for CPython."""

import ctypes
import os

import clr

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

from Autodesk.Revit.UI import UITheme, UIThemeManager
from pyrevit import HOST_APP, script
from System import IntPtr, Uri, UriKind
from System.IO import File
from System.Windows import ResourceDictionary
from System.Windows.Interop import WindowInteropHelper
from System.Windows.Markup import XamlReader


class QRInputWindow(object):
    def __init__(self):
        bundle = os.path.dirname(__file__)
        stream = File.OpenRead(os.path.join(bundle, "QrInput.xaml"))
        try:
            self.window = XamlReader.Load(stream)
        finally:
            stream.Close()

        self.result = None
        self._logger = script.get_logger()
        self._is_dark = UIThemeManager.CurrentTheme == UITheme.Dark
        styles = ResourceDictionary()
        styles.Source = Uri(os.path.abspath(os.path.join(bundle, "Styles.xaml")), UriKind.Absolute)
        self.window.Resources.MergedDictionaries.Add(styles)
        if self._is_dark:
            palette = ResourceDictionary()
            palette.Source = Uri(os.path.abspath(os.path.join(bundle, "Theme.Dark.xaml")), UriKind.Absolute)
            self.window.Resources.MergedDictionaries.Add(palette)

        self.input_text = self.window.FindName("InputText")
        self.generate_button = self.window.FindName("GenerateButton")
        self.window.FindName("OutputPath").Text = os.path.normpath(
            os.path.expanduser("~/Downloads/qrcode_color_replaced.png")
        )
        self.input_text.TextChanged += self._input_changed
        self.generate_button.Click += self._generate
        self.window.FindName("CancelButton").Click += self._cancel
        self.window.Loaded += self._loaded
        self.window.SourceInitialized += self._theme_title_bar

        owner = HOST_APP.proc_window
        if owner is not None and owner != IntPtr.Zero:
            WindowInteropHelper(self.window).Owner = owner
        if WindowInteropHelper(self.window).Handle != IntPtr.Zero:
            self._theme_title_bar(None, None)

    def _theme_title_bar(self, sender, args):
        try:
            handle = WindowInteropHelper(self.window).Handle.ToInt64()
            set_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            set_attribute.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
            set_attribute.restype = ctypes.c_int
            background = self.window.FindResource("QrWindowBrush").Color
            foreground = self.window.FindResource("QrForegroundBrush").Color
            attributes = (
                (20, ctypes.c_int(1 if self._is_dark else 0)),
                (35, ctypes.c_uint(int(background.R) | (int(background.G) << 8) | (int(background.B) << 16))),
                (36, ctypes.c_uint(int(foreground.R) | (int(foreground.G) << 8) | (int(foreground.B) << 16))),
            )
            failures = []
            for attribute, value in attributes:
                pointer = ctypes.c_void_p(ctypes.addressof(value))
                status = set_attribute(handle, attribute, pointer, ctypes.sizeof(value))
                if status < 0:
                    failures.append("{}: HRESULT 0x{:08X}".format(attribute, status & 0xFFFFFFFF))
            if failures:
                raise RuntimeError("Windows rejected title-bar attributes: {}".format(", ".join(failures)))
        except Exception:
            self._logger.exception("Could not apply the QR input dialog's native title-bar theme.")

    def _loaded(self, sender, args):
        self.input_text.Focus()

    def _input_changed(self, sender, args):
        self.generate_button.IsEnabled = bool(self.input_text.Text.strip())

    def _generate(self, sender, args):
        if self.input_text.Text.strip():
            self.result = self.input_text.Text
            self.window.Close()

    def _cancel(self, sender, args):
        self.result = None
        self.window.Close()

    def show(self):
        self.window.ShowDialog()
        return self.result


def show_qr_input():
    return QRInputWindow().show()
