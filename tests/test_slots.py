from smartcity.slots import AIMManager, LightManager, SlotManager, movements_compatible


def test_opposite_throughs_compatible():
    assert movements_compatible("0T", "2T")
    assert not movements_compatible("0T", "1T")
    assert movements_compatible("0R", "1R")


def test_fair_conflicting_streams_separated_by_t2():
    mgr = SlotManager("fair", batch=False)
    t_a = mgr.request(1, "0T", 10.0, now=10.0)
    t_b = mgr.request(2, "1T", 10.0, now=10.0)
    assert t_a == 10.0
    assert t_b >= t_a + 2.47 - 1e-6


def test_fair_same_stream_uses_follow_gap():
    mgr = SlotManager("fair", batch=False)
    t_a = mgr.request(1, "0T", 5.0, now=5.0)
    t_b = mgr.request(2, "0T", 5.0, now=5.0)
    assert t_b >= t_a + 1.0 - 1e-6
    assert t_b < t_a + 2.0


def test_batch_keeps_compatible_platoon_tight():
    mgr = SlotManager("batch", batch=True, batch_n=6, batch_delay_trigger_s=0.0)
    times = [mgr.request(i, "0T", 0.0, now=0.0) for i in range(4)]
    gaps = [times[i + 1] - times[i] for i in range(3)]
    assert all(g <= 1.25 for g in gaps)


def test_lights_hold_cross_street():
    lights = LightManager(cycle=64, green=26, yellow=3, allred=2)
    t_ns = lights.request(1, "1T", 0.0, now=0.0)
    t_ew = lights.request(2, "0T", 0.0, now=0.0)
    assert t_ns == 0.0
    assert t_ew >= 31.0


def test_aim_rejects_overlapping_tiles():
    aim = AIMManager(grid=8)
    t1 = aim.request(1, "0T", 0.0, now=0.0)
    t2 = aim.request(2, "1T", 0.0, now=0.0)
    assert t2 > t1
