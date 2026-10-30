"""Shared deterministic wall extraction and Cartesian door convention."""
import math
from shapely.geometry import LineString, box
from shapely.ops import unary_union


def room_polygon(room):
    return box(room.x, room.y, room.x + room.width, room.y + room.depth)


def opening_line(o):
    return LineString([(o.x, o.y), (o.x + (o.width if o.orientation == 'horizontal' else 0), o.y + (o.width if o.orientation == 'vertical' else 0))])


def door_primitive(o):
    base = 0 if o.orientation == 'horizontal' else 90
    angle = base + (90 if o.swing == 'inward_left' else -90)
    return {'id': o.id, 'hinge': [o.x, o.y],
            'leaf': [round(o.x + o.width * math.cos(math.radians(angle)), 10), round(o.y + o.width * math.sin(math.radians(angle)), 10)],
            'radius': o.width, 'start_angle': min(base, angle) % 360,
            'end_angle': max(base, angle) % 360}


def window_primitive(o, sep):
    # Centerline endpoints.
    end = opening_line(o).coords[-1]
    x1, y1 = o.x, o.y
    x2, y2 = end[0], end[1]
    # Perpendicular unit offset of the centerline direction, scaled by half-separation.
    length = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    px, py = -uy * sep, ux * sep
    return {'id': o.id, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'rails': [[x1 + px, y1 + py, x2 + px, y2 + py],
                      [x1 - px, y1 - py, x2 - px, y2 - py]]}


def render_geometry(layout):
    boundary = box(0, 0, layout.lot.width, layout.lot.depth).boundary
    walls = unary_union([room_polygon(r).boundary for r in layout.rooms])
    cuts = unary_union([opening_line(o) for o in layout.openings])
    walls = walls.difference(cuts)
    segments = []
    for line in getattr(walls, 'geoms', [walls]):
        coords = list(line.coords)
        for a, b in zip(coords, coords[1:]):
            segment = LineString([a, b])
            exterior = boundary.covers(segment)
            segments.append({'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1], 'layer': 'A-WALL-EXTR' if exterior else 'A-WALL-INTR'})
    # Unit-aware half-separation between the two parallel glazing rails (model units).
    sep = 0.075 if layout.unit == 'm' else 0.25
    return {'walls': segments, 'doors': [door_primitive(o) for o in layout.openings if o.type == 'door'],
            'windows': [window_primitive(o, sep) for o in layout.openings if o.type == 'window']}
