# Python runtimes and .NET interop

Read this when editing scripts that execute under IronPython or CPython/pythonnet, or call overloaded .NET APIs/native Windows functions. Revit runtime compatibility cannot be inferred from a successful CPython syntax check, mock, or native-call test.

## Runtime compatibility

- Preserve the script's expected pyRevit engine and Revit version. Check changes with the **installed interpreter/runtime**, and distinguish standalone IronPython checks from execution inside Revit.
- The installed pyRevit WPF loader may behave differently from current online examples. For details on XAML/resource loading and themes, see [WPF](wpf.md).
- In pyRevit 7.0.0.26278+2233, `pyrevit.forms` selects an engine-specific backend. Its CPython `forms.WPFWindow` is a stub that raises `PyRevitCPythonNotSupported`; this does not mean native .NET WPF is unavailable. For a CPython button, load loose XAML with `System.Windows.Markup.XamlReader.Load` and compose a Python controller around the resulting Window. Wire controls found with `FindName`, load resource dictionaries from absolute URIs, and set the owner through `WindowInteropHelper`. QRCode's helper was checked with the installed CPython/Python.NET and real WPF outside Revit using a stubbed host context, then verified in Revit 2026 / CPython 3.12.3 on 2026-10-29: the real modal Generate/Cancel/X flow, current dark theme and Revit-window ownership passed. A standalone host must load the WPF assemblies before embedding Python.NET; Revit normally already hosts them.

## CPython startup: dotted version parsed as an engine ID

- **Reported deployment failure (2026-10-29):** a recipient computer showed Revit's external-command failure with `The input string '3.12.3' was not in a correct format`. The user reports Revit 2026.5 and pyRevit 6.0.0. Its journal and active attachment have not been inspected, so the exact loader path remains unverified. The QR tool's successful local test used Revit 2026 build 26.5.0.55 and pyRevit 7.0.0.26278+2233; matching that tested pyRevit release is the recommended next deployment step. The 6.4.0 workaround below is not verified on 6.0.0.
- This matches [pyRevit issue 3478](https://github.com/pyrevitlabs/pyRevit/issues/3478): in pyRevit 6.4.0's C# loader, `PYREVIT_CPYVERSION` was seeded as `3.12.3`, while `CPythonEngine.GetPythonDll` expected integer engine ID `3123`. The exception occurs before the user script is read; adding extension libraries or a try/except inside that script cannot repair this startup failure. A bare engine initialization test can pass while full command dispatch fails.
- The upstream report identifies 6.5.0.26173+1406 as the first fixed release and confirms success on 6.5.5.26237+2044. Check the affected machine's actual pyRevit attachment and Revit year before choosing an upgrade. For affected 6.4.0 installations, the reported workaround is to close Revit, back up the active pyRevit configuration, set `new_loader = false` in its existing `[core]` section, and restart Revit. The report used `%APPDATA%\pyRevit\pyRevit_config.ini`; use `pyrevit env` to identify the active config for a different installation scope. This workaround was reported upstream, not tested on the recipient computers in this task.

## Overloaded .NET constructors

- Python integers can ambiguously bind to overloads accepting both an enum and a numeric value.
- **Observed in Revit 2026:** `DB.ElementId(1)` failed between the enum and `Int64` overloads during a read-only check. In Revit 2024+, pass numeric IDs explicitly as `DB.ElementId(System.Int64(value))`. Pass actual enum values when an enum overload is intended.

## IronPython 2 `ctypes` pointer marshalling

- **Observed in Revit and reproduced using the installed IronPython 2 runtime:** passing `ctypes.byref(value)` to a declared `c_void_p` argument failed with `expected pointer, got NativeArgument`.
- For the affected interop call, use `ctypes.c_void_p(ctypes.addressof(value))`, keeping `value` alive until the native call completes.
- Test native argument marshalling in **IronPython itself**. CPython native-call tests and IronPython syntax/lifecycle checks alone did not reveal this incompatibility.

## Windows title-bar interop

- When setting WPF window DWM captions, use pointer-sized HWND declarations, 32-bit BOOL/COLORREF/HRESULT, and run the native operation after `SourceInitialized` (or once HWND already exists).
- Unsupported attributes/interop failures should be logged without blocking the dialog. See [WPF](wpf.md) for the title-bar styling requirements.

## WinForms subclasses under CPython/pythonnet

Initialize a `System.Windows.Forms.Form` subclass with `Form.__init__(self)` before assigning inherited properties such as `Text` or adding controls. In the installed pyRevit CPython 3.12.3 runtime on Revit 2024.3.6, omitting this initialization caused `System.NullReferenceException` in `Control.get_CacheTextInternal` / `Control.set_Text`. Explicit base initialization allowed construction, event handlers and disposal to pass.

This was observed in `MyTools.tab/Working.panel/QRCode.pushbutton/script.py`. A `#!python3` button uses the CPython engine even when the default pyRevit engine is IronPython. Test against the actual selected engine; standalone Python syntax checks do not exercise .NET control construction. IronPython and other Revit versions were not verified in this task.

## Windows paths and Explorer links under CPython

Expanding a path such as `~/Downloads` can leave mixed separators when combined with Windows paths. Normalize filesystem/display paths with `os.path.normpath`.

Do not assume an HTML `file://` link opens Explorer in the installed pyRevit output window. Inspection of pyRevit 7.0.0.26278+2233 on Revit 2024 found that its WebView2 navigation handler cancels `file` navigation; the available output helper commands have no folder-opening action. Its documented `output.renderer` API is also unavailable with WebView2. A native WinForms LinkLabel can launch Explorer explicitly with `subprocess.Popen(["explorer.exe", folder_path])`. Pass arguments as a list, and report launch errors separately from successful file generation. QRCode verification raised the actual native link event and launched Explorer for Downloads under CPython 3.12.3; special-character argument and error-path checks used mocks.
