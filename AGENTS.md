# Repository conventions

This repository contains pyRevit tools for Autodesk Revit. Shared helpers, especially `lib/revitfunctions/PT_funcs.py`, support multiple commands and require careful changes.

## Scope and behaviour

- If the user requests a review or proposal without edits, keep the work read-only until edits are authorized. Once authorized, complete the requested change without repeatedly asking for permission.
- Keep changes focused. Preserve existing calculations, units, rounding, function signatures, parameter assignments, and transaction behaviour unless a change is explicitly requested or necessary to the agreed fix. Explain any intended behavioural differences.
- Before changing a shared helper, inspect its callers and references to any names being removed or changed. Avoid unrelated refactoring.
- Preserve existing file formatting and compatibility with the pyRevit engine used by the scripts. A local CPython check does not establish compatibility inside Revit.
- Whenever implementation, debugging, or user feedback reveals a reusable lesson for future scripts, update this `AGENTS.md` during the same task. Integrate the lesson into the relevant section, keep it concise, and distinguish observed results from assumptions or limitations.

## Revit document and view context

- Use one document context consistently for related calculations, queries, parameter updates, and element creation. Capture it when a command starts; make separate contexts explicit for deliberate operations across documents.
- Obtain views from that document using `DOC.ActiveView` or `doc.ActiveView`. When existing code uses `DOC`, keep its helpers tied to `DOC`; do not mix live `revit.doc` view data with creation against a different cached document.
- For new reusable helpers, pass the document or view explicitly. Avoid capturing active document or view objects in module globals that may survive across commands.
- Read level elevations and view ranges when needed, not during module import.

## Material-based join priorities

- Geometry Join ranks all supported pairs, including floor-to-floor pairs, using actual structural material names. Walls and floors prefer compound layers with the Structure function. Do not introduce family/type-name, floor-thickness, or floor-name priority overrides unless requested.
- When matching configured material labels, apply identical normalisation to the labels and the retrieved names. The Geometry Join `HERA_...` labels could not match when only retrieved names were lowercased and stripped of spaces, hyphens, and underscores. Preserve the configured priority order when fixing matching.

## Bulk transactions and performance

- For new bulk-edit commands, prefer one overall `DB.Transaction` with a `DB.SubTransaction` per item or pair when immediate failures need independent rollback. Full transaction commits regenerate the document; committing separately for every item can be much slower. In Geometry Join, the user confirmed a substantial speed improvement for 30 columns and a slab after replacing per-pair full transactions with one overall transaction and per-pair subtransactions. The improvement depends on the operation and model; preserve existing transaction behaviour unless changing it is authorized.
- A subtransaction isolates immediate exceptions and partial changes for its item, but its successful commit does not guarantee the overall transaction will succeed. Revit can detect additional failures at the overall commit. If that commit fails, the entire run is rolled back; report this accurately and do not retry items unless the user authorizes retries.
- A `DB.TransactionGroup` combines Undo history; it does not eliminate regeneration from the full transactions inside it. When an operation requires verification after commit, such as retained join cutter direction, a surrounding group can roll back the committed transaction if verification fails.

## Validation and error handling

- Add only checks required by the specific operation or needed for a useful error message. Level lookup checks for an associated level; view-range lookup checks for a plan view. Do not require unrelated view properties.
- For commands that already require an open Revit project, avoid redundant project-open guards.
- When adding logging, include useful context such as CSV row, operation, view, family, or parameter, along with the traceback. Keep rollback and stop/continue behaviour explicit; do not silently convert failures into success, skipped work, or fallback values.
- Keep successful runs quiet about log-file locations; display the saved log path once per run only when a warning or failure occurs.
- For partial family-based imports, resolve symbols once, warn once per missing family, and skip placement for that family while continuing available families. Preserve shared input context needed by other categories, such as tendon endpoints used to rotate height markers and text notes.

## Verification and reporting

- Scale verification to the change. For shared calculation changes, compare representative outputs and side effects with the prior implementation, including relevant failure paths. Use focused mocks when Revit is unavailable.
- Review the final diff for unintended edits and run applicable syntax and whitespace checks.
- State what was actually verified and what still needs verification in Revit. Describe an unverified lifecycle scenario as conditional; do not present a mock reproduction as an observed Revit failure.
