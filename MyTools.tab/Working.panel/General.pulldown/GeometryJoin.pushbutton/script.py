"""
Process selected element joins in Revit 2024 and newer.

Only walls, structural columns, floors, structural framing, and structural
foundations participate. Wall-to-wall pairs are ignored.

Usage:
1. Select elements in the Revit model.
2. Run the script and arrange the material priority list (highest first).
3. Click Run joins. Close or X exits without changing joins.

All pair priorities use the UI's exact structural material names; higher scores cut.
Walls and floors prefer compound layers with the Structure function.
Wall-to-wall pairs are ignored. Equal or unmatched priorities retain the order.
Changed pairs use subtransactions inside one overall transaction and Undo item.
Pair failures and commit warnings are reported at the end; successful joins remain.
An overall commit or fatal regeneration failure rolls back the run without retries.
"""

from pyrevit import revit, DB, script
from Autodesk.Revit.Exceptions import RegenerationFailedException
from material_order_ui import show_material_order
import heapq
import traceback

__title__ = "Geometry Join Order"
__author__ = "Adam Shaw"

DOC = revit.doc
UIDOC = revit.uidoc


def structural_material_parameter(element):
    """Read the actual structural-material assignment, when available."""
    parameter = element.get_Parameter(DB.BuiltInParameter.STRUCTURAL_MATERIAL_PARAM)
    if parameter is not None and parameter.HasValue:
        material_id = parameter.AsElementId()
        if material_id.Value > 0:
            return material_id
    return None


def type_structural_materials(doc, element, cache):
    """Cache layer/parameter material IDs without inspecting type names."""
    types = cache.setdefault("types", {})
    type_id = element.GetTypeId()
    type_key = type_id.Value
    if type_key not in types:
        element_type = doc.GetElement(type_id)
        structure_ids = []
        assigned_id = None
        if element_type is not None:
            if isinstance(element, (DB.Wall, DB.Floor)) and isinstance(element_type, DB.HostObjAttributes):
                compound = element_type.GetCompoundStructure()
                if compound is not None:
                    try:
                        indices = [index for index in range(compound.LayerCount)
                                   if compound.GetLayerFunction(index) == DB.MaterialFunctionAssignment.Structure]
                        structural_index = compound.StructuralMaterialIndex
                        if structural_index in indices:
                            indices = [structural_index]
                        for index in indices:
                            material_id = compound.GetMaterialId(index)
                            if material_id.Value == -1:
                                # Resolve <By Category> from the Structure subcategory,
                                # then the element category, using this same document.
                                category_id = (DB.BuiltInCategory.OST_WallsStructure
                                               if isinstance(element, DB.Wall)
                                               else DB.BuiltInCategory.OST_FloorsStructure)
                                category = DB.Category.GetCategory(doc, category_id)
                                material = category.Material if category is not None else None
                                if material is None:
                                    category = element.Category
                                    material = category.Material if category is not None else None
                                material_id = material.Id if material is not None else None
                            if material_id is not None and material_id.Value > 0:
                                if all(existing.Value != material_id.Value for existing in structure_ids):
                                    structure_ids.append(material_id)
                    finally:
                        compound.Dispose()
            if not structure_ids:
                assigned_id = structural_material_parameter(element_type)
        types[type_key] = {"structure_ids": structure_ids, "assigned_id": assigned_id}
    return types[type_key]


def element_structural_materials(doc, element, cache):
    """Prefer Structure layers for hosts and instance assignments elsewhere."""
    type_data = None
    if isinstance(element, (DB.Wall, DB.Floor)):
        type_data = type_structural_materials(doc, element, cache)
        if type_data["structure_ids"]:
            return type_data["structure_ids"], "Structure layer"
    if isinstance(element, DB.FamilyInstance):
        material_id = element.StructuralMaterialId
        if material_id.Value > 0:
            return [material_id], "Instance structural material"
    material_id = structural_material_parameter(element)
    if material_id is not None:
        return [material_id], "Instance structural material parameter"
    if type_data is None:
        type_data = type_structural_materials(doc, element, cache)
    if type_data["assigned_id"] is not None:
        return [type_data["assigned_id"]], "Type structural material parameter"
    return [], "No Structure layer or structural material assignment"


class JoinFailures(DB.IFailuresPreprocessor):
    """Unjoin invalid changed pairs; preserve failed and unchanged pairs."""

    def __init__(self, pair_results=None):
        self.messages = []
        self.warnings = []
        self.skipped_pairs = {}
        # Keep the live results: failures/unchanged pairs must not be resolved.
        self._pair_results = pair_results if pair_results is not None else {}
        self._attempted_unjoins = set()

    def PreprocessFailures(self, accessor):
        resolved = False
        for failure in list(accessor.GetFailureMessages()):
            message = failure.GetDescriptionText()
            element_ids = list(failure.GetFailingElementIds())
            severity = failure.GetSeverity()
            pair_key = tuple(sorted(eid.Value for eid in element_ids))
            failure_id = failure.GetFailureDefinitionId()
            invalid_join = failure_id.Equals(
                DB.BuiltInFailures.ColumnInsideWallFailures.ColumnInsideWall
            ) or failure_id.Equals(DB.BuiltInFailures.JoinElementsFailures.JoiningDisjointWarn)
            result = self._pair_results.get(pair_key)
            if (invalid_join and result is not None and any(result)
                    and severity in (DB.FailureSeverity.Warning, DB.FailureSeverity.Error)):
                resolution = DB.FailureResolutionType.DetachElements
                if (pair_key in self._attempted_unjoins
                        or not failure.HasResolutionOfType(resolution)
                        or not accessor.IsFailureResolutionPermitted(failure, resolution)):
                    self.messages.append("Could not unjoin invalid pair {}: {}".format(pair_key, message))
                    continue
                self._attempted_unjoins.add(pair_key)
                failure.SetCurrentResolutionType(resolution)
                accessor.ResolveFailure(failure)
                self.skipped_pairs[pair_key] = message
                resolved = True
                continue
            if severity == DB.FailureSeverity.Warning:
                self.warnings.append((element_ids, message))
                accessor.DeleteWarning(failure)
            else:
                if element_ids:
                    message = "{} (elements {})".format(message, ", ".join(str(eid.Value) for eid in element_ids))
                self.messages.append(message)
        if self.messages:
            return DB.FailureProcessingResult.ProceedWithRollBack
        if resolved:
            return DB.FailureProcessingResult.ProceedWithCommit
        return DB.FailureProcessingResult.Continue


def existing_invalid_joins(doc, pair_keys):
    """Skip known invalid joins without changing their pre-run relationship."""
    invalid = {}
    if not pair_keys:
        return invalid
    for warning in doc.GetWarnings():
        failure_id = warning.GetFailureDefinitionId()
        if (failure_id.Equals(DB.BuiltInFailures.ColumnInsideWallFailures.ColumnInsideWall)
                or failure_id.Equals(DB.BuiltInFailures.JoinElementsFailures.JoiningDisjointWarn)):
            pair_key = tuple(sorted(eid.Value for eid in warning.GetFailingElements()))
            if pair_key in pair_keys:
                invalid[pair_key] = warning.GetDescriptionText()
    return invalid


class CachedElement(object):
    """Snapshot broad-phase geometry and lazily cache each element's priority."""

    def __init__(self, element, index):
        self.element = element
        self.id = element.Id
        self.key = self.id.Value
        self.index = index
        category = element.Category
        self.category_key = category.Id.Value if category else None
        bbox = element.get_BoundingBox(None)
        self.bounds = None
        if bbox is not None:
            self.bounds = (
                (bbox.Min.X, bbox.Min.Y, bbox.Min.Z),
                (bbox.Max.X, bbox.Max.Y, bbox.Max.Z),
            )
        self._material_importance = None
        self._material_loaded = False
        self._material_names = []
        self._material_source = None

    def material_importance(self, type_cache):
        """Cache priority from actual structural materials, never element names."""
        if not self._material_loaded:
            material_ids, self._material_source = element_structural_materials(DOC, self.element, type_cache)
            materials = type_cache.setdefault("materials", {})
            scores = []
            for material_id in material_ids:
                material_key = material_id.Value
                if material_key not in materials:
                    material = DOC.GetElement(material_id)
                    name = material.Name if material is not None else ""
                    materials[material_key] = {"name": name, "importance": type_cache["priority_by_name"].get(name)}
                data = materials[material_key]
                self._material_names.append(data["name"] or "Missing material {}".format(material_key))
                if data["importance"] is not None:
                    scores.append(data["importance"])
            self._material_importance = max(scores) if scores else None
            self._material_loaded = True
        return self._material_importance


def candidate_pairs(elements, tolerance):
    """Sweep cached boxes along the axis with the fewest interval overlaps.

    Each unordered pair is yielded once. These pre-join bounds are a broad
    filter only; join state and cutter direction are read live from Revit.
    """
    bounded = [element for element in elements if element.bounds is not None]
    if len(bounded) < 2:
        return

    best_order = None
    best_axis = None
    best_count = None
    for axis in range(3):
        ordered = sorted(bounded, key=lambda element: element.bounds[0][axis])
        ends = []
        overlap_count = 0
        for element in ordered:
            minimum = element.bounds[0][axis]
            while ends and ends[0] + tolerance < minimum:
                heapq.heappop(ends)
            overlap_count += len(ends)
            heapq.heappush(ends, element.bounds[1][axis])
        if best_count is None or overlap_count < best_count:
            best_order, best_axis, best_count = ordered, axis, overlap_count

    other_axes = [axis for axis in range(3) if axis != best_axis]
    active = []
    for element in best_order:
        minimum = element.bounds[0][best_axis]
        active = [other for other in active if other.bounds[1][best_axis] + tolerance >= minimum]
        for other in active:
            if any(
                element.bounds[0][axis] > other.bounds[1][axis] + tolerance
                or other.bounds[0][axis] > element.bounds[1][axis] + tolerance
                for axis in other_axes
            ):
                continue
            # Preserve selection order for default cutters and priority ties.
            if element.index < other.index:
                yield element, other
            else:
                yield other, element
        active.append(element)


def selected_pairs(element_cache, tolerance, notices):
    """Include existing joins even when their current bounding boxes miss."""
    elements = sorted(element_cache.values(), key=lambda element: element.index)
    for first in elements:
        try:
            joined_ids = DB.JoinGeometryUtils.GetJoinedElements(DOC, first.element)
        except RegenerationFailedException:
            raise
        except Exception as error:
            notices.append((first.id, "Could not read existing joins: {}".format(error)))
            continue
        for joined_id in joined_ids:
            second = element_cache.get(joined_id.Value)
            if second is None or second.key == first.key:
                continue
            if first.index < second.index:
                yield first, second
            else:
                yield second, first
    for first, second in candidate_pairs(elements, tolerance):
        yield first, second


def main():
    """
    Main function to execute the script logic.
    """
    output = script.get_output()
    logger = script.get_logger()
    if DOC is None or UIDOC is None:
        output.print_md("Open a Revit project and select at least two elements.")
        return
    if DOC.IsFamilyDocument or DOC.IsReadOnly or DOC.IsModifiable:
        output.print_md("Run this tool in an editable project with no transaction already open.")
        return
    selection = UIDOC.Selection
    selected_ids = list(selection.GetElementIds())
    supported_categories = set(int(category) for category in (
        DB.BuiltInCategory.OST_Walls,
        DB.BuiltInCategory.OST_StructuralColumns,
        DB.BuiltInCategory.OST_Floors,
        DB.BuiltInCategory.OST_StructuralFraming,
        DB.BuiltInCategory.OST_StructuralFoundation,
    ))
    selected_elements = []
    notices = []
    ignored_count = 0
    for element_id in selected_ids:
        try:
            element = DOC.GetElement(element_id)
            if element is None:
                raise ValueError("The selected element no longer exists.")
            category = element.Category
            if category is None or category.Id.Value not in supported_categories:
                ignored_count += 1
                continue
            selected_elements.append(element)
        except RegenerationFailedException:
            raise
        except Exception as error:
            notices.append((element_id, "Could not read selected element: {}".format(error)))
    material_order = show_material_order(DOC, can_run=len(selected_elements) >= 2)
    if material_order is None:
        return

    tolerance = DB.UnitUtils.ConvertToInternalUnits(20.0, DB.UnitTypeId.Millimeters)
    element_cache = {}
    # The UI is highest-first; build one exact-name lookup for this run.
    type_cache = {"priority_by_name": {name: len(material_order) - index
                                       for index, name in enumerate(material_order)}}
    for index, element in enumerate(selected_elements):
        element_id = element.Id
        key = element_id.Value
        if key not in element_cache:
            try:
                element_cache[key] = CachedElement(element, index)
            except RegenerationFailedException:
                raise
            except Exception as error:
                notices.append((element_id, "Could not cache selected element: {}".format(error)))

    pair_results = {}
    failures = []
    joined_count = 0
    switched_count = 0
    wall_key = int(DB.BuiltInCategory.OST_Walls)
    pairs = []
    # Finish discovery before editing, so queries do not observe partial changes.
    for first, second in selected_pairs(element_cache, tolerance, notices):
        if first.category_key == wall_key and second.category_key == wall_key:
            continue
        pair_key = (min(first.key, second.key), max(first.key, second.key))
        if pair_key not in pair_results:
            pair_results[pair_key] = None
            pairs.append((pair_key, first, second))

    # One warning scan also catches existing warnings that commit may not repost.
    invalid_existing = existing_invalid_joins(DOC, pair_results)
    # Keep one Undo item and roll back only for an overall transaction failure.
    transaction_group = DB.TransactionGroup(DOC, "Update Element Joins")
    join_transaction = DB.Transaction(DOC, "Update Element Joins")
    failure_handler = JoinFailures(pair_results)
    overall_error = None
    try:
        if transaction_group.Start() != DB.TransactionStatus.Started:
            raise RuntimeError("Could not start the join transaction group.")
        if join_transaction.Start() != DB.TransactionStatus.Started:
            raise RuntimeError("Could not start the overall join transaction.")
        options = join_transaction.GetFailureHandlingOptions()
        options = options.SetFailuresPreprocessor(failure_handler)
        options = options.SetClearAfterRollback(True)
        options = options.SetForcedModalHandling(True)
        join_transaction.SetFailureHandlingOptions(options)
        for pair_key, first, second in pairs:
            if pair_key in invalid_existing:
                failures.append((first.id, second.id,
                                 "Skipped existing invalid join; left unchanged: {}".format(invalid_existing[pair_key]),
                                 None))
                continue
            try:
                joined, switched = update_join(first, second, type_cache)
                pair_results[pair_key] = (joined, switched)
                joined_count += int(joined)
                switched_count += int(switched)
            except RegenerationFailedException:
                # A regeneration failure requires stopping access to this document.
                raise
            except Exception as error:
                failures.append((first.id, second.id, "Could not update join: {}".format(error),
                                 traceback.format_exc()))
        if joined_count or switched_count:
            if join_transaction.Commit() != DB.TransactionStatus.Committed:
                message = "; ".join(failure_handler.messages) or "The overall join transaction did not commit."
                raise RuntimeError(message)
            # Regeneration can affect earlier pairs sharing a slab/wall. Check all
            # successful pairs only after the one overall commit has completed.
            for pair_key, first, second in pairs:
                if pair_key in failure_handler.skipped_pairs:
                    result = pair_results[pair_key]
                    if result is not None:
                        joined_count -= int(result[0])
                        switched_count -= int(result[1])
                    pair_results[pair_key] = None
                    message = "Skipped and unjoined: {}".format(failure_handler.skipped_pairs[pair_key])
                    error_trace = None
                    try:
                        if DB.JoinGeometryUtils.AreElementsJoined(DOC, first.element, second.element):
                            raise RuntimeError("Revit did not remove the invalid join.")
                    except RegenerationFailedException:
                        raise
                    except Exception as error:
                        message = "Could not verify the invalid pair was unjoined: {}".format(error)
                        error_trace = traceback.format_exc()
                    failures.append((first.id, second.id, message, error_trace))
                    continue
                if pair_results[pair_key] is None:
                    continue
                try:
                    verify_join(DOC, first, second, desired_cutter(first, second, type_cache))
                except RegenerationFailedException:
                    raise
                except Exception as error:
                    joined, switched = pair_results[pair_key]
                    joined_count -= int(joined)
                    switched_count -= int(switched)
                    pair_results[pair_key] = None
                    failures.append((first.id, second.id,
                                     "Post-commit verification failed; this pair was not undone: {}".format(error),
                                     traceback.format_exc()))
        else:
            # Avoid a regeneration commit when every pair is unchanged or failed.
            join_transaction.RollBack()
        if transaction_group.Assimilate() != DB.TransactionStatus.Committed:
            raise RuntimeError("The join transaction group did not commit.")
    except Exception as error:
        if join_transaction.GetStatus() == DB.TransactionStatus.Started:
            join_transaction.RollBack()
        if transaction_group.GetStatus() == DB.TransactionStatus.Started:
            transaction_group.RollBack()
        if isinstance(error, RegenerationFailedException):
            raise
        logger.exception("Update Element Joins failed; all changes from this run were rolled back.")
        overall_error = str(error)
    finally:
        join_transaction.Dispose()
        transaction_group.Dispose()

    if overall_error is not None:
        output.print_md("**Join update failed: all changes from this run were rolled back. No pairs were retried.**")
        print(overall_error)
    else:
        output.print_md("Checked **{}** pairs across **{}** elements; verified new joins **{}**, verified order changes **{}**, skipped/failed **{}**.".format(
            len(pair_results), len(element_cache), joined_count, switched_count, len(failures)
        ))
    if ignored_count:
        output.print_md("Ignored **{}** selected element(s) outside the supported join categories.".format(ignored_count))
    for element_id, message in notices:
        print("{}: {}".format(output.linkify(element_id), message))
    unmatched_elements = [element for element in element_cache.values()
                          if element._material_loaded and element._material_importance is None]
    if unmatched_elements:
        output.print_md("**Missing/unmatched structural materials: material-based reordering skipped for these elements.**")
        for element in unmatched_elements:
            print("{}: {}; materials: {}".format(
                output.linkify(element.id), element._material_source,
                ", ".join(element._material_names) or "none"
            ))
    if failures:
        output.print_md("**{} join pair(s) skipped, failed, or could not be verified:**".format(len(failures)))
        for first_id, second_id, message, error_trace in failures:
            print("{} / {}: {}".format(
                output.linkify(first_id), output.linkify(second_id), message
            ))
            if error_trace:
                logger.error("Join pair {} / {}: {}\n{}".format(first_id.Value, second_id.Value, message, error_trace))
    if failure_handler.warnings:
        output.print_md("**{} Revit commit warning(s), recorded and dismissed:**".format(len(failure_handler.warnings)))
        for element_ids, message in failure_handler.warnings:
            links = ", ".join(output.linkify(eid) for eid in element_ids) or "No element IDs supplied"
            print("{}: {}".format(links, message))


def desired_cutter(first, second, type_cache):
    """Return whether the first element should cut, or None to keep the order."""
    if first.category_key is None or second.category_key is None:
        return None
    first_score = first.material_importance(type_cache)
    second_score = second.material_importance(type_cache)
    if first_score is None or second_score is None:
        return None
    first_should_cut = first_score > second_score
    return first_should_cut if first_score != second_score else None


def update_join(first, second, type_cache):
    """Update one pair in a subtransaction within the overall transaction."""
    wall_key = int(DB.BuiltInCategory.OST_Walls)
    if first.category_key == wall_key and second.category_key == wall_key:
        return False, False
    elem, other_elem = first.element, second.element
    first_should_cut = desired_cutter(first, second, type_cache)
    already_joined = DB.JoinGeometryUtils.AreElementsJoined(DOC, elem, other_elem)
    switch_needed = False
    if already_joined:
        if first_should_cut is not None:
            switch_needed = DB.JoinGeometryUtils.IsCuttingElementInJoin(DOC, elem, other_elem) != first_should_cut
        if not switch_needed:
            return False, False

    pair_transaction = DB.SubTransaction(DOC)
    try:
        if pair_transaction.Start() != DB.TransactionStatus.Started:
            raise RuntimeError("Could not start the join pair subtransaction.")
        if not already_joined:
            DB.JoinGeometryUtils.JoinGeometry(DOC, elem, other_elem)
            if first_should_cut is not None:
                switch_needed = DB.JoinGeometryUtils.IsCuttingElementInJoin(DOC, elem, other_elem) != first_should_cut
        if switch_needed:
            DB.JoinGeometryUtils.SwitchJoinOrder(DOC, elem, other_elem)
            if DB.JoinGeometryUtils.IsCuttingElementInJoin(DOC, elem, other_elem) != first_should_cut:
                raise RuntimeError("The join order did not change to the required cutter.")
        if pair_transaction.Commit() != DB.TransactionStatus.Committed:
            raise RuntimeError("The join pair subtransaction did not commit.")
    except Exception:
        if pair_transaction.GetStatus() == DB.TransactionStatus.Started:
            pair_transaction.RollBack()
        raise
    finally:
        pair_transaction.Dispose()
    return not already_joined, switch_needed


def verify_join(doc, first, second, first_should_cut):
    """Verify persisted join state after the overall transaction regenerates."""
    if not DB.JoinGeometryUtils.AreElementsJoined(doc, first.element, second.element):
        raise RuntimeError("Revit did not retain the geometry join after commit.")
    if first_should_cut is not None:
        if DB.JoinGeometryUtils.IsCuttingElementInJoin(doc, first.element, second.element) != first_should_cut:
            raise RuntimeError("Revit did not retain the required cutter after commit.")


if __name__ == "__main__":
    main()
