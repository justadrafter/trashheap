import math
from pyrevit import revit, DB
from pyrevit.revit import query

def get_height_and_location(detail_item):
    elem_location = detail_item.Location.Point
    height_param = round(float(detail_item.LookupParameter("Height").AsValueString()), 0) + get_lowest_element_at_point(detail_item.Location.Point)
    return height_param, elem_location


def calculate_height(distance, total_distance, height_sp, height_ep, radius=-5000):
    if height_ep - height_sp != 0:
        g_x = distance**2 / (2 * radius + total_distance**2 / (height_ep - height_sp)) + height_sp
    else:
        g_x = height_sp
    h_x = (distance - total_distance)**2 / (2 * radius) + height_ep
    infl_x = (height_ep - height_sp) / (radius * total_distance) + total_distance
    return g_x if distance <= infl_x else h_x


def create_detail_component(point, height, family_name, symbol_name, doc, view):
    family_symbol = query.get_family_symbol(family_name, symbol_name, doc)[0]
    
    if not family_symbol:
        print("Family symbol not found.")
        return None
    
    detail_component = doc.Create.NewFamilyInstance(point, family_symbol, view)
    detail_component.LookupParameter("Height").Set(height)
    detail_component.LookupParameter("HIGH").Set(0)
    detail_component.LookupParameter("LOW").Set(0)
    detail_component.LookupParameter("END").Set(0)
    return detail_component


def rotate_detail_component(detail_component, start_point, end_point, loc, adjust_rotation=False):
    direction = (end_point - start_point).Normalize()
    angle = DB.XYZ.BasisX.AngleTo(direction)

    if adjust_rotation and not (math.pi < angle <= 2 * math.pi):
        angle += math.pi

    line = DB.Line.CreateBound(loc, loc + DB.XYZ(0, 0, 1))
    detail_component.Location.Rotate(line, angle)


def create_components_between_points(start_point, start_height, end_point, end_height, family_name, symbol_name, doc, view, spacing=1000):
    distance_mm = round(start_point.DistanceTo(end_point) * 304.8, 0)
    num_points = max(1, int(round(distance_mm / spacing)))
    actual_cts = round(distance_mm / num_points, 0)
    location_diff = end_point - start_point

    with revit.Transaction("Create Detail Components"):
        for point in xrange(1, num_points):
            distance = point * actual_cts
            actual_height = calculate_height(distance, distance_mm, start_height, end_height)
            loc = start_point + location_diff * point / num_points
            height = actual_height - get_lowest_element_at_point(loc)
            detail_component = create_detail_component(loc, str(int(round(height / 5) * 5)), family_name, symbol_name, doc, view)
            rotate_detail_component(detail_component, start_point, end_point, loc)


def find_farthest_point(points, start_point):
    return max(points, key=lambda point: start_point.DistanceTo(point))


def sort_objects_along_line(objects, start_point):
    def distance_from_start(obj):
        return start_point.DistanceTo(obj.Location.Point)
    return sorted(objects, key=distance_from_start)


def get_lowest_element_at_point(point):
    outline = DB.Outline(DB.XYZ(point.X-1, point.Y-1, point.Z-10000/304.8), DB.XYZ(point.X+1, point.Y+1, point.Z+5000/304.8))
    bbox_filter = DB.BoundingBoxIntersectsFilter(outline)

    floor_filter = DB.ElementCategoryFilter(DB.BuiltInCategory.OST_Floors)
    framing_filter = DB.ElementCategoryFilter(DB.BuiltInCategory.OST_StructuralFraming)
    category_filter = DB.LogicalOrFilter(floor_filter, framing_filter)

    collector = DB.FilteredElementCollector(revit.doc, revit.doc.ActiveView.Id)
    collector.WherePasses(DB.LogicalAndFilter(category_filter, bbox_filter))

    lowest_elevation = float("inf")

    transform = revit.doc.ActiveProjectLocation.GetTotalTransform().Inverse
  
    for element in collector:
        geo_elem = element.get_Geometry(DB.Options())
        for geo_obj in geo_elem:
            if isinstance(geo_obj, DB.Solid):
                line = DB.Line.CreateBound(point, point + DB.XYZ.BasisZ * -10000*304.8)
                intersect_options = DB.SolidCurveIntersectionOptions()
                intersect_result = geo_obj.IntersectWithCurve(line, intersect_options)
                for i in range(intersect_result.SegmentCount):
                    curve_segment = intersect_result.GetCurveSegment(i)
                    end_point = curve_segment.GetEndPoint(1)
                    transformed_z = transform.OfPoint(end_point).Z
                    if transformed_z < lowest_elevation:
                        lowest_elevation = transformed_z*304.8

    return lowest_elevation