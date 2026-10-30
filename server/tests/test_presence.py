from ztmc_server.presence import PresenceConfig, PresenceTracker

CFG = PresenceConfig(face_on_ms=300, face_off_ms=1500, min_score=0.6, device_timeout_ms=3000)


def feed(t: PresenceTracker, face: bool, start: float, end: float, step: float = 100, score: float = 0.9):
    """start~end(ms) 동안 step 간격으로 detect를 넣고, 바뀐 상태들을 돌려준다."""
    changes = []
    now = start
    while now <= end:
        changes += [(now, c) for c in t.on_detect(face, score, now)]
        changes += [(now, c) for c in t.tick(now)]
        now += step
    return changes


def test_starts_no_device_and_first_detect_goes_absent_not_present():
    t = PresenceTracker(CFG, now=0)
    assert t.state == "no_device"
    assert t.on_detect(True, 0.9, 0) == ["absent"]
    assert t.state == "absent"


def test_present_only_after_face_on_ms():
    t = PresenceTracker(CFG, now=0)
    changes = feed(t, True, 0, 500)
    assert [c for _, c in changes] == ["absent", "present"]
    assert changes[-1][0] == 300


def test_short_look_away_does_not_pause():
    t = PresenceTracker(CFG, now=0)
    feed(t, True, 0, 1000)
    assert t.state == "present"
    changes = feed(t, False, 1100, 2000)  # 0.9초만 안 보임
    assert changes == []
    feed(t, True, 2100, 2500)
    assert t.state == "present"


def test_absent_after_face_off_ms():
    t = PresenceTracker(CFG, now=0)
    feed(t, True, 0, 1000)
    changes = feed(t, False, 1100, 3000)
    assert changes == [(2600, "absent")]


def test_flicker_never_reaches_present():
    t = PresenceTracker(CFG, now=0)
    now = 0
    for i in range(30):  # 100ms마다 얼굴 있음/없음이 번갈아 나옴
        t.on_detect(i % 2 == 0, 0.9, now)
        t.tick(now)
        now += 100
    assert t.state == "absent"


def test_low_score_counts_as_no_face():
    t = PresenceTracker(CFG, now=0)
    feed(t, True, 0, 1000, score=0.5)
    assert t.state == "absent"


def test_offline_status_goes_no_device_immediately():
    t = PresenceTracker(CFG, now=0)
    feed(t, True, 0, 1000)
    assert t.on_status("offline", 1050) == ["no_device"]
    assert t.on_status("online", 1100) == []
    assert t.state == "no_device"


def test_device_timeout_without_detect():
    t = PresenceTracker(CFG, now=0)
    feed(t, True, 0, 1000)
    assert t.tick(3999) == []
    assert t.tick(4000) == ["no_device"]
    assert t.tick(9000) == []  # no_device에서 더 바뀌지 않음


def test_recover_from_no_device_requires_face_on_ms_again():
    t = PresenceTracker(CFG, now=0)
    feed(t, True, 0, 1000)
    t.on_status("offline", 1100)
    changes = feed(t, True, 2000, 2400)
    assert [c for _, c in changes] == ["absent", "present"]
    assert changes[-1][0] == 2300


def test_face_on_zero_reports_both_steps_in_order():
    t = PresenceTracker(PresenceConfig(face_on_ms=0), now=0)
    assert t.on_detect(True, 0.9, 0) == ["absent", "present"]
