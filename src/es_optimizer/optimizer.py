from dataclasses import dataclass, field
from itertools import chain

import pulp
from rich.columns import Columns
from rich.console import Console, Group
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text

from es_optimizer.database.loader import DataBase, load
from es_optimizer.database.models import Outfit, Ship, Weapon, WeaponCategory
from es_optimizer.helpets import value_of

FPS = 60


@dataclass(frozen=True)
class SolutionResult:
    weapons: dict[Weapon, int]
    outfits: dict[Outfit, int]


@dataclass
class Settings:
    outfit_count_upper_bound = 50

    combat_intencity = 0.5
    burst_time = 30

    heat_safety_factor = 0.95

    enemy_paper_DPS = 1500
    combat_efficiency = 0.20

    target_top_speed = 300  # units/sec
    target_acceleration = 75  # units/sec²
    target_turn_rate = 60  # deg/sec

    shield_dps_weight: float = 100
    hull_dps_weight: float = 0.5
    cost_weight: float = 0.000_000_001

    required_outfits: dict[str, int] = field(default_factory=lambda: {"Hyperdrive": 1})
    required_weapons: dict[str, int] = field(
        default_factory=lambda: {"Anti-Missile Turret": 1}
    )


def get_solution(db: DataBase, ship: Ship, settings: Settings) -> SolutionResult:
    prob = pulp.LpProblem(sense=pulp.LpMaximize)

    weapons_count: dict[str, pulp.LpVariable] = pulp.LpVariable.dict(
        "weapons_count",
        db.weapons.keys(),
        0,
        settings.outfit_count_upper_bound,
        cat=pulp.LpInteger,
    )
    outfits_count: dict[str, pulp.LpVariable] = pulp.LpVariable.dict(
        "outfits_count",
        db.outfits.keys(),
        0,
        settings.outfit_count_upper_bound,
        cat=pulp.LpInteger,
    )

    cost = pulp.LpAffineExpression()
    total_mass = pulp.LpAffineExpression(ship.mass)

    outfit_space = pulp.LpAffineExpression()
    weapon_capacity = pulp.LpAffineExpression()
    gun_ports = pulp.LpAffineExpression()
    turret_mounts = pulp.LpAffineExpression()
    engine_capacity = pulp.LpAffineExpression()

    idle_energy = pulp.LpAffineExpression()
    burst_energy = pulp.LpAffineExpression()
    idle_heat = pulp.LpAffineExpression()
    burst_heat = pulp.LpAffineExpression()

    total_cooling = pulp.LpAffineExpression()
    shield_generation = pulp.LpAffineExpression()

    # Speed
    thrust = pulp.LpAffineExpression()
    turn = pulp.LpAffineExpression()

    # Damage
    shield_dps = pulp.LpAffineExpression()
    hull_dps = pulp.LpAffineExpression()

    # Energy generation
    energy_capacity = pulp.LpAffineExpression()
    energy_generation = pulp.LpAffineExpression()
    solar_collection = pulp.LpAffineExpression()

    for weapon_name, v in weapons_count.items():
        weapon = db.weapons[weapon_name]

        cost += weapon.cost * v
        total_mass += weapon.mass * v
        burst_energy += (weapon.firing_energy / weapon.reload) * v * FPS
        burst_heat += (weapon.firing_heat / weapon.reload) * v * FPS

        shield_dps += (weapon.shield_damage / weapon.reload) * v * FPS
        hull_dps += (weapon.hull_damage / weapon.reload) * v * FPS

        outfit_space += weapon.outfit_space * v
        weapon_capacity += weapon.weapon_capacity * v
        gun_ports += weapon.gun_ports * v
        turret_mounts += weapon.turret_mounts * v

    for outfit_name, v in outfits_count.items():
        outfit = db.outfits[outfit_name]

        cost += outfit.cost * v
        total_mass += outfit.mass * v
        total_cooling += outfit.cooling * v * FPS
        shield_generation += outfit.shield_generation * v * FPS
        burst_energy += outfit.shield_energy * v * FPS

        thrust += outfit.thrust * v
        burst_energy += outfit.thrusting_energy * v * FPS
        burst_heat += outfit.thrusting_heat * v * FPS

        turn += outfit.turn * v
        burst_energy += outfit.turning_energy * v * FPS
        burst_heat += outfit.turning_heat * v * FPS

        energy_capacity += outfit.energy_capacity * v
        energy_generation += outfit.energy_generation * v * FPS
        solar_collection += outfit.solar_collection * v * FPS

        idle_energy += outfit.energy_consumption * v * FPS
        idle_heat += outfit.heat_generation * v * FPS

        outfit_space += outfit.outfit_space * v
        weapon_capacity += outfit.weapon_capacity * v
        engine_capacity += outfit.engine_capacity * v

    for outfit, count in settings.required_outfits.items():
        prob += outfits_count[outfit] == count
    for outfit, count in settings.required_weapons.items():
        prob += weapons_count[outfit] == count

    # Space and capacity
    prob += outfit_space + ship.outfit_space >= 0
    prob += weapon_capacity + ship.weapon_capacity >= 0
    prob += gun_ports + ship.gun_ports >= 0
    prob += turret_mounts + ship.turret_mounts >= 0
    prob += engine_capacity + ship.engine_capacity >= 0

    # Energy
    # TODO: Review theese constraints: are they optimal? What problem do they solve?
    prob += energy_generation >= (
        idle_energy + burst_energy * settings.combat_intencity
    )
    prob += energy_capacity >= (burst_energy - energy_generation) * settings.burst_time

    # Heat and cooling
    max_heat = total_mass * 100  # 100 - MAXIMUM_TEMPERATURE
    heat_equilibrium = (idle_heat + burst_heat - total_cooling) / (
        ship.heat_dissipation * 0.001 * FPS
    )
    prob += heat_equilibrium <= (settings.heat_safety_factor * max_heat)

    # Shield generation
    # Note: incoming_DPS != paper_DPS (movement, misses, kills etc.)
    expected_incoming_DPS = settings.enemy_paper_DPS * settings.combat_efficiency
    prob += shield_generation >= settings.combat_efficiency * expected_incoming_DPS

    # Movement
    # TODO: support reverse thrust
    prob += thrust >= settings.target_top_speed * ship.drag / FPS
    prob += thrust * FPS**2 >= settings.target_acceleration * total_mass
    prob += turn * FPS >= settings.target_turn_rate * total_mass

    # Objective
    prob += (
        settings.shield_dps_weight * shield_dps + settings.hull_dps_weight * hull_dps
    ) - settings.cost_weight * cost

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


def get_heat_and_energy_table(solution: SolutionResult, ship: Ship) -> Table:
    table = Table("", "energy", "heat")
    idle_energy = 0
    idle_heat = 0
    burst_energy = 0
    burst_heat = 0
    cooling = 0

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
            cooling += outfit.cooling * count * FPS

        if isinstance(outfit, Weapon):
            burst_energy -= outfit.firing_energy * count * FPS
            burst_heat += outfit.firing_heat * count * FPS

    burst_energy += idle_energy
    burst_heat += idle_heat

    heat_equilibrium = (burst_heat - cooling) / (ship.heat_dissipation * 0.001 * FPS)

    table.add_row("idle", f"{idle_energy:,.0f}", f"{idle_heat:,.0f}")
    table.add_row("burst", f"{burst_energy:,.0f}", f"{burst_heat:,.0f}")

    table.add_row("heat_equilibrium", "", f"{heat_equilibrium:,.0f}")
    return table


def get_shield_table(solution: SolutionResult):
    shield_generation = 0
    for outfit, count in solution.outfits.items():
        shield_generation += outfit.shield_generation * count * FPS
    table = Table(title="Shield generation", show_header=False)
    table.add_row("shield_generation", f"{shield_generation:,.2f}")
    return table


def main():
    console = Console()
    db = load()

    target_ship = db.ships["Falcon"]

    assert target_ship.outfits is not None
    baseline_outfits = {
        o: count for o, count in target_ship.outfits.items() if isinstance(o, Weapon)
    }
    baseline_weapons = {
        o: count for o, count in target_ship.outfits.items() if isinstance(o, Outfit)
    }
    baseline = SolutionResult(baseline_outfits, baseline_weapons)

    db.weapons = {
        name: weapon
        for name, weapon in db.weapons.items()
        if weapon.category != WeaponCategory.SecondaryWeapons
        and weapon.name not in ["Heavy Blaster", "Plasma Repeater"]
    }
    db.outfits = {
        name: outfit
        for name, outfit in db.outfits.items()
        if name not in ["Outfits Expansion"]
    }
    db.outfits = {
        name: outfit for name, outfit in db.outfits.items() if "Regenerator" not in name
    }

    solution = baseline

    settings = Settings()

    solution = get_solution(db, target_ship, settings)

    console.print(Rule("Results"))
    console.print(get_shopping_list_table(solution))
    console.print(
        Columns(
            [
                Group(
                    get_movement_table(solution, target_ship),
                    get_dps_table(solution),
                    get_shield_table(solution),
                ),
                Group(
                    get_capacity_table(solution, target_ship),
                    get_heat_and_energy_table(solution, target_ship),
                ),
            ]
        )
    )


if __name__ == "__main__":
    main()
