import math as m
import random
from abc import ABC
from collections.abc import Callable
from functools import cache, partial
from typing import Protocol

from valheim_statistics.caseutil import pascal_to_snake, pascal_to_words

type DropSimulatorFactory = Callable[[], DropChanceSimulator]


class DropChanceAlgorithm(ABC):
    @classmethod
    def name(cls) -> str:
        return pascal_to_words(cls.__name__)

    @classmethod
    def lower_name(cls) -> str:
        return pascal_to_snake(cls.__name__)

    def simulator_factory(self, chance: float) -> DropSimulatorFactory: ...


class DropChanceSimulator(Protocol):
    def sample(self) -> bool: ...

    def reset(self) -> None:
        """
        Resets any internal state.
        """
        ...


class RandomDrop(DropChanceSimulator, DropChanceAlgorithm):
    def simulator_factory(self, chance: float) -> DropSimulatorFactory:
        return partial(self._Sim, chance=chance)

    class _Sim:
        def __init__(self, chance):
            self._chance = chance

        def sample(self):
            return random.random() < self._chance

        def reset(self):
            return


def randint_exclusive(inclusive_lower: int, exclusive_upper: int) -> int:
    """
    A variation on `random.randint` with an exclusive upper bound.

    Allows for PseudoDrop's implementation to more closely mirror the C#, as
    Unity's random integer function has an exclusive upper bound.
    """

    inclusive_upper = exclusive_upper - 1
    return random.randint(inclusive_lower, inclusive_upper)


class PseudoDrop(DropChanceAlgorithm):
    @classmethod
    def name(cls) -> str:
        return "Vanilla Pseudo Drop"

    def simulator_factory(self, chance: float) -> DropSimulatorFactory:
        return partial(self._Sim, chance=chance)

    class _Sim:
        def __init__(self, chance: float):
            self._chance: float = chance
            self._next: int | None = None

        def sample(self):
            if self._next is None:
                self._next = randint_exclusive(0, int(1 / self._chance * 2))
            else:
                self._next -= 1
            if self._next <= 0:
                self._next = randint_exclusive(0, int(1 / self._chance * 2 + 1))
                return True
            return False

        def reset(self):
            self._next = None


class PseudoDropCorrectedInterval(DropChanceAlgorithm):
    def simulator_factory(self, chance: float) -> DropSimulatorFactory:
        return partial(self._Sim, chance=chance)

    class _Sim:
        def __init__(self, chance: float):
            self._chance: float = chance
            self._next: int | None = None

        def sample(self):
            if self._next is None:
                self._next = randint_exclusive(1, int(1 / self._chance * 2))

            self._next -= 1

            if self._next <= 0:
                self._next = randint_exclusive(1, int(1 / self._chance * 2))
                return True
            return False

        def reset(self):
            self._next = None


class HybridPitySystem(DropChanceAlgorithm):
    def simulator_factory(self, chance: float) -> DropSimulatorFactory:
        return partial(self._Sim, chance=chance)

    class _Sim:
        def __init__(self, chance: float):
            self._chance: float = chance
            self._next: int | None = None

            self._samples: int = 0
            self._drops: int = 0

        def sample(self):
            drop = False

            if random.random() < self._chance:
                drop = True
            else:
                if self._next is None:
                    self._next = randint_exclusive(
                        int(1 / self._chance * 1), int(1 / self._chance * 2)
                    )
                self._next -= 1
                if self._next <= 0:
                    drop = True

            if drop:
                self._next = randint_exclusive(
                    int(1 / self._chance * 1), int(1 / self._chance * 2)
                )

            self._samples += 1
            self._drops += 1 if drop else 0

            return drop

        def reset(self):
            self._next = None


class PseudoDropRandomArrival(DropChanceAlgorithm):
    @classmethod
    def name(cls) -> str:
        return "Fixed Pseudo Drop"

    def simulator_factory(self, chance: float) -> DropSimulatorFactory:
        return partial(self._Sim, chance=chance)

    class _Sim:
        def __init__(self, chance: float):
            self._chance: float = chance
            self._next: int | None = None

        def sample(self):
            if self._next is None:
                self._next = first_interval(self._chance)

            self._next -= 1

            if self._next <= 0:
                self._next = subsequent_interval(self._chance)
                return True
            return False

        def reset(self):
            self._next = None


def subsequent_interval(chance) -> int:
    return randint_exclusive(1, int(1 / chance * 2))


@cache
def possible_arrival_states(chance):
    """
    Generates all possible arrival states for a given drop chance.
    """
    bound = int(1 / chance * 2) - 1
    return tuple(j for i in range(1, bound + 1) for j in range(1, i + 1))


def first_interval(chance):
    possible_states = possible_arrival_states(chance)
    return random.choice(possible_states)


def first_interval_optimized(chance) -> int:
    """
    This is a statistically equivalent implementation of
    `first_interval` that does not require a cached lookup table for
    every drop chance.
    """

    bound = int(1 / chance * 2) - 1
    total_weight = (bound * (bound + 1)) // 2
    random_sample = random.randint(1, total_weight)
    discriminant = (2 * bound + 1) ** 2 - 8 * random_sample
    real_interval = ((2 * bound + 1) - m.sqrt(discriminant)) / 2
    return m.ceil(real_interval)
