# Repository instructions

This repository contains pyRevit tools for Autodesk Revit. Shared helpers, including `lib/revitfunctions/PT_funcs.py`, may be called by multiple commands.

## Editing rules

- Treat review/proposal requests as **read-only**. Once edits are authorized, carry them out without repeatedly asking for permission.
- Keep changes scoped to the request. Preserve calculations, units, rounding, interfaces, parameter assignments, transaction behaviour, and formatting unless a change is needed. Explain intended behavioural differences.
- Before changing a shared helper, inspect its callers and references to renamed or removed symbols. Avoid unrelated refactors.
- Use the **actual installed pyRevit engine and Revit version** as compatibility targets; CPython checks do not prove Revit/IronPython compatibility.
- Before recovery/overwrite work, snapshot the command bundle, compare verified previous versions, and restore associated Python, XAML, and resource files together. Verify archive files against source bytes.

## Read context selectively

Read **only the relevant** reference before working on a feature; do not preload every document:

- [Revit API](docs/revit-api.md): document/view context, transactions, failures, geometry, imports.
- [WPF](docs/wpf.md): dialogs, previews, preferences, XAML, themes, styles.
- [PDF24](docs/pdf24.md): PDF printing, output verification, paper sizes, print setup.
- [Python runtimes and .NET interop](docs/ironpython.md): IronPython, CPython/pythonnet, .NET overloads, native interop.
- [Script notes](SCRIPTS.md): specific command behaviour and verification; inspect the relevant entry when editing a script.

## Validation and reporting

- Guard only conditions relevant to the operation. Never silently treat failures as success, skipped work, zero geometry, or fallback values.
- Log actionable context and tracebacks. Define stop/continue and rollback behaviour; show log-file locations only if warnings/errors occur.
- For shared calculations, compare representative results, side effects, and failure paths with the previous version. Use focused mocks when Revit is unavailable.
- Check the final diff and applicable syntax/whitespace tests. Distinguish **observed results**, **mock-only checks**, and **unverified Revit scenarios**.
- Record newly discovered reusable failure patterns in the relevant `docs/` topic during the same task. Put script-specific decisions, thresholds, limitations, and verification results in `SCRIPTS.md`, grouped by real script path when known.
