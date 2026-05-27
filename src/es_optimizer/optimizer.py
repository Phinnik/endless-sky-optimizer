from dataclasses import dataclass
from itertools import chain
from typing import TypeAlias

import pulp
from rich.columns import Columns
from rich.console import Console, Group
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text

from es_optimizer.database.loader import load
from es_optimizer.database.models import Outfit, Ship, Weapon, WeaponCategory

FPS = 60
Valued: TypeAlias = pulp.LpVariable | pulp.LpAffineExpression


def value_of(x: Valued) -> float:
    value = x.value()
    assert value is not None, "f{x} has no value - Is the problem solved?"
    return value


console = Console()


db = load()

db.weapons = {
    name: weapon
    for name, weapon in db.weapons.items()
    if weapon.category != WeaponCategory.SecondaryWeapons
}
db.outfits = {
    name: outfit
    for name, outfit in db.outfits.items()
    if name not in ["Outfits Expansion"]
}
db.outfits = {
    name: outfit for name, outfit in db.outfits.items() if "Regenerator" not in name
}
target_ship = db.ships["Falcon"]


@dataclass(frozen=True)
class SolutionResult:
    weapons: dict[Weapon, int]
    outfits: dict[Outfit, int]


def get_solution() -> SolutionResult:
    prob = pulp.LpProblem(sense=pulp.LpMaximize)

    weapons_count: dict[str, pulp.LpVariable] = pulp.LpVariable.dict(
        "weapons_count", db.weapons.keys(), 0, 50, cat=pulp.LpInteger
    )
    outfits_count: dict[str, pulp.LpVariable] = pulp.LpVariable.dict(
        "outfits_count", db.outfits.keys(), 0, 50, cat=pulp.LpInteger
    )

    total_cost = pulp.LpAffineExpression()
    total_mass = pulp.LpAffineExpression(target_ship.mass)
    total_shields = pulp.LpAffineExpression()
    total_hull = pulp.LpAffineExpression()

    total_outfit_space = pulp.LpAffineExpression()
    total_weapon_capacity = pulp.LpAffineExpression()
    total_gun_ports = pulp.LpAffineExpression()
    total_turret_mounts = pulp.LpAffineExpression()
    total_engine_capacity = pulp.LpAffineExpression()

    idle_energy_cost = pulp.LpAffineExpression()  # idle
    burst_additional_energy_cost = pulp.LpAffineExpression()  # fire + movement
    total_max_heat_cost = pulp.LpAffineExpression()

    total_cooling = pulp.LpAffineExpression()
    total_shield_generation = pulp.LpAffineExpression()

    # Speed
    total_thrust = pulp.LpAffineExpression()
    total_turn = pulp.LpAffineExpression()
    total_reverse_thrust = pulp.LpAffineExpression()

    # Damage
    total_shield_damage = pulp.LpAffineExpression()
    total_hull_damage = pulp.LpAffineExpression()

    # Energy generation
    total_energy_capacity = pulp.LpAffineExpression()
    total_energy_generation = pulp.LpAffineExpression()
    total_solar_collection = pulp.LpAffineExpression()

    for weapon_name, v in weapons_count.items():
        weapon = db.weapons[weapon_name]

        total_cost += weapon.cost * v
        total_mass += weapon.mass * v
        burst_additional_energy_cost += (weapon.firing_energy * 60 / weapon.reload) * v
        total_max_heat_cost += (weapon.firing_heat * 60 / weapon.reload) * v

        total_shield_damage += (weapon.shield_damage * 60 / weapon.reload) * v
        total_hull_damage += (weapon.hull_damage * 60 / weapon.reload) * v

        total_outfit_space += weapon.outfit_space * v
        total_weapon_capacity += weapon.weapon_capacity * v
        total_gun_ports += weapon.gun_ports * v
        total_turret_mounts += weapon.turret_mounts * v

    for outfit_name, v in outfits_count.items():
        outfit = db.outfits[outfit_name]

        total_cost += outfit.cost * v
        total_mass += outfit.mass * v
        total_cooling += (outfit.cooling * 60) * v
        total_shield_generation += (outfit.shield_generation * 60) * v
        burst_additional_energy_cost += (outfit.shield_energy * 60) * v

        total_thrust += outfit.thrust * v
        burst_additional_energy_cost += (outfit.thrusting_energy * 60) * v
        total_max_heat_cost += (outfit.thrusting_heat * 60) * v

        total_turn += outfit.turn * v
        burst_additional_energy_cost += (outfit.turning_energy * 60) * v
        total_max_heat_cost += (outfit.turning_heat * 60) * v

        # # TODO: Thrusting cannot be done forward and backward simultaniously
        # total_reverse_thrust += outfit.reverse_thrust * v
        # total_max_energy_cost += outfit.reverse_thrusting_energy * v
        # total_max_heat_cost += outfit.reverse_thrusting_heat * v

        total_energy_capacity += outfit.energy_capacity * v
        total_energy_generation += (outfit.energy_generation * 60) * v
        total_solar_collection += (outfit.solar_collection * 60) * v

        idle_energy_cost += (outfit.energy_consumption * 60) * v
        total_max_heat_cost += (outfit.heat_generation * 60) * v

        total_outfit_space += outfit.outfit_space * v
        total_weapon_capacity += outfit.weapon_capacity * v
        total_engine_capacity += outfit.engine_capacity * v

    prob += outfits_count["Hyperdrive"] == 1

    # Total constraints

    # total_mass
    # total_shields
    # total_hull

    prob += total_outfit_space + target_ship.outfit_space >= 0
    prob += total_weapon_capacity + target_ship.weapon_capacity >= 0
    prob += total_gun_ports + target_ship.gun_ports >= 0
    prob += total_turret_mounts + target_ship.turret_mounts >= 0
    prob += total_engine_capacity + target_ship.engine_capacity >= 0

    light_combat_duty = 0.5
    burst_time = 30
    prob += total_energy_generation >= (
        idle_energy_cost + burst_additional_energy_cost * light_combat_duty
    )
    prob += (
        total_energy_capacity
        >= (burst_additional_energy_cost - total_energy_generation) * burst_time
    )

    # Heat and cooling
    safety_factor = 0.8
    max_heat = (target_ship.mass + total_mass) * 100
    H_eq = (total_max_heat_cost - total_cooling) / (target_ship.heat_dissipation * 0.06)
    prob += H_eq <= (safety_factor * max_heat)

    # shield generation
    expected_incoming_DPS = 150
    k = 0.6
    prob += total_shield_generation >= k * expected_incoming_DPS

    # Acceleration, max speed and turn
    # min_acceleration
    # min_rotation

    prob += total_thrust >= 1
    prob += total_turn >= 1
    # total_reverse_thrust

    # # Damage
    # total_shield_damage
    # total_hull_damage

    # # Energy generation
    # total_energy_capacity
    # total_energy_generation
    # total_solar_collection

    # Objective
    prob += (total_shield_damage + total_hull_damage) - (total_cost / 1_000)
    # prob += (1 * total_shield_damage + 0.5 * total_hull_damage) - (total_cost / 1_000_000)

    status = prob.solve(solver=pulp.PULP_CBC_CMD(msg=False))
    assert status == pulp.LpStatusOptimal, (
        f"Solution status is not Optimal (status={status})"
    )

    return SolutionResult(
        weapons={
            db.weapons[name]: int(value_of(var))
            for name, var in weapons_count.items()
            if value_of(var)
        },
        outfits={
            db.outfits[name]: int(value_of(var))
            for name, var in outfits_count.items()
            if value_of(var)
        },
    )


def get_shopping_list_table(solution: SolutionResult) -> Table:
    table_title = "Shopping list"
    table = Table("Outfit", "Count", "Category", "Cost", title=table_title)

    total_cost = 0

    for outfit, count in chain(solution.weapons.items(), solution.outfits.items()):
        name = outfit.name
        category = outfit.category.value
        cost = outfit.cost

        table.add_row(name, f"{count:.0f}", category)
        total_cost += cost

    table.add_row(
        Text("Total", style=Style(bold=True), justify="right"),
        "",
        "",
        Text(f"{total_cost:,.0f}", style=Style(color="cyan")),
    )
    return table


def get_movement_table(solution: SolutionResult, ship: Ship) -> Table:
    table = Table(title="Movement", show_header=False)

    thrust = 0
    turn = 0
    mass = ship.mass
    for outfit, count in chain(solution.outfits.items(), solution.weapons.items()):
        if isinstance(outfit, Outfit):
            thrust += outfit.thrust * count
            turn += outfit.turn * count
        mass += outfit.mass * count

    max_speed = thrust / ship.drag * FPS
    acceleration = thrust / mass * FPS**2
    turning = turn / mass * FPS

    time_to_full_speed = max_speed / acceleration
    time_to_360 = 360 / turning

    table.add_row("max_speed", f"{max_speed:,.3f}")
    table.add_row("acceleration", f"{acceleration:,.5f}")
    table.add_row("turning", f"{turning:,.5f}")
    table.add_row()
    table.add_row("time_to_full_speed", f"{time_to_full_speed:,.5f}")
    table.add_row("time_to_360", f"{time_to_360:,.5f}")

    return table


def get_dps_table(solution: SolutionResult) -> Table:
    table = Table(title="DPS", show_header=False)
    shield_dps = sum(
        weapon.shield_damage * count * FPS for weapon, count in solution.weapons.items()
    )
    hull_dps = sum(
        weapon.hull_damage * count * FPS for weapon, count in solution.weapons.items()
    )

    table.add_row("Shield", f"{shield_dps:,.0f}")
    table.add_row("Hull", f"{hull_dps:,.0f}")
    return table


def get_capacity_table(solution: SolutionResult, ship: Ship) -> Table:
    table = Table("", "Value", "Max value", title="Capacity")

    outfit_space = 0
    weapon_capacity = 0
    gun_ports = 0
    turret_mounts = 0
    engine_capacity = 0

    for outfit, count in chain(solution.outfits.items(), solution.weapons.items()):
        outfit_space -= outfit.outfit_space * count
        weapon_capacity -= outfit.weapon_capacity * count

        if isinstance(outfit, Outfit):
            engine_capacity -= outfit.engine_capacity * count

        if isinstance(outfit, Weapon):
            gun_ports -= outfit.gun_ports * count
            turret_mounts -= outfit.turret_mounts * count

    # fmt: off
    table.add_row("outfit_space", f"{outfit_space:,.0f}", f"{ship.outfit_space:,.0f}")
    table.add_row("weapon_capacity", f"{weapon_capacity:,.0f}", f"{ship.weapon_capacity:,.0f}")
    table.add_row("gun_ports", f"{gun_ports:,.0f}", f"{ship.gun_ports:,.0f}")
    table.add_row("turret_mounts", f"{turret_mounts:,.0f}", f"{ship.turret_mounts:,.0f}")
    table.add_row("engine_capacity", f"{engine_capacity:,.0f}", f"{ship.engine_capacity:,.0f}")
    # fmt: on

    return table


def get_heat_and_energy_table(solution: SolutionResult) -> Table:
    table = Table("", "energy", "heat")
    idle_energy = 0
    idle_heat = 0
    burst_energy = 0
    burst_heat = 0

    for outfit, count in chain(solution.outfits.items(), solution.weapons.items()):
        if isinstance(outfit, Outfit):
            idle_energy += (
                (outfit.energy_generation - outfit.energy_consumption) * count * FPS
            )
            idle_heat += outfit.heat_generation * count * FPS

            burst_energy -= (
                (
                    max(outfit.thrusting_energy, outfit.reverse_thrusting_energy)
                    + outfit.turning_energy
                    + outfit.shield_energy
                )
                * count
                * FPS
            )
            burst_heat += (
                (
                    max(outfit.thrusting_heat, outfit.reverse_thrusting_heat)
                    + outfit.turning_heat
                )
                * count
                * FPS
            )

        if isinstance(outfit, Weapon):
            burst_energy -= outfit.firing_energy * count * FPS
            burst_heat += outfit.firing_heat * count * FPS

    burst_energy += idle_energy
    burst_heat += idle_heat

    table.add_row("idle", f"{idle_energy:,.0f}", f"{idle_heat:,.0f}")
    table.add_row("burst", f"{burst_energy:,.0f}", f"{burst_heat:,.0f}")
    table.add_row("max")  # TODO: max - energy capacity and max temperature
    return table


def main():
    solution = get_solution()

    console.print(Rule("Results"))
    console.print(
        Columns(
            [
                get_shopping_list_table(solution),
                Group(
                    get_movement_table(solution, target_ship),
                    get_dps_table(solution),
                ),
                Group(
                    get_capacity_table(solution, target_ship),
                    get_heat_and_energy_table(solution),
                ),
                # parameters_table
                # debug_table
            ]
        )
    )


if __name__ == "__main__":
    main()


# fmt: off
# debug_table = Table(title="parameters_table")
# debug_table.add_row("total_shield_generation", str(total_shield_generation.value()))
# debug_table.add_row("total_energy_capacity", str(total_energy_capacity.value()))
# debug_table.add_row("H_eq", str(H_eq.value()))
# debug_table.add_row("safety × max_h", str((safety_factor * max_heat).value()))
# debug_table.add_row("heat_in/sec", str(total_max_heat_cost.value()))
# debug_table.add_row("cooling/sec", str(total_cooling.value()))
# debug_table.add_row("slack to cap", str((safety_factor * max_heat - H_eq).value()))
# fmt: on
