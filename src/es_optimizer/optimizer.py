import pulp
from rich.console import Console
from rich.rule import Rule
from rich.table import Table
from rich.columns import Columns

from es_optimizer.database.loader import load
from es_optimizer.database.models import Outfit, Ship, Weapon, WeaponCategory

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


prob = pulp.LpProblem(sense=pulp.LpMaximize)
weapons_count: dict[str, pulp.LpVariable] = pulp.LpVariable.dict(
    "weapons_count", db.weapons.keys(), 0, 6, cat=pulp.LpInteger
)
outfits_count: dict[str, pulp.LpVariable] = pulp.LpVariable.dict(
    "outfits_count", db.outfits.keys(), 0, 6, cat=pulp.LpInteger
)


total_cost = pulp.LpAffineExpression()
total_mass = pulp.LpAffineExpression()
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


# Speed
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


status = prob.solve(solver=pulp.PULP_CBC_CMD(msg=False))
assert status == pulp.LpStatusOptimal

console.print(Rule("Results"))


outfits_table = Table("outfit", "amount", "category", title="Outfits")
for weapon, v in weapons_count.items():
    if v.varValue != 0:
        assert v.varValue is not None
        outfits_table.add_row(
            weapon, str(int(v.varValue)), db.weapons[weapon].category.value
        )

for outfit, v in outfits_count.items():
    assert v.varValue is not None
    if v.varValue != 0:
        outfits_table.add_row(
            outfit, str(int(v.varValue)), db.outfits[outfit].category.value
        )

# parameters_table
# fmt: off
parameters_table = Table("parameter", "result", "ship", title="Result parameters")
parameters_table.add_row("outfit_space", str(total_outfit_space.value()), str(target_ship.outfit_space))
parameters_table.add_row("weapon_capacity", str(total_weapon_capacity.value()), str(target_ship.weapon_capacity))
parameters_table.add_row("gun_ports", str(total_gun_ports.value()), str(target_ship.gun_ports))
parameters_table.add_row("turret_mounts", str(total_turret_mounts.value()), str(target_ship.turret_mounts))
parameters_table.add_row("engine_capacity", str(total_engine_capacity.value()), str(target_ship.engine_capacity))
# fmt: on

parameters_table.add_row("cost", str(total_cost.value()))
parameters_table.add_row("shiled damage", str(total_shield_damage.value()))
parameters_table.add_row("hull damage", str(total_hull_damage.value()))
parameters_table.add_row("thrust", str(total_thrust.value()))
parameters_table.add_row("turn", str(total_turn.value()))
parameters_table.add_row(
    "energy",
    str(total_energy_generation.value()),
    str(burst_additional_energy_cost.value()),
)
parameters_table.add_row("capacity", str(total_energy_capacity.value()))
parameters_table.add_row(
    "heat", str(total_cooling.value()), str(total_max_heat_cost.value())
)


# fmt: off
debug_table = Table(title="parameters_table")
debug_table.add_row("idle_energy_cost", str(idle_energy_cost.value()))
debug_table.add_row("burst_additional_energy_cost", str(burst_additional_energy_cost.value()))
debug_table.add_row("total_max_heat_cost", str(total_max_heat_cost.value()))
debug_table.add_row("total_cooling", str(total_cooling.value()))
debug_table.add_row("total_shield_generation", str(total_shield_generation.value()))
debug_table.add_row("total_thrust", str(total_thrust.value()))
debug_table.add_row("total_turn", str(total_turn.value()))
debug_table.add_row("total_reverse_thrust", str(total_reverse_thrust.value()))
debug_table.add_row("total_shield_damage", str(total_shield_damage.value()))
debug_table.add_row("total_hull_damage", str(total_hull_damage.value()))
debug_table.add_row("total_energy_capacity", str(total_energy_capacity.value()))
debug_table.add_row("total_energy_generation", str(total_energy_generation.value()))
debug_table.add_row("total_solar_collection", str(total_solar_collection.value()))
debug_table.add_row("H_eq", str(H_eq.value()))
debug_table.add_row("safety × max_h", str((safety_factor * max_heat).value()))
debug_table.add_row("heat_in/sec", str(total_max_heat_cost.value()))
debug_table.add_row("cooling/sec", str(total_cooling.value()))
debug_table.add_row("slack to cap", str((safety_factor * max_heat - H_eq).value()))
# fmt: on

console.print(Columns([outfits_table, parameters_table, debug_table]))
