import math
from pyrevit import revit, DB, forms


UIDOC = revit.uidoc
DOC = UIDOC.Document

POINT_FAMILYSYMBOL = "PT Height_HERA"
POINT_TYPE = "PT Height"
TENDON_FAMILYSYMBOL = "PT Tendon_HERA"
TENDON_TYPE = "PT Tendon"

XYTOLERANCE = 100.0 / 304.8
ANGLETOLERANCE = 10.0 / 180 * math.pi


class Tendon:
    def __init__(self, tendon_curve_elem, sorted_points, tendon_mark="0"):
        # Tendon
        self.curve_elem = tendon_curve_elem
        self.direction = tendon_curve_elem.Location.Curve.Direction
        self.curve = get_actual_tendon_curve(tendon_curve_elem)
        self.flat_length = self.curve.Length * 304.8
        self.start_point = self.curve.GetEndPoint(0)
        self.end_point = self.curve.GetEndPoint(1)
        self.start_height = sorted_points[0].LookupParameter("Height").AsValueString()
        self.end_height = sorted_points[-1].LookupParameter("Height").AsValueString()
        self.start_type = self.curve_elem.LookupParameter("Start").AsValueString()
        self.end_type = self.curve_elem.LookupParameter("End").AsValueString()
        self.strandnum = "12.7"
        self.assign_tendon_mark(tendon_mark)
        self.grouping = "0"

        # Tendon Points
        self.sorted_points = sorted_points
        self.sorted_heights = [
            pt.LookupParameter("Height").AsValueString() for pt in sorted_points
        ]
        self.assign_point_marks()  # Id
        self.assign_point_types()  # High,Low,Inter
        self.assign_points_string()  # Point heights of low/high as a string 'Id'
        self.assign_points_distances()  # Distances between low/high heights

    def assign_point_types(self):
        sorted_types = []
        for point in self.sorted_points:
            if point.LookupParameter("HIGH").AsInteger() == 1:
                sorted_types.append("HIGH")
            elif point.LookupParameter("LOW").AsInteger() == 1:
                sorted_types.append("LOW")
            elif point.LookupParameter("END").AsInteger() == 1:
                sorted_types.append("END")
            else:
                sorted_types.append("INTER")
        self.sorted_types = sorted_types

    def assign_tendon_mark(self, tendon_mark="0"):
        self.mark = str(tendon_mark)
        self.curve_elem.LookupParameter("Mark").Set(self.mark)

    def assign_point_marks(self):
        self.sorted_marks = [
            self.mark + "." + str(idx)
            for idx, _ in enumerate(self.sorted_points, start=1)
        ]
        for point, mark in zip(self.sorted_points, self.sorted_marks):
            point.LookupParameter("Mark").Set(mark)

    def assign_points_string(self):
        points_string = ""
        points_string_reverse = ""
        points_primary = self.list_primary_point_heights()
        points_string = "".join(points_primary)
        points_string_reverse += "".join(points_primary[::-1])
        self.points_string = (points_string, points_string_reverse)

    def assign_points_distances(self):
        dist = []
        for idx in range(len(self.sorted_points) - 1):
            dist.append(
                self.sorted_points[idx].Location.Point.DistanceTo(
                    self.sorted_points[idx + 1].Location.Point
                )
                * 304.8
            )
        self.points_distances = dist

    def list_primary_points(self):
        points_primary = []
        for point, type in zip(self.sorted_points, self.sorted_types):
            if type == "HIGH" or type == "LOW" or type == "END":
                points_primary.append(point)
        return points_primary

    def list_primary_point_heights(self):
        points_primary = []
        for height, type in zip(self.sorted_heights, self.sorted_types):
            if type == "HIGH" or type == "LOW" or type == "END":
                points_primary.append(height)
        return points_primary

    def create_intermediate_points(self):
        prim_points = self.list_primary_points()
        for idx in range(len(prim_points) - 1):
            start_height = (
                float(self.sorted_heights[idx])
                + get_bottom_and_top_RL(prim_points[idx].Location.Point)[0]
            )
            end_height = (
                float(self.sorted_heights[idx + 1])
                + get_bottom_and_top_RL(prim_points[idx + 1].Location.Point)[0]
            )
            create_components_between_points(
                prim_points[idx].Location.Point,
                start_height,
                prim_points[idx + 1].Location.Point,
                end_height,
                POINT_FAMILYSYMBOL,
                DOC,
                DOC.ActiveView,
            )

    def print_attributes(self):
        print("Tendon: #{}".format(self.mark))
        print(
            "Start Point: {:.2f}, {:.2f}".format(self.start_point.X, self.start_point.Y)
        )
        print("Start Height: {}".format(self.start_height))
        print("Length: {:.2f}".format(self.flat_length))
        print("End Point: {:.2f}, {:.2f}".format(self.end_point.X, self.end_point.Y))
        print("End Height: {}".format(self.end_height))
        print("Start Type: {}".format(self.start_type))
        print("End Type: {}".format(self.end_type))
        print("Sorted Points:")
        for point, height, type, mark in zip(
            self.sorted_points,
            self.sorted_heights,
            self.sorted_types,
            self.sorted_marks,
        ):
            print(
                "#{} : ({:.2f}, {:.2f}) is {} at {}".format(
                    mark, point.Location.Point.X, point.Location.Point.Y, type, height
                )
            )
        print("Points String: {}".format(self.points_string))


def get_height_and_location(detail_item):
    elem_location = detail_item.Location.Point
    height_param = (
        round(float(detail_item.LookupParameter("Height").AsValueString()), 0)
        + get_bottom_and_top_RL(detail_item.Location.Point)[0]
    )
    return height_param, elem_location


def get_midheight_at_location(location_point):
    bottom_rl, top_rl = get_bottom_and_top_RL(location_point)
    distance = (top_rl - bottom_rl) / 2
    return distance


def calculate_height(distance, total_distance, height_sp, height_ep, radius=-5000):
    if height_sp > height_ep:
        height_sp, height_ep = height_ep, height_sp
        distance = total_distance - distance

    if height_ep - height_sp != 0:
        g_x = (
            distance**2 / (2 * radius + total_distance**2 / (height_ep - height_sp))
            + height_sp
        )
    else:
        g_x = height_sp
    h_x = (distance - total_distance) ** 2 / (2 * radius) + height_ep
    infl_x = (height_ep - height_sp) / (radius * total_distance) + total_distance
    return g_x if distance <= infl_x else h_x


def calculate_height_pans(distance, total_distance, height_pan, height_other):
    f_x = (distance - total_distance) ** 2 * (
        height_pan - height_other
    ) / total_distance**2 + height_other
    return f_x


def create_detail_component(point, height, family_symbol, doc, view):
    detail_component = doc.Create.NewFamilyInstance(point, family_symbol, view)
    detail_component.LookupParameter("Height").Set(height)
    detail_component.LookupParameter("HIGH").Set(0)
    detail_component.LookupParameter("LOW").Set(0)
    detail_component.LookupParameter("END").Set(0)
    return detail_component


def rotate_detail_component(detail_component, start_point, end_point, loc):
    direction = (start_point - end_point).Normalize()
    angle = DB.XYZ.BasisX.AngleTo(direction)
    if angle < 0:
        angle = angle % math.pi + math.pi
    elif angle > math.pi:
        angle = angle % math.pi - math.pi

    line = DB.Line.CreateBound(loc, loc + DB.XYZ(0, 0, 1))
    detail_component.Location.Rotate(line, angle)


def create_detail_component_at_point(loc, height, family_symbol, doc, view):
    height = float(height)
    height_rounded = str(int(round(height / 5) * 5))
    detail_component = create_detail_component(
        loc, height_rounded, family_symbol, doc, view
    )
    return detail_component


def create_components_between_points(
    start_point,
    start_height,
    end_point,
    end_height,
    family_symbol,
    doc,
    view,
    spacing=1000,
):
    distance_mm = round(start_point.DistanceTo(end_point) * 304.8, 0)
    num_points = max(1, int(round(distance_mm / spacing)))
    actual_cts = round(distance_mm / num_points, 0)
    location_diff = end_point - start_point

    with revit.Transaction("Create Detail Components"):
        for point in range(1, num_points):
            distance = point * actual_cts
            actual_height = calculate_height(
                distance, distance_mm, start_height, end_height
            )
            loc = start_point + location_diff * point / num_points
            height = actual_height - get_bottom_and_top_RL(loc)[0]
            detail_component = create_detail_component_at_point(
                loc,
                height,
                family_symbol,
                doc,
                view,
            )
            rotate_detail_component(detail_component, start_point, end_point, loc)


def find_farthest_point(points, start_point):
    return max(points, key=lambda point: start_point.DistanceTo(point))


def sort_objects_along_line(objects, start_point):
    def distance_from_start(obj):
        return start_point.DistanceTo(obj.Location.Point)

    return sorted(objects, key=distance_from_start)


def get_bottom_and_top_RL(point):
    outline = DB.Outline(
        DB.XYZ(point.X - 1, point.Y - 1, point.Z - 10000 / 304.8),
        DB.XYZ(point.X + 1, point.Y + 1, point.Z + 3000 / 304.8),
    )
    bbox_filter = DB.BoundingBoxIntersectsFilter(outline)

    floor_filter = DB.ElementCategoryFilter(
        DB.BuiltInCategory.OST_Floors
    )  # need to filter out non-concrete elements
    framing_filter = DB.ElementCategoryFilter(
        DB.BuiltInCategory.OST_StructuralFraming
    )  # need to filter out non-concrete elements

    CATEGORY_FILTER = DB.LogicalOrFilter(floor_filter, framing_filter)

    collector = DB.FilteredElementCollector(revit.doc, revit.doc.ActiveView.Id)
    collector.WherePasses(DB.LogicalAndFilter(CATEGORY_FILTER, bbox_filter))
    if collector.GetElementCount() == 0:
        return 999999.9, -999999.9
    else:
        transform = revit.doc.ActiveProjectLocation.GetTotalTransform().Inverse
        curve_ends = []

        for element in collector:
            geo_elem = element.get_Geometry(DB.Options())
            for geo_obj in geo_elem:
                if isinstance(geo_obj, DB.Solid):
                    line = DB.Line.CreateBound(
                        point, point + DB.XYZ.BasisZ * -10000 / 304.8
                    )
                    intersect_options = DB.SolidCurveIntersectionOptions()
                    intersect_result = geo_obj.IntersectWithCurve(line, intersect_options)

                    for i in range(intersect_result.SegmentCount):
                        curve_segment = intersect_result.GetCurveSegment(i)
                        curve_ends.append(transform.OfPoint(curve_segment.GetEndPoint(0)).Z)
                        curve_ends.append(transform.OfPoint(curve_segment.GetEndPoint(1)).Z)

        return min([min(curve_ends), 999999.9]) * 304.8, max(
            [max(curve_ends), -999999.9]
        ) * 304.8


def get_family_symbol(family_partial_name):
    collector = DB.FilteredElementCollector(DOC)
    collector.OfClass(DB.FamilySymbol)
    collector.OfCategory(DB.BuiltInCategory.OST_DetailComponents)

    name_provider = DB.ParameterValueProvider(
        DB.ElementId(DB.BuiltInParameter.ALL_MODEL_FAMILY_NAME)
    )
    name_rule = DB.FilterStringRule(
        name_provider, DB.FilterStringBeginsWith(), family_partial_name
    )
    name_filter = DB.ElementParameterFilter(name_rule)

    filtered_collector = collector.WherePasses(name_filter)
    return filtered_collector.FirstElement()


def get_actual_tendon_curve(component):
    start_offset_param = component.LookupParameter("Start Offset")
    end_offset_param = component.LookupParameter("End Offset")

    if start_offset_param and end_offset_param:
        start_offset = start_offset_param.AsDouble()
        end_offset = end_offset_param.AsDouble()

        location_curve = component.Location.Curve
        start_point = location_curve.GetEndPoint(0)
        start_point = DB.XYZ(start_point.X, start_point.Y, 0)
        end_point = location_curve.GetEndPoint(1)
        end_point = DB.XYZ(end_point.X, end_point.Y, 0)

        start_point = start_point.Add(location_curve.Direction.Multiply(start_offset))
        end_point = end_point.Add(location_curve.Direction.Multiply(-end_offset))

        new_curve = DB.Line.CreateBound(start_point, end_point)
        return new_curve


def get_location_and_rotation_of_height(component):
    location_3d = component.Location.Point
    location_2d = DB.XYZ(location_3d.X, location_3d.Y, 0)
    rotation = component.HandOrientation
    return location_2d, rotation


def angle_between_vectors(vector1, vector2):
    angle1 = abs(vector1.AngleTo(vector2))
    angle2 = abs(vector1.AngleTo(vector2.Negate()))
    return angle1 <= math.radians(ANGLETOLERANCE) or angle2 % math.pi <= math.radians(
        ANGLETOLERANCE
    )


def get_curves_and_points_within_tolerance(tendons, heights):
    result = []

    for tendon in tendons:
        tendon_curve = get_actual_tendon_curve(tendon)
        tendon_direction = tendon_curve.Direction
        height_points = []

        for height in list(heights):
            height_location, height_rotation = get_location_and_rotation_of_height(
                height
            )

            if tendon_curve.Distance(height_location) <= XYTOLERANCE:
                if angle_between_vectors(tendon_direction, height_rotation):
                    height_points.append(height)
                    heights.remove(height)

        if height_points:
            sorted_height_points = sort_objects_along_line(
                height_points, tendon_curve.GetEndPoint(0)
            )
            result.append((tendon, sorted_height_points))

    return result


def group_tendons(tendons):
    tendon_groups = []

    with forms.ProgressBar(title="Identifying Tendons") as pb:
        for idx, tendon in enumerate(tendons, start=1):
            found_group = False
            for group in tendon_groups:
                if (
                    tendon.points_string[0] == group[0].points_string[0]
                    or tendon.points_string[1] == group[0].points_string[0]
                ):
                    tendon.grouping = tendon_groups.index(group) + 1
                    group.append(tendon)
                    found_group = True
                    break
            if not found_group:
                tendon.grouping = len(tendon_groups) + 1
                tendon_groups.append([tendon])
            pb.update_progress(idx, len(tendons))
    return tendon_groups


def compare_lists_with_tolerance(listA, listB, tolerance=300):
    for itemA, itemB in zip(listA, listB):
        if abs(itemA - itemB) > tolerance / 2:
            return False
    return True


def renumber_all_tendons(selection):
    pt_tendons = [element for element in selection if TENDON_TYPE in element.Name]
    pt_heights = [element for element in selection if POINT_TYPE in element.Name]

    curves_and_points = get_curves_and_points_within_tolerance(pt_tendons, pt_heights)

    tendons = [
        Tendon(curve, sorted_height_points, str(tendon_number))
        for tendon_number, (curve, sorted_height_points) in enumerate(
            curves_and_points, start=1
        )
    ]

    tendon_group = group_tendons(tendons)
    return tendon_group


def create_all_intermediate_points(tendon_group):
    total = 0
    counter = 0

    for elem in tendon_group:
        for _ in elem:
            total += 1

    with forms.ProgressBar(title="Creating Intermediates") as pb:
        for group in tendon_group:
            for tendon in group:
                tendon.create_intermediate_points()
                counter += 1
                pb.update_progress(counter, total)


def create_tendon_heights(tendon):
    start_point = get_actual_tendon_curve(tendon).GetEndPoint(0)
    end_point = get_actual_tendon_curve(tendon).GetEndPoint(1)

    start_height = get_midheight_at_location(start_point)
    end_height = get_midheight_at_location(end_point)

    start_type = tendon.LookupParameter("Start").AsValueString()
    end_type = tendon.LookupParameter("End").AsValueString()

    if start_type == "Pan End":
        start_height = (start_height * 2) - 80
    elif end_type == "Pan End":
        end_height = (end_height * 2) - 80

    # Create tendon points at the ends
    start_height_point = create_detail_component_at_point(
        start_point,
        str(int(round(start_height / 5) * 5)),
        POINT_FAMILYSYMBOL,
        DOC,
        DOC.ActiveView
    )
    end_height_point = create_detail_component_at_point(
        end_point,
        str(int(round(end_height / 5) * 5)),
        POINT_FAMILYSYMBOL,
        DOC,
        DOC.ActiveView
    )
    start_height_point.LookupParameter("END").Set(1)
    end_height_point.LookupParameter("END").Set(1)
    return start_height_point, end_height_point


def print_tendons(tendon_group):
    for group_number, group in enumerate(tendon_group, start=1):
        for tendon in group:
            print("Tendon #{}: Group {}".format(tendon.mark, group_number))


def populate_family_symbols():
    global TENDON_FAMILYSYMBOL, POINT_FAMILYSYMBOL
    TENDON_FAMILYSYMBOL = get_family_symbol("PT Tendon")
    POINT_FAMILYSYMBOL = get_family_symbol("PT Height")
