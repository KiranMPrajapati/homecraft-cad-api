import json
from pathlib import Path

import pytest


def fixture():
    return json.loads((Path(__file__).parent / 'fixtures/valid_layout.json').read_text())


def test_valid_layout_compiles_unique_cut_walls_and_audited_dxf():
    from cad_generator.schema import Layout
    from cad_generator.services.validator import validate_layout
    from cad_generator.services.dxf_compiler import compile_layout
    import ezdxf
    import io
    layout = Layout.model_validate(fixture())
    validate_layout(layout)
    result = compile_layout(layout)
    doc = ezdxf.read(io.StringIO(result['dxf_content']))
    assert doc.dxfversion == 'AC1024'
    assert not doc.audit().has_errors
    assert doc.header['$INSUNITS'] == 6
    from cad_generator.services.dxf_compiler import LAYERS
    for name, (color, weight) in LAYERS.items():
        assert doc.layers.get(name).dxf.color == color
        assert doc.layers.get(name).dxf.lineweight == weight
    assert all(ord(c) < 128 for c in result['dxf_content'])
    assert len(list(doc.modelspace().query('INSERT'))) == 1
    assert len(list(doc.modelspace().query('DIMENSION'))) >= 2
    walls = result['render_geometry']['walls']
    assert len({tuple(w.values()) for w in walls}) == len(walls)
    assert sum(abs(w['x2']-w['x1'])+abs(w['y2']-w['y1']) for w in walls) == 40.5
    assert result['render_geometry']['doors'][0]['leaf'] == [1.0, 1.0]


def test_windows_are_double_lines_in_preview_and_dxf():
    from cad_generator.schema import Layout
    from cad_generator.services.geometry import render_geometry
    from cad_generator.services.dxf_compiler import compile_layout
    import ezdxf
    import io
    layout = Layout.model_validate(fixture())
    geometry = render_geometry(layout)
    windows = geometry['windows']
    assert windows
    for w in windows:
        # Centerline + two parallel rails offset by the unit-aware half-separation.
        assert set(w) == {'id', 'x1', 'y1', 'x2', 'y2', 'rails'}
        assert len(w['rails']) == 2
        for rail in w['rails']:
            assert len(rail) == 4
        # Metre layout half-separation is 0.075; horizontal window => y offset.
        (ax, ay, bx, by), (cx, cy, dx, dy) = w['rails']
        assert abs(ay - w['y1']) == pytest.approx(0.075)
        assert abs(cy - w['y1']) == pytest.approx(0.075)
        assert ay != cy
    result = compile_layout(layout)
    doc = ezdxf.read(io.StringIO(result['dxf_content']))
    glaz = list(doc.modelspace().query('LINE[layer=="A-GLAZ"]'))
    assert len(glaz) >= len(windows) * 3


def test_per_room_dimension_text_exists_for_every_room():
    from cad_generator.schema import Layout
    from cad_generator.services.dxf_compiler import compile_layout
    import ezdxf
    import io
    layout = Layout.model_validate(fixture())
    result = compile_layout(layout)
    doc = ezdxf.read(io.StringIO(result['dxf_content']))
    texts = [t.dxf.text for t in doc.modelspace().query('TEXT[layer=="A-ANNO-TEXT"]')]
    # Name + dimensions per room.
    assert len(texts) >= 2 * len(layout.rooms)
    for r in layout.rooms:
        assert f'{r.width} x {r.depth} {layout.unit}' in texts
