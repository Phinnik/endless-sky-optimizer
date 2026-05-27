from dataclasses import dataclass, field

import pulp

from es_optimizer.database.loader import DataBase
from es_optimizer.database.models import Outfit, Ship, Weapon
from es_optimizer.helpets import value_of

FPS = 60


@dataclass(frozen=True)
class SolutionResult:
    outfits: dict[Outfit, int]
    weapons: dict[Weapon, int]


@dataclass
class Settings:
    outfit_count_upper_bound = 50

    combat_intensity: float = 0.5
    burst_time: float = 30

    heat_safety_factor: float = 0.95

    enemy_paper_DPS: float = 1500
    combat_efficiency: float = 0.05

    target_top_speed: float = 300  # units/sec
    target_acceleration: float = 75  # units/sec²
    target_turn_rate: float = 60  # deg/sec

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
        idle_energy + burst_energy * settings.combat_intensity
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
    prob += shield_generation >= expected_incoming_DPS

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
