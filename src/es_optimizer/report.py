from itertools import chain

from rich.style import Style
from rich.table import Table
from rich.text import Text

from es_optimizer.database.models import Outfit, Ship, Weapon
from es_optimizer.optimizer import FPS, SolutionResult


def _format_delta(delta: float, fmt: str, lower_is_better: bool = False) -> Text:
    if delta == 0:
        return Text("·", style=Style(color="grey50"))
    sign = "+" if delta > 0 else ""
    improved = (delta < 0) if lower_is_better else (delta > 0)
    color = "green" if improved else "red"
    return Text(sign + fmt.format(delta), style=Style(color=color))


def _add_comparison_row(
    table: Table,
    label: str,
    values: list[float],
    fmt: str = "{:,.3f}",
    lower_is_better: bool = False,
) -> None:
    """Add a row showing each value formatted, plus a delta (last - first) cell."""
    cells: list[str | Text] = [label, *(fmt.format(v) for v in values)]
    delta = values[-1] - values[0] if len(values) >= 2 else 0
    cells.append(_format_delta(delta, fmt, lower_is_better))
    table.add_row(*cells)


def _solution_columns(solutions: dict[str, SolutionResult]) -> list[str]:
    return list(solutions.keys())


def get_shopping_list_table(solutions: dict[str, SolutionResult]) -> Table:
    labels = _solution_columns(solutions)
    table = Table("Outfit", "Category", *labels, "Δ", title="Shopping list")

    # Collect every outfit/weapon mentioned in any solution.
    seen: dict[Outfit | Weapon, dict[str, int]] = {}
    for label, sol in solutions.items():
        for item, count in chain(sol.weapons.items(), sol.outfits.items()):
            seen.setdefault(item, {})[label] = count

    items_sorted = sorted(
        seen.items(), key=lambda kv: (kv[0].category.value, kv[0].name)
    )

    totals = {label: 0.0 for label in labels}
    for item, counts in items_sorted:
        per_label = [counts.get(label, 0) for label in labels]
        for label, c in zip(labels, per_label):
            totals[label] += item.cost * c
        count_cells: list[str | Text] = [
            f"{c:.0f}" if c else Text("—", style=Style(color="grey50"))
            for c in per_label
        ]
        delta = per_label[-1] - per_label[0] if len(per_label) >= 2 else 0
        delta_cell = _format_delta(delta, "{:.0f}")
        table.add_row(item.name, item.category.value, *count_cells, delta_cell)

    total_cells = [
        Text(f"{totals[label]:,.0f}", style=Style(color="cyan")) for label in labels
    ]
    cost_delta = totals[labels[-1]] - totals[labels[0]] if len(labels) >= 2 else 0
    table.add_row(
        Text("Total cost", style=Style(bold=True), justify="right"),
        "",
        *total_cells,
        _format_delta(cost_delta, "{:,.0f}", lower_is_better=True),
    )
    return table


def _movement_stats(solution: SolutionResult, ship: Ship) -> dict[str, float]:
    thrust = 0.0
    turn = 0.0
    mass = ship.mass
    for outfit, count in chain(solution.outfits.items(), solution.weapons.items()):
        if isinstance(outfit, Outfit):
            thrust += outfit.thrust * count
            turn += outfit.turn * count
        mass += outfit.mass * count

    max_speed = thrust / ship.drag * FPS if ship.drag else 0
    acceleration = thrust / mass * FPS**2 if mass else 0
    turning = turn / mass * FPS if mass else 0
    return {
        "mass": mass,
        "max_speed": max_speed,
        "acceleration": acceleration,
        "turning": turning,
        "time_to_full_speed": max_speed / acceleration if acceleration else 0,
        "time_to_360": 360 / turning if turning else 0,
    }


def get_movement_table(solutions: dict[str, SolutionResult], ship: Ship) -> Table:
    labels = _solution_columns(solutions)
    table = Table("metric", *labels, "Δ", title="Movement")

    stats = {label: _movement_stats(sol, ship) for label, sol in solutions.items()}

    def row(metric: str, fmt: str, lower_is_better: bool = False) -> None:
        _add_comparison_row(
            table,
            metric,
            [stats[label][metric] for label in labels],
            fmt,
            lower_is_better,
        )

    row("mass", "{:,.0f}", lower_is_better=True)
    row("max_speed", "{:,.3f}")
    row("acceleration", "{:,.5f}")
    row("turning", "{:,.5f}")
    table.add_row()
    row("time_to_full_speed", "{:,.5f}", lower_is_better=True)
    row("time_to_360", "{:,.5f}", lower_is_better=True)

    return table


def get_dps_table(solutions: dict[str, SolutionResult]) -> Table:
    labels = _solution_columns(solutions)
    table = Table("metric", *labels, "Δ", title="DPS")

    def shield_dps(sol: SolutionResult) -> float:
        return sum(w.shield_damage * c * FPS for w, c in sol.weapons.items())

    def hull_dps(sol: SolutionResult) -> float:
        return sum(w.hull_damage * c * FPS for w, c in sol.weapons.items())

    _add_comparison_row(
        table, "Shield", [shield_dps(solutions[label]) for label in labels], "{:,.0f}"
    )
    _add_comparison_row(
        table, "Hull", [hull_dps(solutions[label]) for label in labels], "{:,.0f}"
    )
    return table


def _capacity_used(solution: SolutionResult) -> dict[str, float]:
    outfit_space = 0.0
    weapon_capacity = 0.0
    gun_ports = 0.0
    turret_mounts = 0.0
    engine_capacity = 0.0

    for item, count in chain(solution.outfits.items(), solution.weapons.items()):
        outfit_space -= item.outfit_space * count
        weapon_capacity -= item.weapon_capacity * count
        if isinstance(item, Outfit):
            engine_capacity -= item.engine_capacity * count
        if isinstance(item, Weapon):
            gun_ports -= item.gun_ports * count
            turret_mounts -= item.turret_mounts * count

    return {
        "outfit_space": outfit_space,
        "weapon_capacity": weapon_capacity,
        "gun_ports": gun_ports,
        "turret_mounts": turret_mounts,
        "engine_capacity": engine_capacity,
    }


def get_capacity_table(solutions: dict[str, SolutionResult], ship: Ship) -> Table:
    labels = _solution_columns(solutions)
    table = Table("metric", *labels, "Δ", "Max", title="Capacity (used)")

    used = {label: _capacity_used(sol) for label, sol in solutions.items()}
    maxima = {
        "outfit_space": ship.outfit_space,
        "weapon_capacity": ship.weapon_capacity,
        "gun_ports": ship.gun_ports,
        "turret_mounts": ship.turret_mounts,
        "engine_capacity": ship.engine_capacity,
    }

    for metric, ship_max in maxima.items():
        values = [used[label][metric] for label in labels]
        cells: list[str | Text] = [metric, *(f"{v:,.0f}" for v in values)]
        delta = values[-1] - values[0] if len(values) >= 2 else 0
        cells.append(_format_delta(delta, "{:,.0f}", lower_is_better=True))
        cells.append(f"{ship_max:,.0f}")
        table.add_row(*cells)
    return table


def _heat_energy_stats(solution: SolutionResult, ship: Ship) -> dict[str, float]:
    idle_energy = 0.0
    idle_heat = 0.0
    burst_energy = 0.0
    burst_heat = 0.0
    cooling = 0.0

    for item, count in chain(solution.outfits.items(), solution.weapons.items()):
        if isinstance(item, Outfit):
            idle_energy += (
                (item.energy_generation - item.energy_consumption) * count * FPS
            )
            idle_heat += item.heat_generation * count * FPS
            burst_energy -= (
                (
                    max(item.thrusting_energy, item.reverse_thrusting_energy)
                    + item.turning_energy
                    + item.shield_energy
                )
                * count
                * FPS
            )
            burst_heat += (
                (
                    max(item.thrusting_heat, item.reverse_thrusting_heat)
                    + item.turning_heat
                )
                * count
                * FPS
            )
            cooling += item.cooling * count * FPS
        if isinstance(item, Weapon):
            burst_energy -= item.firing_energy * count * FPS
            burst_heat += item.firing_heat * count * FPS

    burst_energy += idle_energy
    burst_heat += idle_heat
    heat_equilibrium = (
        (burst_heat - cooling) / (ship.heat_dissipation * 0.001 * FPS)
        if ship.heat_dissipation
        else 0
    )
    return {
        "idle_energy": idle_energy,
        "idle_heat": idle_heat,
        "burst_energy": burst_energy,
        "burst_heat": burst_heat,
        "heat_equilibrium": heat_equilibrium,
    }


def get_heat_and_energy_table(
    solutions: dict[str, SolutionResult], ship: Ship
) -> Table:
    labels = _solution_columns(solutions)
    table = Table("metric", *labels, "Δ", title="Heat & Energy")

    stats = {label: _heat_energy_stats(sol, ship) for label, sol in solutions.items()}

    def row(metric: str, lower_is_better: bool) -> None:
        _add_comparison_row(
            table,
            metric,
            [stats[label][metric] for label in labels],
            "{:,.0f}",
            lower_is_better,
        )

    row("idle_energy", lower_is_better=False)
    row("burst_energy", lower_is_better=False)
    row("idle_heat", lower_is_better=True)
    row("burst_heat", lower_is_better=True)
    row("heat_equilibrium", lower_is_better=True)
    return table


def get_shield_table(solutions: dict[str, SolutionResult]) -> Table:
    labels = _solution_columns(solutions)
    table = Table("metric", *labels, "Δ", title="Shield generation")
    values = [
        sum(o.shield_generation * c * FPS for o, c in solutions[label].outfits.items())
        for label in labels
    ]
    _add_comparison_row(table, "shield_generation", values, "{:,.2f}")
    return table
