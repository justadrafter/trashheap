# WPF UI, themes, and preferences

Load this reference only when editing pyRevit WPF/XAML dialogs, preview launchers, material ordering, saved UI state, or visual theming. Check the **installed** pyRevit implementation before using APIs from newer online examples.

## Preview and command execution

- For layout-only requests, preserve the command's existing entry point and provide a separate preview launcher. A pyRevit pushbutton's `config.py` executes on **Shift-click**, so a WPF dialog can be previewed without invoking `script.py`.
- In unauthorized previews, disable controls that change the model or persist data. Keep temporary list reordering in memory and pass the Revit document explicitly to material queries.
- For a command settings dialog, capture the document and selection **before** opening it. Return executable settings only from an explicit **Run** action. Start model transactions **after** the modal window closes. Close/X may preserve settings but must not change the model.

## Material-order presets and file safety

- Store material **names**, not project-specific `ElementId`s. Include a format version and priority direction.
- When reconciling a preset with the current document, retain missing names in stored data and append newly encountered materials at the bottom of the order.
- Validate imported presets before changing the displayed order; replace saved files only after a full successful write. Use a pyRevit **universal data file** for preferences that should survive sessions and Revit version changes.
- Highlight appended materials only if comparing with an existing remembered or imported order. A first-time alphabetical initialization has no prior order to compare.
- When matching configured labels to material names, normalize both identically; for exact-name priority lists, build the rank map once per run and keep processing consistent with the displayed order.
- Where a serialized preference stores the same colour multiple ways, update all representations with native conversions without touching unrelated data. Verify its **loaded appearance**, not just the structure of the saved file.

## Save and close behaviour

- Synchronous writes in WPF `Closing` can make the window appear slow to dismiss. Save only when dirty, including changes caused by project reconciliation. Measure `Closing` handlers and file I/O before assuming persistence is the cause; unchanged settings should skip writes.
- If saving in `Closing` fails, cancel closure, clear any pending Run result, and keep edits available for retry/export. Include an explicit **discard-and-close** path so a read-only or unwritable settings file cannot trap the user.

## XAML layout, selection, and status

- When deleting XAML controls, also remove Python references, event handlers, obsolete rows/containers, and now-unused styles. Check remaining named Python control references against parsed XAML to avoid initialization errors.
- Avoid a heading that merely repeats the title bar in compact dialogs. Explicit font setters on text, button, caption and tooltip styles override changing only the window-level font size.
- For multi-row ordering, snapshot the selected names **in list order** and restore selection after collection moves. Preserve selection on mouse-down until a click/drag is confirmed; translate insertion gaps after removing dragged rows. Handle scrolling and virtualized item containers. Cancelling a drag must preserve the original order.
- For mixed-colour WPF status messages, rebuild `TextBlock.Inlines`, apply a theme-specific warning brush to the notice `Run`, preserve the normal caption style for other text, and clear stale notices on subsequent changes.

## Themes and styles

- The installed pyRevit WPF loader may lack `resolve_theme` and semantic brushes shown in current documentation. For Revit 2024+, `UIThemeManager.CurrentTheme` and local `DynamicResource` brushes are options.
- Check backgrounds, selection, hover, disabled states, and scrollbars in **both Revit light and dark themes**. Windows `SystemColors` alone does not follow Revit's theme. Keep button-state brushes distinct from list/scrollbar hover brushes and match the selected visual reference rather than assuming all hover states should lighten or darken.
- **RevitLookup `develop` UI, inspected October 2026:** uses [LookupEngine.UI](https://github.com/lookup-foundation/LookupEngine.UI), an adapted WPF UI library with shared controls/themes and Revit theme-change tracking. Custom controls require compiled assemblies: check framework compatibility before importing them into pyRevit. To imitate its appearance without that dependency, use a reusable WPF resource dictionary and standard controls/templates. Its default dark button hover **lightens**, rather than darkens.
- For loose-file dictionaries, load the root stylesheet from Python through an **absolute file URI**. Use `DynamicResource` when styles become available after XAML loads. In a standalone check, the installed IronPython loader failed to resolve a window-relative dictionary `Source`; loading an absolute `ResourceDictionary.Source` allowed nested relative resources to resolve. Keep light/dark resource keys identical, merge the selected palette **after** shared styles, verify loading with the installed loader, and then check the form in Revit.

## Native title bar

- WPF brushes do not alter the native Windows caption. Apply DWM title-bar attributes after `SourceInitialized`, or immediately if pyRevit has already created the window HWND.
- Declare HWND as a pointer-sized value and BOOL/COLORREF/HRESULT as **32-bit** native types. On Windows 11, explicit caption/text colours follow the chosen form palette independently of Windows' system theme.
- Log unsupported DWM attributes or interop failures without preventing the form from opening. For the IronPython 2 `ctypes` pointer issue, see [IronPython](ironpython.md).

## Colour gradients

- To position gradient stops based on colour separation, normalize cumulative distances between **adjacent** colours in a perceptual space such as **OKLab**.
- Preserve the selected interpolation method. Redistributing stop positions does **not** create discrete bands or ensure a perceptually uniform gradient *within* each interpolated segment.
