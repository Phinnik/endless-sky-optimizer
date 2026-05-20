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


class WeaponCategory(Enum):
    Turrets = "Turrets"
    SecondaryWeapons = "Secondary Weapons"
    Guns = "Guns"


@dataclass
class Weapon:
    name: str

    category: WeaponCategory
    cost: int
    mass: int
    outfit_space: int
    weapon_capacity: int
    gun_ports: int
    inaccuracy: float
    lifetime: int
    reload: float
    firing_energy: float
    firing_heat: float
    shield_damage: float
    hull_damage: float


class OutfitCategory(Enum):
    Systems = "Systems"
    Power = "Power"
    Engines = "Engines"


@dataclass
class Outfit:
    name: str

    category: OutfitCategory
    cost: float
    mass: float
    outfit_space: float
    cooling: float
    shield_generation: float
    shield_energy: float
    energy_consumption: float
    heat_generation: float
    fuel_capacity: float
    required_crew: float
    solar_collection: float
    energy_generation: float
    energy_capacity: float
