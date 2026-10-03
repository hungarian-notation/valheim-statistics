from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from functools import partial
from pathlib import Path

import plotly.graph_objects as go

from .algorithms import *


@dataclass
class DropSimulationResults:
    kills: int = 0
    drops: int = 0
    sessions: int = 0
    trials: int = 1

    @property
    def effective_chance(self) -> float:
        return self.drops / self.kills

    def __add__(self, other: DropSimulationResults) -> DropSimulationResults:
        if other == 0:
            return self
        if isinstance(other, DropSimulationResults):
            return DropSimulationResults(
                kills=self.kills + other.kills,
                drops=self.drops + other.drops,
                sessions=self.sessions + other.sessions,
                trials=self.trials + other.trials,
            )
        return NotImplemented

    def __radd__(self, other) -> DropSimulationResults:
        return self.__add__(other)


def simulate_drops(
    algorithm_factory: DropSimulatorFactory,
    total_drops: int | None = None,
    total_kills: int | None = None,
    session_kills: int | None = None,
) -> DropSimulationResults:
    algorithm = algorithm_factory()

    sim_kills = 0
    sim_drops = 0
    sim_sessionlength = 0
    sim_sessions = 1

    def halt_condition():
        return (total_kills is not None and sim_kills >= total_kills) or (
            total_drops is not None and sim_drops >= total_drops
        )

    while not halt_condition():
        if session_kills is not None and sim_sessionlength >= session_kills:
            algorithm.reset()
            sim_sessionlength = 0
            sim_sessions += 1
        result = algorithm.sample()
        sim_kills += 1
        sim_sessionlength += 1
        sim_drops += 1 if result else 0

    return DropSimulationResults(sim_kills, sim_drops, sim_sessions)


def _trials(trial_function: Callable[[], DropSimulationResults], trials: int):
    results = DropSimulationResults(0, 0, 0, 0)
    kills_table = defaultdict[int, int](lambda: 0)
    for i in range(trials):
        result = trial_function()
        results += result
        kills_table[result.kills] += 1
    return results, {k: kills_table[k] for k in range(max(kills_table) + 1)}


def at_most(data: Mapping[int, int], *, domain: Iterable[int] | None = None):

    if domain is None:
        xmax = max(data.keys())
        domain = range(xmax + 1)

    total = sum(data.values())
    return {x: sum(data[i] for i in range(x + 1) if i in data) / total for x in domain}


def at_least(data: Mapping[int, int]):
    xmax = max(data.keys())
    total = sum(data.values())
    return {
        x: sum(data[i] for i in range(x, xmax + 1) if i in data) / total
        for x in range(xmax + 1)
    }


def simulate_farming(
    algorithm_factory: DropSimulatorFactory,
    kills: int,
    trials: int,
    kps: int | None = None,
):
    data, _ = _trials(
        partial(
            simulate_drops,
            algorithm_factory=algorithm_factory,
            total_kills=kills,
            session_kills=kps,
        ),
        trials,
    )

    return data


def simulate_grinding(
    algorithm_factory: DropSimulatorFactory,
    trials: int = 1000,
    kps: int | None = None,
    collate: Callable[[Mapping[int, int]], Mapping[int, float]] = at_most,
):
    _, data = _trials(
        partial(
            simulate_drops,
            algorithm_factory=algorithm_factory,
            total_drops=1,
            session_kills=kps,
        ),
        trials,
    )
    return collate(data)


def _series_label(kps: int | None):
    if kps is None:
        return "Continuous"
    return f"{kps} kill{'s' if kps != 1 else ''}/restart"


_PLOT_DIR = Path("./plots")


def _plot_filename(name, plot_type):
    return str(_PLOT_DIR / f"{(name).lower().replace(' ', '_')}.{plot_type}.png")


def first_drop_plot(
    algo: DropChanceAlgorithm,
    name: str | None = None,
    chance=0.1,
    scale=1.5,
    seed: int | None = None,
):
    print(f"plotting (first) ({algo.name()})...")

    if seed is not None:
        random.seed(seed)
    if name is None:
        name = algo.name()

    maximum = 50  # max(*d1.keys(), *d_kps10.keys())
    domain = range(maximum + 1)
    trials = 200000

    nominal_series = {i: 1 - ((1 - chance) ** i) for i in domain}

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=list(domain),
            y=[nominal_series.get(x, None) for x in domain],
            name="Nominal (Pre 1.0)",
            zorder=100,
        )
    )

    figure.update_layout(
        title="Probability of first item drop occuring on or before a certain kill."
        "<br>"
        f"<i>chance: {chance}, algorithm: {algo.name()}</i>",
    )
    figure.update_xaxes(title=r"$\text{Kills } (k)$")
    figure.update_yaxes(title=r"$\operatorname{P} \left( k_{r} \leq k \right)$")

    for kps in (20, 10, 1):
        data = simulate_grinding(
            algo.simulator_factory(chance),
            trials=trials,
            kps=kps,
            collate=partial(at_most, domain=domain),
        )

        figure.add_trace(
            go.Scatter(
                x=list(domain),
                y=[data.get(x, None) for x in domain],
                name=_series_label(kps),
            )
        )

    figure.add_vline(
        17,
        line_dash="dash",
        line_color="#aaaaaa",
        annotation={
            "text": "$k=17$",
        },
        annotation_position="top left",
    )

    figure.update_layout(showlegend=True)
    # figure.show()
    figure.write_image(_plot_filename(algo.lower_name(), "first"), scale=scale)


def average_drop_plot(
    algo: DropChanceAlgorithm,
    name: str | None = None,
    chance=0.1,
    scale=1.5,
    seed: int | None = None,
):
    print(f"plotting (average) ({algo.name()})...")

    if seed is not None:
        random.seed(seed)
    if name is None:
        name = algo.name()

    trials = 5000
    domain = [1, 5, 10, 15, 20] + list(range(30, 210, 10))

    figure = go.Figure()
    figure.update_layout(
        title="Simulated average drops with respect to kill count."
        "<br>"
        f"<i>chance: {chance}, algorithm: {algo.name()}</i>",
    )

    figure.update_xaxes(title="Kills")
    figure.update_yaxes(title="Average Drops")

    figure.add_trace(
        go.Scatter(
            x=domain,
            y=[chance * x for x in domain],
            name="Nominal (Pre 1.0)",
            zorder=100,
        )
    )

    for kps in (None, 40, 20, 10, 1):
        figure.add_trace(
            go.Scatter(
                x=domain,
                y=[
                    result.drops / trials
                    for kills in domain
                    for result in (
                        simulate_farming(
                            algo.simulator_factory(chance),
                            kills=kills,
                            trials=trials,
                            kps=kps,
                        ),
                    )
                ],
                name=_series_label(kps),
            )
        )

    figure.update_layout(showlegend=True)
    # figure.show()
    figure.write_image(_plot_filename(algo.lower_name(), "average"), scale=scale)


if __name__ == "__main__":
    if not _PLOT_DIR.exists():
        _PLOT_DIR.mkdir(parents=True)

    # first_drop_plot(algo=PseudoDrop(), seed=42)
    # average_drop_plot(algo=PseudoDrop(), seed=42)
    # # average_drop_plot(algo=PseudoDropCorrectedInterval(), seed=42)
    # first_drop_plot(algo=PseudoDropRandomArrival(), seed=42)
    # average_drop_plot(algo=PseudoDropRandomArrival(), seed=42)
    first_drop_plot(algo=HybridPitySystem(), seed=42)
    average_drop_plot(algo=HybridPitySystem(), seed=42)
