from dataclasses import FrozenInstanceError

import pytest
from shapely.geometry import box


def test_immutable_geometry_revision_roundtrip():
    from parametric_deco.model import PartDefinition, canonical

    a = PartDefinition.from_polygon("rib", box(0, 0, 100, 40), 6)
    b = PartDefinition.from_polygon("rib", box(0, 0, 100, 40), 6)
    c = PartDefinition.from_polygon("rib", box(0, 0, 101, 40), 6)
    assert a.fingerprint == b.fingerprint
    assert a.revision != c.revision
    assert PartDefinition.from_dict(a.to_dict()) == a
    assert canonical(a.to_dict()) == canonical(b.to_dict())
    with pytest.raises(FrozenInstanceError):
        a.thickness_mm = 7


def test_rejects_bad_transform_and_stale_fingerprint():
    from parametric_deco.model import PartDefinition, PartInstance

    d = PartDefinition.from_polygon("rib", box(0, 0, 100, 40), 6).to_dict()
    d["thickness_mm"] = 7
    with pytest.raises(ValueError, match="fingerprint"):
        PartDefinition.from_dict(d)
    with pytest.raises(ValueError, match="rigid"):
        PartInstance("bad", "rib", "r1", ((2, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
