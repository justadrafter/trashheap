# Python runtimes and .NET interop

Read this when editing scripts that execute under IronPython or CPython/pythonnet, or call overloaded .NET APIs/native Windows functions. Revit runtime compatibility cannot be inferred from a successful CPython syntax check, mock, or native-call test.

## Runtime compatibility

- Preserve the script's expected pyRevit engine and Revit version. Check changes with the **installed interpreter/runtime**, and distinguish standalone IronPython checks from execution inside Revit.
- The installed pyRevit WPF loader may behave differently from current online examples. For details on XAML/resource loading and themes, see [WPF](wpf.md).

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
