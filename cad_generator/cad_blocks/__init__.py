"""Unit-square (0..1) recognizable symbols, scaled and rotated by INSERT.

One block per supported furniture type, named 'FURN_' + type.upper(),
with all entities drawn on layer '0' so INSERT styling is inherited.
"""

FURNITURE_TYPES = (
    'bed_king', 'bed_single', 'sofa', 'toilet', 'sink',
    'kitchen_counter', 'dining_table', 'wardrobe',
)


def install_blocks(doc):
    for name in FURNITURE_TYPES:
        b = doc.blocks.new('FURN_' + name.upper())
        attrs = {'layer': '0'}
        if name in ('bed_king', 'bed_single'):
            # Mattress outline + blanket fold line.
            b.add_lwpolyline([(0, 0), (1, 0), (1, 1), (0, 1)], close=True, dxfattribs=attrs)
            b.add_line((0, .7), (1, .7), dxfattribs=attrs)
            if name == 'bed_king':
                # Two pillows.
                for x in (.08, .54):
                    b.add_lwpolyline([(x, .76), (x + .38, .76), (x + .38, .94), (x, .94)], close=True, dxfattribs=attrs)
            else:
                # One wide pillow.
                b.add_lwpolyline([(.1, .76), (.9, .76), (.9, .94), (.1, .94)], close=True, dxfattribs=attrs)
        elif name == 'sofa':
            # Outer back+arms outline, inner seat, seat division line.
            b.add_lwpolyline([(0, 0), (1, 0), (1, 1), (0, 1)], close=True, dxfattribs=attrs)
            b.add_lwpolyline([(.15, .1), (.15, .8), (.85, .8), (.85, .1)], dxfattribs=attrs)
            b.add_line((.5, .1), (.5, .8), dxfattribs=attrs)
        elif name == 'toilet':
            # Tank rectangle + bowl ellipse.
            b.add_lwpolyline([(.2, .8), (.8, .8), (.8, 1), (.2, 1)], close=True, dxfattribs=attrs)
            b.add_ellipse((.5, .4), major_axis=(0, .35), ratio=.75, dxfattribs=attrs)
        elif name == 'sink':
            # Basin rounded rect (chamfered) + tap.
            b.add_lwpolyline(
                [(.15, .25), (.85, .25), (.95, .4), (.95, .8), (.05, .8), (.05, .4)],
                close=True, dxfattribs=attrs)
            b.add_line((.5, .8), (.5, .95), dxfattribs=attrs)
            b.add_circle((.5, .95), .04, dxfattribs=attrs)
        elif name == 'kitchen_counter':
            # Counter outline, sink basin rect, 4 burner ellipses.
            b.add_lwpolyline([(0, 0), (1, 0), (1, 1), (0, 1)], close=True, dxfattribs=attrs)
            b.add_lwpolyline([(.08, .55), (.42, .55), (.42, .92), (.08, .92)], close=True, dxfattribs=attrs)
            for x in (.6, .88):
                for y in (.25, .75):
                    b.add_ellipse((x, y), major_axis=(.09, 0), ratio=1, dxfattribs=attrs)
        elif name == 'dining_table':
            # Table outline + four chairs.
            b.add_lwpolyline([(.2, .25), (.8, .25), (.8, .75), (.2, .75)], close=True, dxfattribs=attrs)
            b.add_lwpolyline([(.3, .02), (.7, .02), (.7, .2), (.3, .2)], close=True, dxfattribs=attrs)
            b.add_lwpolyline([(.3, .8), (.7, .8), (.7, .98), (.3, .98)], close=True, dxfattribs=attrs)
            b.add_lwpolyline([(.02, .3), (.18, .3), (.18, .7), (.02, .7)], close=True, dxfattribs=attrs)
            b.add_lwpolyline([(.82, .3), (.98, .3), (.98, .7), (.82, .7)], close=True, dxfattribs=attrs)
        elif name == 'wardrobe':
            # Outline, two doors (center division), diagonal.
            b.add_lwpolyline([(0, 0), (1, 0), (1, 1), (0, 1)], close=True, dxfattribs=attrs)
            b.add_line((.5, 0), (.5, 1), dxfattribs=attrs)
            b.add_line((0, 0), (1, 1), dxfattribs=attrs)
