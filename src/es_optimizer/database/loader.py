from es_optimizer.database.parser import Node
from es_optimizer.database.models import (
    Outfit,
    OutfitCategory,
    Ship,
    ShipCategory,
    Weapon,
    WeaponCategory,
)


def _attrs(node: Node) -> dict[str, str]:
    return {
        c.key: c.value
        for c in node.children
        if isinstance(c.key, str) and isinstance(c.value, str) and not c.children
    }


def load_ships(tree: Node) -> list[Ship]:
    ships: list[Ship] = []
    for ship_node in tree.children:
        # Skip ship modifications: they differ only in the outfits installed
        if isinstance(ship_node.value, list):
            continue

        attrs_node = next(c for c in ship_node.children if c.key == "attributes")
        a = _attrs(attrs_node)

        ships.append(
            Ship(
                name=ship_node.value,
                category=ShipCategory(a["category"]),
                cost=int(a["cost"]),
                shields=int(a.get("shields", 0)),
                hull=int(a["hull"]),
                required_crew=int(a.get("required crew", 0)),
                bunks=int(a.get("bunks", 0)),
                mass=int(a["mass"]),
                drag=float(a["drag"]),
                heat_dissipation=float(a["heat dissipation"]),
                fuel_capacity=int(a.get("fuel capacity", 0)),
                cargo_space=int(a.get("cargo space", 0)),
                outfit_space=int(a["outfit space"]),
                weapon_capacity=int(a.get("weapon capacity", 0)),
                engine_capacity=int(a["engine capacity"]),
            )
        )
    return ships


def load_weapons(tree: Node) -> list[Weapon]:
    weapons: list[Weapon] = []
    for node in tree.children:
        if node.key != "outfit":
            continue

        outfit_a = _attrs(node)
        try:
            category = WeaponCategory(outfit_a.get("category", ""))
        except ValueError:
            continue

        weapon_node = next(c for c in node.children if c.key == "weapon")
        weapon_a = _attrs(weapon_node)

        weapons.append(
            Weapon(
                name=node.value,
                category=category,
                cost=int(outfit_a["cost"]),
                mass=int(outfit_a["mass"]),
                outfit_space=int(outfit_a["outfit space"]),
                weapon_capacity=int(outfit_a["weapon capacity"]),
                turret_mounts=int(outfit_a.get("turret mounts", 0)),
                gun_ports=int(outfit_a.get("gun ports", 0)),
                inaccuracy=float(weapon_a.get("inaccuracy", 0)),
                lifetime=int(weapon_a["lifetime"]),
                reload=float(weapon_a["reload"]),
                firing_energy=float(weapon_a["firing energy"]),
                firing_heat=float(weapon_a["firing heat"]),
                shield_damage=float(weapon_a.get("shield damage", 0)),
                hull_damage=float(weapon_a.get("hull damage", 0)),
            )
        )
    return weapons


def load_outfits(tree: Node) -> list[Outfit]:
    outfits: list[Outfit] = []
    for node in tree.children:
        a = _attrs(node)
        try:
            category = OutfitCategory(a.get("category", ""))
        except ValueError:
            continue

        outfits.append(
            Outfit(
                name=node.value,
                category=category,
                cost=float(a.get("cost", 0)),
                mass=float(a.get("mass", 0)),
                outfit_space=float(a.get("outfit space", 0)),
                cooling=float(a.get("cooling", 0)),
                shield_generation=float(a.get("shield generation", 0)),
                shield_energy=float(a.get("shield energy", 0)),
                energy_consumption=float(a.get("energy consumption", 0)),
                heat_generation=float(a.get("heat generation", 0)),
                fuel_capacity=float(a.get("fuel capacity", 0)),
                required_crew=float(a.get("required crew", 0)),
                solar_collection=float(a.get("solar collection", 0)),
                energy_generation=float(a.get("energy generation", 0)),
                energy_capacity=float(a.get("energy capacity", 0)),
                reverse_thrusting_energy=float(a.get("reverse thrusting energy", 0)),
                turning_energy=float(a.get("turning energy", 0)),
                thrust=float(a.get("thrust", 0)),
                thrusting_heat=float(a.get("thrusting heat", 0)),
                turning_heat=float(a.get("turning heat", 0)),
                reverse_thrust=float(a.get("reverse thrust", 0)),
                thrusting_energy=float(a.get("thrusting energy", 0)),
                engine_capacity=float(a.get("engine capacity", 0)),
                turn=float(a.get("turn", 0)),
                reverse_thrusting_heat=float(a.get("reverse thrusting heat", 0)),
                weapon_capacity=float(a.get("weapon capacity", 0)),
            )
        )
    return outfits
