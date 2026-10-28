# PDF24 and Revit printing

Load this reference only when working on PDF printers, Revit printing, paper sizes, or PDF output handling. Printer behaviour depends on installed PDF24 Creator settings and version; verify these locally.

## PDF24 control codes

- PDF24 `@@fn` and `@@df` control codes must be **printed as document content**. Putting them in a print-job name or Revit `PrintToFileName` does not embed them in the PDF.
- They require PDF24 Creator **11.31.0 or later** and are enabled **per printer**, not automatically on every instance.
- Before adding temporary codes to a Revit view, check the installed version and printer configuration. After printing, roll back temporary model content and verify the codes are removed from the saved PDF.

## Printer identity and configuration

- PDF24 auto-save settings can be distinct for different PDF24 printers.
- The printer's Windows name may differ from its registry service key under `HKLM\SOFTWARE\PDF24\Services\`. For example, the default printer can be called `PDF24` while its service key is `PDF`.
- Represent both identifiers in a printer backend. Do not bake PDF24 registry naming assumptions into individual command scripts.

## Reliable output and replacement

- Revit can report successful submission to a virtual printer **before the PDF exists**. Determine that printer's actual output directory and naming rules, submit with a unique identifiable name, and monitor only the corresponding job output.
- A stable file size is not proof of completion. Check the `%PDF-` header and the final `%%EOF`, then wait for exclusive access before processing the file.
- Stage a copy in the destination folder before replacing the target; keep the old destination until a complete replacement is ready.
- Revit may reject a print when `PrintToFileName` points to an already-existing file, even if the configured PDF printer writes somewhere else.
- Open the final PDF only after the destination exists. Distinguish a viewer-launch problem from generation and file-placement failures.

## Revit print parameters

- Access to `PrintParameters.Zoom` throws when `ZoomType` is not `Zoom`. Set `ZoomType` **before** writing a percentage and check `ZoomType` **before** reading `Zoom`.
- Revit `PaperSize` exposes a name but not paper dimensions. For printing a view at 100% scale:
  1. Convert `View.Outline` from feet to inches.
  2. Read available paper sizes from the selected Windows printer, whose dimensions are expressed in **hundredths of an inch**.
  3. Match names/size and select the smallest available size that fits the requested orientation.

## Print-setup persistence — observed in Revit 2026

- Changing the in-session `PrintParameters` and calling `PrintManager.Apply()` inside a `DryTransaction` left a newly obtained `PrintManager` at its **previous paper and Fit to Page** values.
- Calling `PrintSetup.SaveAs()` made the updated setup visible to a fresh manager.
- Roll back/remove the temporary saved print setup once output is ready. Application-wide, in-session print values can survive rollback; explicitly configure **every** submitted PDF view when printing multiple sheets.

These observations describe tested behaviour in the stated environment, not a guarantee across all Revit versions or print drivers. Record per-command verification in [SCRIPTS.md](../SCRIPTS.md).
