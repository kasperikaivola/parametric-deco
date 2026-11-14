"""Coupled parameter regressions through complete manufacturing validation."""
import pytest
from parametric_deco.assembly import assemble
from parametric_deco.config import config_from_dict


@pytest.mark.parametrize('scale,reach,width',[(0.9,0.85,0.9),(0.9,0.9,1.0)])
def test_small_six_limb_creature_keeps_mounting_bores_clear_of_blade_seats(scale,reach,width):
    build = assemble(config_from_dict({'style':'layered-creature','parameters':{
        'limb_count':6,'ribs_per_limb':4,'scale':scale,'limb_reach':reach,'limb_width':width}}))
    assert build.report.digital_valid,build.report.to_dict()


@pytest.mark.parametrize('data',[
    {'parameters':{'focal_count':9,'branching':3,'complexity':2},
     'envelope':{'width_mm':800,'height_mm':800,'depth_mm':120}},
    {'parameters':{'arrangement':'bilateral','symmetry':'bilateral','focal_count':4}},
    {'style':'radial-weave','parameters':{'radius_mm':250,'amplitude_mm':50,'opening_radius_mm':140}},
    {'style':'rib-study','parameters':{'recipe':{'stations_mm':[55,130,285]}}},
])
def test_coupled_parameter_builds(data):
    build = assemble(config_from_dict(data))
    assert build.report.digital_valid,build.report.to_dict()
