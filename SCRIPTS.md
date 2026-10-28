# Script-specific notes

Use this document for behaviour, constraints, thresholds, design decisions, and verification records belonging to **individual scripts or command bundles**. Keep reusable Revit, WPF, IronPython, and PDF24 lessons in the corresponding `docs/` file.

The printing and material-order paths below were confirmed from source imports and entry points during documentation consolidation on 2026-10-28. Source inspection does not establish a successful end-to-end Revit run.

## `lib/revitfunctions/PT_funcs.py` — shared helper module

- **Scope:** referenced as a helper shared by multiple pyRevit commands.
- **Before changes:** inspect callers and references to changed or removed functions; preserve existing behaviour unless the requested fix requires otherwise.
- **Verification status:** no function-level tests or compatibility results were supplied. Record observed results here after verifying in the relevant Revit/pyRevit versions.

## `MyTools.tab/Testing.panel/infopane.pulldown/PrintCurrentPDF.pushbutton/script.py`

- **Intended behaviour:** printer-specific configuration; submit each view with an identifiable output; do not open a PDF until its destination exists. A viewer-launch failure is distinct from a print/generation failure.
- **Special constraints:** temporary Revit model content and print setup used to control output must be cleaned up appropriately. Explicitly configure each submitted view to avoid print-setting leakage.
- **Source:** prints the active view through `lib/pdfprinting.py`; sanitizes its sheet number/name, prefixes the current date and opens the resulting PDF after printing returns. Printer-specific work is delegated to `lib/pdf24printing.py`, with output and setup helpers in `lib/pdfprintfiles.py` and `lib/revitpdfsettings.py`.
- **Reference:** [PDF24 and Revit printing](docs/pdf24.md).
- **Verification status:** the historical reference reports a Revit 2026 print-setup persistence issue without identifying the original command. The current command's path and helper imports were inspected; an end-to-end print test was not performed during documentation consolidation.

## `MyTools.tab/Testing.panel/infopane.pulldown/PrintByConvention.pushbutton/script.py`

- **Purpose:** reads PDF/DWG filename and output-directory conventions from CSV, resolves sheet-parameter tokens, and processes selected non-placeholder sheets.
- **Dependencies:** the PDF path imports `lib/pdfprinting.py`, `lib/pdfprintfiles.py` and `lib/revitpdfsettings.py`; DWG output uses Revit export options.
- **Constraints:** retain the shared PDF output/setup requirements described in [PDF24 and Revit printing](docs/pdf24.md).
- **Verification status:** path and implementation inspected during documentation consolidation; no PDF/DWG export or Revit runtime test performed.

## `MyTools.tab/Working.panel/General.pulldown/GeometryJoin.pushbutton/material_order_ui.py`

- **Entry point:** `GeometryJoin.pushbutton/script.py` calls `show_material_order` before joining selected elements.
- **Intended behaviour:** save names rather than document-specific IDs; preserve missing names in presets; append newly discovered materials after existing priorities. An initial alphabetical setup must not be flagged as an imported/remembered-order change.
- **Execution:** Close/X may save preferences but must not modify the Revit model; only explicit Run initiates the command after the dialog closes.
- **Reference:** [WPF dialogs and preferences](docs/wpf.md).
- **Verification status:** source confirms the universal settings file, preset reconciliation, close/save handling and Run result. No end-to-end UI test was performed during documentation consolidation.

## `MyTools.tab/Working.panel/QRCode.pushbutton/script.py`

- **Dependencies:** CPython (`#!python3`), Segno 1.6.6 bundled in `lib/segno` with its upstream LICENSE, and the existing PyPNG `lib/png.py`. No qrcode/Pillow imports. Segno wheel SHA256: `28c7d081ed0cf935e0411293a465efd4d500704072cdb039778a2ab8736190c7`.
- **Behaviour:** automatic standard QR version, error correction M without boosting, and 10-pixel module cells with centred 8-pixel coloured squares. No outer white quiet zone (`QUIET_ZONE = 0`); the one-pixel inset within each module cell remains. Split each matrix axis at the nearest whole module to one-third and two-thirds, excluding any outer border. Each of the nine regions is approximately one-ninth of the matrix area; segment widths/heights differ by at most one module. Choose one colour per dark module before drawing its pixels, so a square cannot straddle two colours. Keeps the existing 3-by-3 colour arrangement (including repeated colours), RGB values, input dialog and `~/Downloads/qrcode_color_replaced.png` destination. Segno may select a different encoding/mask from qrcode; gaps apply to all dark modules, including finder patterns. Generation/write errors propagate; cancellation skips generation. No Revit transactions or model edits.
- **Compatibility:** explicitly initializes the .NET Form base before setting WinForms properties; see `docs/ironpython.md`.
- **Observed verification (2026-10-28):** Revit 2024.3.6, pyRevit 7.0.0.26278+2233, CPython 3.12.3: real bundled imports, form construction/disposal, OK/Cancel handlers, 330-pixel URL output, quiet zone/module centre/gap samples, RGB PNG write/read equality in a temporary directory, Unicode and longer-input matrices, overflow propagation, and the cancellation branch passed (run `e61f623bfc98`). An earlier exhaustive pixel check exceeded the runner's 60-second tracing limit; focused checks replaced it. No mocks were used for generation, PNG or WinForms; temporary-path substitution and a stubbed input response covered save/cancel paths.
- **Observed colour/border verification (2026-10-28):** same Revit/CPython runtime, run `9f7065c98d45`: boundaries passed for all 40 standard QR versions; all-dark synthetic matrices of 21, 25 and 29 modules confirmed every rendered 8-by-8 square is uniformly coloured, with segment widths respectively 7/7/7, 8/9/8 and 10/9/10. Actual URL and Unicode QR images passed RGB PNG round trips, had dimensions exactly module count times 10, and started drawing the first dark square at pixel (1, 1), confirming removal of the former 40-pixel quiet zone. Synthetic matrix checks exercise the renderer; real payload checks use Segno and PyPNG without mocks. The earlier 330-pixel/border result describes the version before this update.
- **Dependency cleanup (2026-10-28):** Pillow/PIL was already absent from `lib`. Removed the obsolete `lib/qrcode` package and its otherwise-unused `lib/colorama` and `lib/typing_extensions.py` dependencies, including their bundled tests/caches (89 files). Searched hidden and ignored scripts as well as ordinary files; the only remaining command import was in `MyTools.tab/Testing.panel/Testings.pulldown/!ArchivedScripts/qrcode.py`. The user explicitly authorized ignoring archived-script imports, so that archived script is no longer supported by the bundled dependencies. Kept Segno, PyPNG and all unrelated helpers. Before removal, archived all 89 files in the temporary `trashheap-qr-deps/unused-qrcode-dependencies-before-removal.zip` and verified every member against source bytes (archive SHA256 `f9ea5c6a222c33fcc18f0f2fcf8fe68de8efe78718ebab995a7a9e5063ed799f`). After removal, real URL and Unicode generation/PNG round trips passed with Pillow and all removed modules blocked, using the installed pyRevit CPython 3.12.3 executable outside Revit. No generation mocks were used; WinForms/ribbon interaction was not repeated. Verified exactly the intended 89 files were removed and all 19 remaining library files were unchanged byte-for-byte; no non-archived script imports a removed package.
- **Unverified:** modal interaction launched from the ribbon, writing to the actual Downloads folder, scanner decoding of the coloured/gapped design, and other Revit versions. The full original bundle was archived and checked byte-for-byte before replacement; its Python, YAML and icon matched HEAD after newline normalization.

## Future entries

For each script, record:

- **Path and purpose:** actual repository-relative file/bundle paths.
- **Behaviour:** inputs, outputs, ordering, units, thresholds, and relevant dependencies.
- **Constraints:** decisions and limitations that should not change accidentally.
- **Verification:** what was run, in which Revit/pyRevit version, observed outcome, and remaining unverified cases.
