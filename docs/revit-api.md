# Revit API: document context, transactions, and validation

Load this reference for Revit model changes, geometry/material queries, bulk edits, import workflows, failures, and API behaviour. Keep command-specific state and verification in [SCRIPTS.md](../SCRIPTS.md).

## Document and view context

- Capture one document context when a command begins and use it consistently for related queries, calculations, parameter changes, and element creation. Explicitly distinguish intentional multi-document operations.
- Obtain the view from that same document (`DOC.ActiveView` or `doc.ActiveView`). When a helper uses a cached `DOC`, do not combine a live `revit.doc` view with creation in a different document.
- New reusable helpers should accept the document/view as an argument, rather than capture active objects in module globals that may survive between commands.
- Query level elevations and view ranges when needed, **not during module import**.

## Bulk transactions and regeneration

- For **new** bulk-edit workflows requiring isolated immediate failures, prefer a single outer `DB.Transaction` with a `DB.SubTransaction` per item/pair. Separate full transaction commits can each regenerate the document and cost more time; performance depends on the model/operation. Do not change a working transaction strategy without authorization.
- A committed subtransaction protects only against **immediate** failures. Errors can surface at the **outer commit**; if that commit fails, the whole run is rolled back. Report this accurately, and do not retry items unless authorized.
- `DB.TransactionGroup` combines Undo history but does **not** eliminate regeneration caused by full transactions inside it. A surrounding group can roll back a previously committed transaction if post-commit verification fails.

## Failure handling and post-commit verification

- In `IFailuresPreprocessor`, distinguish `FailureSeverity.Warning` from errors. When authorized to dismiss a warning, capture descriptions and failing element IDs **before** `DeleteWarning`. Deleting a warning does not fix its underlying geometry.
- Never suppress unresolved errors or continue document access following fatal regeneration failure.
- For authorized native resolutions, compare **built-in failure IDs and affected elements**, not localized message strings. Confirm the proposed resolution is available and allowed, apply it only to the current operation, avoid repeated attempts, and check the resulting state **after commit** rather than treating dismissal as repair.
- **Revit 2026 example:** `ColumnInsideWallFailures.ColumnInsideWall` can provide the `DetachElements` / Unjoin Elements resolution.
- Scope resolutions to **live successful change results**, not an original list of all candidates. Otherwise a failed item may be modified at commit yet omitted from a success-only verification list. Report each resolved item separately.
- Look for existing known-invalid joins before editing: a relation/cutter test may not detect a joined-but-disjoint warning, and an existing warning may not be reposted during the new commit.
- When the operation intentionally permits partial results, independently report post-commit verification failures without undoing other valid successes; exclude **unverified items** from success counts.

## Data, geometry, selection, and imports

- For geometry-based queries, report geometry extraction or Boolean failures explicitly. Do not interpret them as zero overlap or a successful non-match.
- Add only relevant guards. A level query needs a corresponding level; a view-range query needs a plan view. Avoid checks for unrelated properties, and redundant project-open guards in commands already requiring a project.
- Filter unsupported selected categories **before** caching geometry/materials or computing element pairs. Enable execution according to **eligible** count, not raw selection count; report ineligible elements as ignored rather than failed.
- Normalize configured labels and retrieved names the same way. For exact-name priority operations, build a rank lookup once and preserve execution order from the displayed priority list.
- For partial family imports, resolve symbols once, warn **once per missing family**, skip placements for that family, and continue with available families. Preserve shared input context required by other categories.
- For ambiguous `.NET` overload resolution of `DB.ElementId` under IronPython, see [IronPython](ironpython.md).
