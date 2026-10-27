"""Material-priority dialog and presets; return the order when Run joins is clicked."""

import io
import json
import os
import tempfile
import time

from pyrevit import DB, forms, script
from Autodesk.Revit.UI import UITheme, UIThemeManager
from System import Guid, IntPtr, String, Uri, UriKind
from System.Collections.ObjectModel import ObservableCollection
from System.IO import File
from System.Windows import DataObject, DragDrop, DragDropEffects, Point, ResourceDictionary, SystemParameters, Thickness, Visibility
from System.Windows.Controls import ItemsControl, ListBoxItem, ScrollViewer
from System.Windows.Documents import Run, TextElement
from System.Windows.Input import Keyboard, ModifierKeys, MouseButtonState
from System.Windows.Interop import WindowInteropHelper
from System.Windows.Media import VisualTreeHelper


MATERIAL_DRAG_FORMAT = "HERA.GeometryJoin.MaterialOrder"


def apply_revit_theme(window):
    """Load shared styles and Revit's palette from absolute bundle paths."""
    bundle_path = os.path.dirname(__file__)
    styles = ResourceDictionary()
    styles.Source = Uri(os.path.abspath(os.path.join(bundle_path, "Styles.xaml")), UriKind.Absolute)
    window.Resources.MergedDictionaries.Add(styles)
    window._is_dark_theme = UIThemeManager.CurrentTheme == UITheme.Dark
    if not window._is_dark_theme:
        return
    theme_path = os.path.join(bundle_path, "Theme.Dark.xaml")
    palette = ResourceDictionary()
    palette.Source = Uri(os.path.abspath(theme_path), UriKind.Absolute)
    window.Resources.MergedDictionaries.Add(palette)


def apply_title_bar_theme(window):
    """Theme the native Windows caption separately from the WPF content."""
    import ctypes

    handle = WindowInteropHelper(window).Handle.ToInt64()
    set_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
    # HWND is pointer-sized; BOOL, COLORREF, and HRESULT are all 32-bit values.
    set_attribute.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
    set_attribute.restype = ctypes.c_int
    background = window.FindResource("MaterialWindowBrush").Color
    foreground = window.FindResource("MaterialForegroundBrush").Color
    attributes = (
        (20, ctypes.c_int(1 if window._is_dark_theme else 0)),  # Immersive dark mode
        (35, ctypes.c_uint(int(background.R) | (int(background.G) << 8) | (int(background.B) << 16))),
        (36, ctypes.c_uint(int(foreground.R) | (int(foreground.G) << 8) | (int(foreground.B) << 16))),
    )
    failures = []
    for attribute, value in attributes:
        # IronPython's byref() NativeArgument cannot satisfy a c_void_p argument.
        value_pointer = ctypes.c_void_p(ctypes.addressof(value))
        result = set_attribute(handle, attribute, value_pointer, ctypes.sizeof(value))
        if result < 0:
            failures.append("{}: HRESULT 0x{:08X}".format(attribute, result & 0xFFFFFFFF))
    if failures:
        raise RuntimeError("Windows rejected title-bar attributes: {}".format(", ".join(failures)))


def preset_material_names(data):
    """Validate the preset format and remove duplicate names in saved order."""
    if not isinstance(data, dict):
        raise ValueError("The preset must contain a JSON object.")
    if type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("The preset has an unsupported format version.")
    if data.get("priority") != "highest_first":
        raise ValueError("The preset must specify highest_first priority.")
    names = data.get("materials")
    if not isinstance(names, list):
        raise ValueError("The preset must contain a materials list.")
    result = []
    seen = set()
    for name in names:
        if not isinstance(name, (str, type(u""))) or not name.startswith("HERA_"):
            raise ValueError("Every preset material must be a name starting with HERA_.")
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def read_preset(path):
    """Read a UTF-8 JSON preset, including files with a byte-order mark."""
    with io.open(path, "r", encoding="utf-8-sig") as stream:
        return preset_material_names(json.load(stream))


def write_preset(path, material_names):
    """Replace the file only after the full validated preset has been written."""
    path = os.path.abspath(path)
    data = {"version": 1, "priority": "highest_first", "materials": list(material_names)}
    data["materials"] = preset_material_names(data)
    directory = os.path.dirname(path)
    descriptor, temporary_path = tempfile.mkstemp(prefix=".material-order-", suffix=".tmp", dir=directory)
    os.close(descriptor)
    try:
        with io.open(temporary_path, "w", encoding="utf-8") as stream:
            stream.write(u"{}\n".format(json.dumps(data, ensure_ascii=False, indent=2)))
        if File.Exists(path):
            File.Replace(temporary_path, path, None)
        else:
            File.Move(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            try:
                os.remove(temporary_path)
            except Exception:
                script.get_logger().exception("Could not remove temporary preset file: {}".format(temporary_path))


def reconcile_order(saved_names, available_names):
    """Show available saved materials first and append new ones at the bottom."""
    available = set(available_names)
    saved = set(saved_names)
    present = [name for name in saved_names if name in available]
    missing = [name for name in saved_names if name not in available]
    new = [name for name in available_names if name not in saved]
    return present + new, missing, new


def complete_order(saved_names, visible_names):
    """Apply visible reordering while preserving missing materials' saved slots."""
    visible = set(visible_names)
    reordered = iter(visible_names)
    result = [next(reordered) if name in visible else name for name in saved_names]
    result.extend(reordered)
    return result


def move_materials(material_names, selected_names, offset):
    """Move every selected row one position without changing their relative order."""
    result = list(material_names)
    selected = set(selected_names)
    indices = [index for index, name in enumerate(result) if name in selected]
    if not indices or offset not in (-1, 1):
        return result
    if indices[0] + offset < 0 or indices[-1] + offset >= len(result):
        return result
    for index in indices if offset < 0 else reversed(indices):
        target = index + offset
        result[index], result[target] = result[target], result[index]
    return result


def drop_materials(material_names, selected_names, insertion_index):
    """Place selected rows together at a gap in the original list."""
    selected = set(selected_names)
    moving = [name for name in material_names if name in selected]
    remaining = [name for name in material_names if name not in selected]
    insertion_index = max(0, min(insertion_index, len(material_names)))
    target = sum(1 for name in material_names[:insertion_index] if name not in selected)
    return remaining[:target] + moving + remaining[target:]


def find_scroll_viewer(visual):
    """Find the list's own scroll viewer after its template has been created."""
    if isinstance(visual, ScrollViewer):
        return visual
    for index in range(VisualTreeHelper.GetChildrenCount(visual)):
        found = find_scroll_viewer(VisualTreeHelper.GetChild(visual, index))
        if found is not None:
            return found
    return None


def project_material_names(doc):
    """Read HERA_ materials from the explicitly supplied document once."""
    if doc is None:
        return []
    collector = DB.FilteredElementCollector(doc).OfClass(DB.Material)
    try:
        names = []
        for material in collector:
            name = material.Name
            if name.startswith("HERA_"):
                names.append(name)
        return sorted(names, key=lambda name: name.lower())
    finally:
        collector.Dispose()


class MaterialOrderWindow(forms.WPFWindow):
    """Edit and remember priority; let the caller perform joins after closing."""

    def __init__(self, material_names, can_run=True):
        xaml_path = os.path.join(os.path.dirname(__file__), "MaterialOrder.xaml")
        forms.WPFWindow.__init__(self, xaml_path)
        apply_revit_theme(self)
        self._initial_names = tuple(material_names)
        self._can_run = can_run
        self.run_order = None
        self._logger = script.get_logger()
        self._settings_path = script.get_universal_data_file("HERA_GeometryJoin_material_order", "json")
        self._saved_names = []
        self._dirty = False
        self._reordering = False
        self._drag_start = None
        self._pressed_name = None
        self._deferred_click = False
        self._drag_names = []
        self._drag_token = Guid.NewGuid().ToString()
        self._scroll_viewer = None
        self._last_scroll_at = 0
        self.rows = ObservableCollection[String]()
        self.MaterialList.ItemsSource = self.rows
        self.MaterialList.SelectionChanged += self.selection_changed
        self.MaterialList.PreviewMouseLeftButtonDown += self.list_mouse_down
        self.MaterialList.PreviewMouseLeftButtonUp += self.list_mouse_up
        self.MaterialList.PreviewMouseMove += self.list_mouse_move
        self.MaterialList.PreviewDragOver += self.list_drag_over
        self.MaterialList.PreviewDrop += self.list_drop
        self.MaterialList.DragLeave += self.list_drag_leave
        self.MoveUpButton.Click += self.move_up
        self.MoveDownButton.Click += self.move_down
        self.ResetButton.Click += self.reset
        self.LoadButton.Click += self.load
        self.SaveButton.Click += self.save_as
        self.CancelButton.Click += self.close_window
        self.RunButton.Click += self.run_joins
        self.Closing += self.remember_order
        self._restore_remembered_order()
        self.SourceInitialized += self.theme_title_bar
        # pyRevit may already have created the handle while setting the owner.
        if WindowInteropHelper(self).Handle != IntPtr.Zero:
            self.theme_title_bar(None, None)

    def theme_title_bar(self, sender, args):
        try:
            apply_title_bar_theme(self)
        except Exception:
            self._logger.exception("Could not apply Material Join Priority's native title-bar theme.")

    def _restore_remembered_order(self):
        has_saved_order = os.path.isfile(self._settings_path)
        if has_saved_order:
            try:
                self._saved_names = read_preset(self._settings_path)
            except Exception as error:
                self._report_error("Load remembered order", self._settings_path, error)
                self._display_order(list(self._initial_names), [], [], "Remembered order could not be loaded.")
                # Preserve the unreadable file unless the user edits/loads an order.
                return
            message = "Remembered order loaded."
        else:
            message = "Starting with alphabetical order."
        ordered, missing, new = reconcile_order(self._saved_names, self._initial_names)
        self._display_order(ordered, missing, new, message, highlight_new=has_saved_order)
        self._dirty = bool(new)

    def _display_order(self, ordered, missing, new, message, highlight_new=False):
        self.rows.Clear()
        for name in ordered:
            self.rows.Add(name)
        self.EmptyListMessage.Visibility = Visibility.Collapsed if self.rows.Count else Visibility.Visible
        self.MaterialList.SelectedIndex = 0 if self.rows.Count else -1
        self.ResetButton.IsEnabled = self.rows.Count > 0
        self.RunButton.IsEnabled = self._can_run and self.rows.Count > 0
        if not self._can_run:
            self.RunButton.ToolTip = "Select at least two walls, structural columns, floors, structural framing elements, or structural foundations in Revit before opening this window."
        elif not self.rows.Count:
            self.RunButton.ToolTip = "No HERA_ materials are available to define a join order."
        else:
            self.RunButton.ToolTip = "Join the selected elements using this order; materials at the top cut those below."
        details = [message]
        if missing:
            details.append("{} saved material(s) unavailable here; retained in presets.".format(len(missing)))
        self.PresetStatus.Inlines.Clear()
        self.PresetStatus.Inlines.Add(Run(" ".join(details)))
        if new:
            notice = Run(" {} new material(s) added at the bottom.".format(len(new)))
            if highlight_new:
                notice.Text = " {} new material(s) were not in the saved order; added at the bottom. Please review their priority.".format(len(new))
                notice.SetResourceReference(TextElement.ForegroundProperty, "MaterialWarningBrush")
            self.PresetStatus.Inlines.Add(notice)
        self.selection_changed(None, None)

    def _report_error(self, operation, path, error, allow_discard=False):
        self._logger.exception("{} failed for material-order file: {}".format(operation, path))
        message = "{} failed.\n\nFile: {}\n\n{}".format(operation, path, error)
        if allow_discard:
            message += "\n\nKeep editing to retry or use Save as. Closing without saving cancels this run."
            return forms.alert(message, title="Material Cut Order",
                               options=["Keep editing", "Close without saving"])
        return forms.alert(message, title="Material Cut Order")

    def selection_changed(self, sender, args):
        if self._reordering:
            return
        selected = set(self.MaterialList.SelectedItems)
        indices = [index for index, name in enumerate(self.rows) if name in selected]
        self.MoveUpButton.IsEnabled = bool(indices) and indices[0] > 0
        self.MoveDownButton.IsEnabled = bool(indices) and indices[-1] < self.rows.Count - 1

    def _selected_names(self):
        selected = set(self.MaterialList.SelectedItems)
        return [name for name in self.rows if name in selected]

    def _apply_order(self, ordered, selected):
        if ordered == list(self.rows):
            return
        self._reordering = True
        try:
            for target, name in enumerate(ordered):
                current = self.rows.IndexOf(name)
                if current != target:
                    self.rows.Move(current, target)
            self.MaterialList.SelectedItems.Clear()
            for name in selected:
                self.MaterialList.SelectedItems.Add(name)
            self._dirty = True
        finally:
            self._reordering = False
            self.selection_changed(None, None)

    def _move(self, offset):
        selected = self._selected_names()
        self._apply_order(move_materials(list(self.rows), selected, offset), selected)
        if selected:
            self.MaterialList.ScrollIntoView(selected[0] if offset < 0 else selected[-1])

    def move_up(self, sender, args):
        self._move(-1)

    def move_down(self, sender, args):
        self._move(1)

    def list_mouse_down(self, sender, args):
        self._drag_start = None
        self._pressed_name = None
        self._deferred_click = False
        item = ItemsControl.ContainerFromElement(self.MaterialList, args.OriginalSource)
        if not isinstance(item, ListBoxItem):
            return
        self._drag_start = args.GetPosition(self.MaterialList)
        self._pressed_name = item.Content
        # Keep an existing multi-selection intact until we know whether this is a drag.
        if item.IsSelected and Keyboard.Modifiers == getattr(ModifierKeys, "None"):
            self._deferred_click = True
            self.MaterialList.Focus()
            args.Handled = True

    def list_mouse_up(self, sender, args):
        if self._deferred_click and self._pressed_name is not None:
            self.MaterialList.SelectedItems.Clear()
            self.MaterialList.SelectedItem = self._pressed_name
            args.Handled = True
        self._drag_start = None
        self._pressed_name = None
        self._deferred_click = False

    def list_mouse_move(self, sender, args):
        if self._drag_start is None or self._drag_names:
            return
        if args.LeftButton != MouseButtonState.Pressed:
            self._drag_start = None
            self._pressed_name = None
            self._deferred_click = False
            return
        position = args.GetPosition(self.MaterialList)
        if (abs(position.X - self._drag_start.X) < SystemParameters.MinimumHorizontalDragDistance
                and abs(position.Y - self._drag_start.Y) < SystemParameters.MinimumVerticalDragDistance):
            return
        selected = self._selected_names()
        if self._pressed_name not in selected:
            return
        self._drag_names = selected
        self._deferred_click = False
        self._scroll_viewer = find_scroll_viewer(self.MaterialList)
        args.Handled = True
        try:
            data = DataObject(MATERIAL_DRAG_FORMAT, self._drag_token)
            DragDrop.DoDragDrop(self.MaterialList, data, DragDropEffects.Move)
        finally:
            self.DropMarker.Visibility = Visibility.Collapsed
            self._drag_start = None
            self._pressed_name = None
            self._drag_names = []

    def _accept_drag(self, args):
        return (bool(self._drag_names)
                and args.Data.GetDataPresent(MATERIAL_DRAG_FORMAT)
                and args.Data.GetData(MATERIAL_DRAG_FORMAT) == self._drag_token)

    def _drop_position(self, position):
        # Only realized containers have screen positions; this also works when scrolled.
        insertion_index, marker_top = 0, 1
        for index in range(self.rows.Count):
            item = self.MaterialList.ItemContainerGenerator.ContainerFromIndex(index)
            if item is None:
                continue
            top = item.TranslatePoint(Point(0, 0), self.MaterialList).Y
            bottom = top + item.ActualHeight
            if bottom <= 0 or top >= self.MaterialList.ActualHeight:
                continue
            if position.Y < top + item.ActualHeight / 2:
                return index, max(1, top)
            insertion_index, marker_top = index + 1, bottom
        return insertion_index, min(marker_top, max(1, self.MaterialList.ActualHeight - 3))

    def list_drag_over(self, sender, args):
        args.Handled = True
        args.Effects = getattr(DragDropEffects, "None")
        if not self._accept_drag(args):
            self.DropMarker.Visibility = Visibility.Collapsed
            return
        position = args.GetPosition(self.MaterialList)
        now = time.time()
        if self._scroll_viewer is not None and now - self._last_scroll_at >= 0.1:
            if position.Y < 24:
                self._scroll_viewer.LineUp()
                self._last_scroll_at = now
            elif position.Y > self.MaterialList.ActualHeight - 24:
                self._scroll_viewer.LineDown()
                self._last_scroll_at = now
            self.MaterialList.UpdateLayout()
        insertion_index, marker_top = self._drop_position(position)
        self.DropMarker.Margin = Thickness(2, marker_top, 18, 0)
        self.DropMarker.Visibility = Visibility.Visible
        args.Effects = DragDropEffects.Move

    def list_drag_leave(self, sender, args):
        position = args.GetPosition(self.MaterialList)
        if (position.X < 0 or position.X >= self.MaterialList.ActualWidth
                or position.Y < 0 or position.Y >= self.MaterialList.ActualHeight):
            self.DropMarker.Visibility = Visibility.Collapsed

    def list_drop(self, sender, args):
        args.Handled = True
        args.Effects = getattr(DragDropEffects, "None")
        self.DropMarker.Visibility = Visibility.Collapsed
        if not self._accept_drag(args):
            return
        insertion_index, marker_top = self._drop_position(args.GetPosition(self.MaterialList))
        selected = list(self._drag_names)
        ordered = drop_materials(list(self.rows), selected, insertion_index)
        self._apply_order(ordered, selected)
        self.MaterialList.ScrollIntoView(selected[0])
        args.Effects = DragDropEffects.Move

    def reset(self, sender, args):
        available = set(self._initial_names)
        missing = [name for name in self._saved_names if name not in available]
        self._display_order(list(self._initial_names), missing, [], "Alphabetical order restored.")
        self._dirty = True

    def load(self, sender, args):
        path = forms.pick_file(file_ext="json", title="Load material cut order")
        if not path:
            return
        try:
            saved_names = read_preset(path)
        except Exception as error:
            self._report_error("Load preset", path, error)
            return
        ordered, missing, new = reconcile_order(saved_names, self._initial_names)
        self._saved_names = saved_names
        self._display_order(ordered, missing, new, "Preset loaded: {}.".format(os.path.basename(path)),
                            highlight_new=True)
        self._dirty = True

    def save_as(self, sender, args):
        path = forms.save_file(file_ext="json", default_name="HERA-material-cut-order.json",
                               title="Save material cut order")
        if not path:
            return
        try:
            write_preset(path, complete_order(self._saved_names, list(self.rows)))
        except Exception as error:
            self._report_error("Save preset", path, error)
            return
        self.PresetStatus.Text = "Preset saved: {}. Unavailable saved materials are retained.".format(os.path.basename(path))

    def remember_order(self, sender, args):
        if not self._dirty:
            return
        try:
            write_preset(self._settings_path, complete_order(self._saved_names, list(self.rows)))
        except Exception as error:
            args.Cancel = True
            self.run_order = None
            choice = self._report_error("Remember order on close", self._settings_path, error,
                                        allow_discard=True)
            if choice == "Close without saving":
                args.Cancel = False
            return
        self._dirty = False

    def close_window(self, sender, args):
        self.run_order = None
        self.Close()

    def run_joins(self, sender, args):
        if self._can_run and self.rows.Count:
            self.run_order = list(self.rows)
            self.Close()


def show_material_order(doc, can_run=True):
    """Return highest-first visible names on Run joins, or None on Close/X."""
    window = MaterialOrderWindow(project_material_names(doc), can_run=can_run)
    window.ShowDialog()
    return window.run_order
