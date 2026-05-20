from es_optimizer.database.parser import Node
from es_optimizer.database.models import (
    Outfit,
    OutfitCategory,
    Ship,
    ShipCategory,
    Weapon,
    WeaponCategory,
)


def load_ships(tree: Node) -> list[Ship]:
    ships: list[Ship] = []
    for ship_node in tree.children:
        assert ship_node.value is not None

        # Skip ship modifications: they differ only in the outfits installed
        if isinstance(ship_node.value, list):
            continue

        attributes_node = [c for c in ship_node.children if c.key == "attributes"][0]
        attributes: dict[str, str] = {}
        for ch in attributes_node.children:
            if ch.key in ["weapon", "licenses"]:
                continue
            assert isinstance(ch.key, str), f"{ship_node.value}: {ch.key}"
            assert isinstance(ch.value, str), f"{ship_node.value}: {ch.key} {ch.value}"
            attributes[ch.key] = ch.value

        ship = Ship(
            name=ship_node.value,
            category=ShipCategory(attributes["category"]),
            cost=int(attributes["cost"]),
            shields=int(attributes.get("shields", 0)),
            hull=int(attributes["hull"]),
            required_crew=int(attributes.get("required crew", 0)),
            bunks=int(attributes.get("bunks", 0)),
            mass=int(attributes["mass"]),
            drag=float(attributes["drag"]),
            heat_dissipation=float(attributes["heat dissipation"]),
            fuel_capacity=int(attributes.get("fuel capacity", 0)),
            cargo_space=int(attributes.get("cargo space", 0)),
            outfit_space=int(attributes["outfit space"]),
            weapon_capacity=int(attributes.get("weapon capacity", 0)),
            engine_capacity=int(attributes["engine capacity"]),
        )
        ships.append(ship)

    return ships


def load_weapons(tree: Node) -> list[Weapon]:
    weapons: list[Weapon] = []

    for node in tree.children:
        if node.key in ["outfitter", "effect"]:
            continue
        assert node.key == "outfit"
        assert isinstance(node.value, str), node.value

        outfit_attributes: dict[str, str] = {}
        for c in node.children:
            if not c.children and isinstance(c.value, str):
                assert c.key
                outfit_attributes[c.key] = c.value

        # Skip ammunition and subammunition
        if outfit_attributes.get("category") in ["Ammunition", None]:
            continue

        weapon_node = [c for c in node.children if c.key == "weapon"][0]

        weapon_attributes: dict[str, str] = {}
        for c in weapon_node.children:
            if c.key in [
                "hit effect",
                "hardpoint offset",
                "submunition",
                "homing",
                "stream",
                "triggers nuke alert",
                "cluster",
                "ammo",
            ]:
                continue
            assert c.key
            assert isinstance(c.value, str), c.key
            weapon_attributes[c.key] = c.value
        weapon = Weapon(
            name=node.value,
            category=WeaponCategory(outfit_attributes["category"]),
            cost=int(outfit_attributes["cost"]),
            mass=int(outfit_attributes["mass"]),
            outfit_space=int(outfit_attributes["outfit space"]),
            weapon_capacity=int(outfit_attributes["weapon capacity"]),
            gun_ports=int(outfit_attributes.get("gun ports", 0)),
            inaccuracy=float(weapon_attributes.get("inaccuracy", 0)),
            lifetime=int(weapon_attributes["lifetime"]),
            reload=float(weapon_attributes["reload"]),
            firing_energy=float(weapon_attributes["firing energy"]),
            firing_heat=float(weapon_attributes["firing heat"]),
            shield_damage=float(weapon_attributes.get("shield damage", 0)),
            hull_damage=float(weapon_attributes.get("hull damage", 0)),
        )
        weapons.append(weapon)
    return weapons


def load_outfits(tree: Node) -> list[Outfit]:
    outfits: list[Outfit] = []

    for node in tree.children:
        assert isinstance(node.value, str)

        attributes: dict[str, str] = {}
        for c in node.children:
            if c.key != "description":
                assert c.key is not None
                assert isinstance(c.value, str)
                attributes[c.key] = c.value
        if attributes["category"] not in ["Systems", "Power", "Engines"]:
            continue

        outfit = Outfit(
            name=node.value,
            category=OutfitCategory(attributes["category"]),
            cost=float(attributes.get("cost", 0)),
            mass=float(attributes.get("mass", 0)),
            outfit_space=float(attributes.get("outfit space", 0)),
            cooling=float(attributes.get("cooling", 0)),
            shield_generation=float(attributes.get("shield generation", 0)),
            shield_energy=float(attributes.get("shield energy", 0)),
            energy_consumption=float(attributes.get("energy consumption", 0)),
            heat_generation=float(attributes.get("heat generation", 0)),
            fuel_capacity=float(attributes.get("fuel capacity", 0)),
            required_crew=float(attributes.get("required crew", 0)),
            solar_collection=float(attributes.get("solar collection", 0)),
            energy_generation=float(attributes.get("energy generation", 0)),
            energy_capacity=float(attributes.get("energy capacity", 0)),
        )
        outfits.append(outfit)

    return outfits
