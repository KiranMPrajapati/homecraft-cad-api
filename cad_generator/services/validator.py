"""Fail closed before rendering/export. Coordinates are in the declared unit."""
import math
from itertools import combinations
from shapely.geometry import box, Point
from shapely.affinity import rotate
from shapely.ops import unary_union
from .geometry import room_polygon, opening_line, door_primitive

EPS = 1e-8

class GeometryError(ValueError):
    pass


def validate_layout(layout):
    objects = [*layout.rooms, *layout.openings, *layout.furniture]
    if len({o.id for o in objects}) != len(objects):
        raise GeometryError('IDs must be globally unique.')
    lot = box(0, 0, layout.lot.width, layout.lot.depth)
    polygons = [room_polygon(r) for r in layout.rooms]
    if any(not lot.covers(p) for p in polygons):
        raise GeometryError('Rooms must remain inside the lot.')
    if any(a.intersection(b).area > EPS for a, b in combinations(polygons, 2)):
        raise GeometryError('Rooms must not overlap.')
    if lot.symmetric_difference(unary_union(polygons)).area > EPS:
        raise GeometryError('Rooms must fill the lot without gaps.')
    lines = [opening_line(o) for o in layout.openings]
    if any(a.intersects(b) for a, b in combinations(lines, 2)):
        raise GeometryError('Openings must not overlap or touch.')
    graph = {i: set() for i in range(len(polygons))}
    graph[-1] = set()
    swings = []
    for o, line in zip(layout.openings, lines):
        hosts = [i for i, p in enumerate(polygons) if p.boundary.covers(line)]
        exterior = lot.boundary.covers(line)
        if len(hosts) != (1 if exterior else 2):
            raise GeometryError('Each opening must lie wholly on one wall span, not across a junction.')
        if o.type == 'window':
            if not exterior or o.swing is not None:
                raise GeometryError('Windows must be exterior with null swing.')
            continue
        if o.swing is None:
            raise GeometryError('Doors require a swing direction.')
        a, b = (hosts[0], -1) if exterior else hosts
        graph[a].add(b); graph[b].add(a)
        d = door_primitive(o)
        end = line.coords[-1]
        # The quarter-circle extrema are exactly the closed/open endpoints.
        quadrant = box(min(o.x, end[0], d['leaf'][0]), min(o.y, end[1], d['leaf'][1]), max(o.x, end[0], d['leaf'][0]), max(o.y, end[1], d['leaf'][1]))
        if not any(polygons[i].buffer(EPS).covers(quadrant) for i in hosts):
            raise GeometryError('Door swing must fit entirely inside one host room.')
        # Circumscribed disk avoids false negatives between sampled arc vertices.
        disk = Point(o.x, o.y).buffer(o.width / math.cos(math.pi/256), quad_segs=64)
        swings.append((Point(o.x, o.y), o.width, quadrant, disk.intersection(quadrant)))
    visited, pending = {-1}, [-1]
    while pending:
        for nxt in graph[pending.pop()] - visited:
            visited.add(nxt); pending.append(nxt)
    if len(visited) != len(graph):
        raise GeometryError('Every room needs a door path to the exterior.')
    furniture = []
    for f in layout.furniture:
        p = rotate(box(f.x, f.y, f.x+f.width, f.y+f.depth), f.rotation, origin=(f.x, f.y))
        if not any(room.buffer(EPS).covers(p) for room in polygons):
            raise GeometryError('Rotated furniture must fit within a single room.')
        furniture.append(p)
    if any(a.intersection(b).area > EPS for a, b in combinations(furniture, 2)):
        raise GeometryError('Furniture must not overlap.')
    for hinge, radius, quadrant, _ in swings:
        for p in furniture:
            clipped = p.intersection(quadrant)
            if not clipped.is_empty and clipped.area > EPS and hinge.distance(clipped) < radius-EPS:
                raise GeometryError('Furniture obstructs a door swing.')
    if any(a[3].intersection(b[3]).area > EPS for a, b in combinations(swings, 2)):
        raise GeometryError('Door swings must not collide.')
    return layout
