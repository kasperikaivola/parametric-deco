from parametric_deco.config import RibStudy
import pytest


def test_slot_fit_and_coupon_range():
    from parametric_deco.config import DesignConfig
    from parametric_deco.geometry.joints import slot_width, fit_coupon

    c = DesignConfig(style="rib-study", parameters=RibStudy())
    assert slot_width(c) == pytest.approx(6.2)
    coupon = fit_coupon(c)
    assert len(coupon.interfaces) == 5
    assert [s.slot_width_mm for s in coupon.interfaces] == pytest.approx([6, 6.1, 6.2, 6.3, 6.4])
