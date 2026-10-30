import copy
import pytest
from test_pipeline import fixture
from cad_generator.schema import Layout
from cad_generator.services.validator import GeometryError, validate_layout

@pytest.mark.parametrize('case', ['overlap','outside','duplicate','floating','disconnected','opening_overlap','wrong_swing','furniture_outside','furniture_collision','swing_collision','internal_window','door_crosses_junction'])
def test_reject_bad_geometry(case):
    d = fixture()
    if case == 'overlap': d['rooms'][1]['x'] = 4
    if case == 'outside': d['rooms'][1]['x'] = 6
    if case == 'duplicate': d['furniture'][0]['id'] = 'entry'
    if case == 'floating': d['openings'][0]['y'] = 2
    if case == 'disconnected': d['openings'].pop(1)
    if case == 'opening_overlap':
        o = copy.deepcopy(d['openings'][0]); o['id'] = 'extra'; d['openings'].append(o)
    if case == 'wrong_swing': d['openings'][0]['swing'] = 'inward_right'
    if case == 'furniture_outside': d['furniture'][0]['rotation'] = 180
    if case == 'furniture_collision':
        f = copy.deepcopy(d['furniture'][0]); f['id'] = 'extra'; d['furniture'].append(f)
    if case == 'swing_collision': d['furniture'][0].update(x=1.2,y=.1,width=.2,depth=.2)
    if case == 'internal_window': d['openings'][1].update(type='window',swing=None)
    if case == 'door_crosses_junction': d['openings'][0].update(x=4.5,width=1)
    with pytest.raises(GeometryError): validate_layout(Layout.model_validate(d))

@pytest.mark.parametrize('value', [float('nan'),float('inf'),-1,1001,True,'10'])
def test_schema_rejects_unbounded_numbers(value):
    d=fixture(); d['lot']['width']=value
    with pytest.raises(ValueError): Layout.model_validate(d)


def test_colliding_door_swings_are_rejected():
    d=fixture()
    d['openings'].append({'id':'entry2','type':'door','x':0,'y':.2,'width':1.5,'orientation':'vertical','swing':'inward_right'})
    with pytest.raises(GeometryError, match='swings'): validate_layout(Layout.model_validate(d))


@pytest.mark.parametrize('orientation,swing,leaf,angles', [
    ('horizontal','inward_left',[3,5],(0,90)),
    ('horizontal','inward_right',[3,1],(270,0)),
    ('vertical','inward_left',[1,3],(90,180)),
    ('vertical','inward_right',[5,3],(0,90))])
def test_door_conventions(orientation,swing,leaf,angles):
    from cad_generator.schema import Opening
    from cad_generator.services.geometry import door_primitive
    door=door_primitive(Opening(id='d',type='door',x=3,y=3,width=2,orientation=orientation,swing=swing))
    assert door['leaf']==leaf
    assert (door['start_angle'],door['end_angle'])==angles


def test_imperial_rotated_valid_furniture_roundtrip():
    import io, ezdxf
    from cad_generator.services.dxf_compiler import compile_layout
    d=fixture(); d['unit']='ft'; d['furniture'][0].update(x=8,y=4,rotation=90)
    doc=ezdxf.read(io.StringIO(compile_layout(Layout.model_validate(d))['dxf_content']))
    assert doc.units == 2
    assert not doc.audit().has_errors
