from collections import Counter, defaultdict
from collections.abc import Callable

import pytest

from valheim_statistics.algorithms import (
    first_interval,
    first_interval_optimized,
    possible_arrival_states,
)


def test_arrival_states():
    # fmt: off
    expected = [
        1, 
        1,  2, 
        1,  2,  3, 
        1,  2,  3,  4, 
        1,  2,  3,  4,  5, 
        1,  2,  3,  4,  5,  6, 
        1,  2,  3,  4,  5,  6,  7, 
        1,  2,  3,  4,  5,  6,  7,  8, 
        1,  2,  3,  4,  5,  6,  7,  8,  9, 
        1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 
        1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 
        1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 
        1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 
        1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 
        1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 
        1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 
        1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 
        1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 
        1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
    ]
    # fmt: on

    assert Counter(expected) == Counter(possible_arrival_states(0.1))


def _sample_interval_function(fn: Callable[[], int], trials: int = 1000000):
    results: defaultdict[int, int] = defaultdict(lambda: 0)
    for i in range(trials):
        value = fn()
        results[value] += 1
    return {k: v for k, v in sorted(results.items())}


def _test_first_interval_function(fn: Callable[[float], int], chance=0.1):

    totals = _sample_interval_function(lambda: fn(chance))

    assert max(totals.keys()) == 19
    assert min(totals.keys()) == 1

    for i in range(19, 1, -1):
        actual = totals[i] / totals[1]
        expected = (20 - i) / 19
        assert actual == pytest.approx(expected, rel=0.03), (
            f"high variance in measured probability for {i=} {expected=} {actual=}\n"
            "this may just be an exceedingly unlikely event, try rerunning"
        )


@pytest.mark.flaky(reruns=1)
def test_first_interval_optimized():
    _test_first_interval_function(first_interval_optimized)


@pytest.mark.flaky(reruns=1)
def test_first_interval():
    _test_first_interval_function(first_interval)


@pytest.mark.flaky(reruns=1)
def test_interval_function_equivalency():
    a = _sample_interval_function(lambda: first_interval(0.1))
    b = _sample_interval_function(lambda: first_interval_optimized(0.1))

    for i in range(1, 19 + 1):
        assert a[i] == pytest.approx(b[i], rel=0.03)
