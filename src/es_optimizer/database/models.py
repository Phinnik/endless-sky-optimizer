from dataclasses import dataclass
from enum import Enum


class ShipCategory(Enum):
    Transport = "Transport"
    HeavyFreighter = "Heavy Freighter"
    SpaceLiner = "Space Liner"
    LightFreighter = "Light Freighter"
    Drone = "Drone"
    Interceptor = "Interceptor"
    MediumWarship = "Medium Warship"
    Fighter = "Fighter"
    HeavyWarship = "Heavy Warship"
    LightWarship = "Light Warship"
    Utility = "Utility"


@dataclass
class Ship:
    name: str

    category: ShipCategory
    cost: int
    shields: int
    hull: int
    required_crew: int
    bunks: int
    mass: int
    drag: float
    heat_dissipation: float
    fuel_capacity: int
    cargo_space: int
    outfit_space: int
    weapon_capacity: int
    engine_capacity: int
