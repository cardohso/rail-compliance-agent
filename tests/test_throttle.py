from rail_compliance.throttle import Throttle


class Clock:
    def __init__(self):
        self.now = 1000.0
        self.slept = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def make(per_minute):
    clock = Clock()
    return Throttle(per_minute, clock=clock.time, sleep=clock.sleep), clock


def test_calls_under_the_limit_do_not_wait():
    throttle, clock = make(3)
    for _ in range(3):
        throttle.wait()
    assert clock.slept == []


def test_the_call_over_the_limit_waits_until_a_minute_after_the_oldest():
    throttle, clock = make(3)
    throttle.wait()  # t=1000
    clock.now += 10
    throttle.wait()  # t=1010
    throttle.wait()  # t=1010
    throttle.wait()  # must wait until 1000 + 60
    assert round(sum(clock.slept), 3) == 50.0
    assert clock.now == 1060.0


def test_the_window_slides():
    throttle, clock = make(2)
    throttle.wait()
    throttle.wait()
    clock.now += 61
    throttle.wait()  # the first two have aged out
    assert clock.slept == []


def test_zero_means_unlimited():
    throttle, clock = make(0)
    for _ in range(100):
        throttle.wait()
    assert clock.slept == []


def test_a_sustained_stream_stays_under_the_limit_in_every_window():
    throttle, clock = make(5)
    stamps = []
    for _ in range(40):
        throttle.wait()
        stamps.append(clock.now)
    for i, t in enumerate(stamps):
        in_window = [s for s in stamps[: i + 1] if t - s < 60]
        assert len(in_window) <= 5
