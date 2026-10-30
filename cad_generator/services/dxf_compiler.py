import io
import ezdxf
from ..cad_blocks import install_blocks
from .geometry import render_geometry
from .validator import validate_layout

LAYERS = {'A-WALL-EXTR': (7, 50), 'A-WALL-INTR': (8, 35), 'A-DOOR': (1, 25), 'A-GLAZ': (4, 25), 'A-FURN': (3, 18), 'A-ANNO-TEXT': (2, 18), 'A-ANNO-DIMS': (6, 18)}


def compile_layout(layout):
    validate_layout(layout)
    geometry = render_geometry(layout)
    doc = ezdxf.new('R2010')
    doc.units = 6 if layout.unit == 'm' else 2
    doc.header['$MEASUREMENT'] = 1 if layout.unit == 'm' else 0
    doc.header['$LWDISPLAY'] = True
    for name, (color, weight) in LAYERS.items():
        doc.layers.new(name, dxfattribs={'color': color, 'lineweight': weight})
    install_blocks(doc)
    msp = doc.modelspace()
    for w in geometry['walls']:
        msp.add_line((w['x1'], w['y1']), (w['x2'], w['y2']), dxfattribs={'layer': w['layer']})
    for d in geometry['doors']:
        attrs = {'layer': 'A-DOOR'}
        msp.add_line(d['hinge'], d['leaf'], dxfattribs=attrs)
        msp.add_arc(d['hinge'], d['radius'], d['start_angle'], d['end_angle'], dxfattribs=attrs)
    for w in geometry['windows']:
        attrs = {'layer': 'A-GLAZ'}
        # Two parallel glazing rails plus the centerline (identical to preview).
        for rail in w['rails']:
            msp.add_line((rail[0], rail[1]), (rail[2], rail[3]), dxfattribs=attrs)
        msp.add_line((w['x1'], w['y1']), (w['x2'], w['y2']), dxfattribs=attrs)
    scale = 1 if layout.unit == 'm' else 3.280839895
    for r in layout.rooms:
        msp.add_text(r.name, height=.2*scale, dxfattribs={'layer': 'A-ANNO-TEXT'}).set_placement((r.x+.1*scale, r.y+r.depth/2))
        dims = f'{r.width} x {r.depth} {layout.unit}'
        msp.add_text(dims, height=.15*scale, dxfattribs={'layer': 'A-ANNO-TEXT'}).set_placement((r.x+.1*scale, r.y+r.depth/2-.3*scale))
    for f in layout.furniture:
        msp.add_blockref('FURN_' + f.type.upper(), (f.x, f.y), dxfattribs={'layer': 'A-FURN', 'xscale': f.width, 'yscale': f.depth, 'rotation': f.rotation})
    for a, b in [((0, 0), (layout.lot.width, 0)), ((layout.lot.width, 0), (layout.lot.width, layout.lot.depth))]:
        dim = msp.add_aligned_dim(a, b, distance=-.8*scale, override={'dimtxt': .18*scale, 'dimasz': .15*scale, 'dimdec': 2}, dxfattribs={'layer': 'A-ANNO-DIMS'})
        dim.render()
    stream = io.StringIO()
    doc.write(stream)
    # R2010 supports Unicode; escape non-ASCII text for portable ASCII downloads.
    text = ''.join(c if ord(c) < 128 else ''.join('\\U+%04X' % int.from_bytes(c.encode('utf-16-be')[i:i+2], 'big') for i in range(0, len(c.encode('utf-16-be')), 2)) for c in stream.getvalue())
    return {'layout': layout.model_dump(), 'dxf_content': text, 'render_geometry': geometry}
