from es_optimizer.database.parser import Node
from es_optimizer.database.models import Ship, ShipCategory


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
