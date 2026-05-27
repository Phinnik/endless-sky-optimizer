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


@dataclass(frozen=True)
class Ship:
    # --- Common attributs ---
    name: str
    category: ShipCategory
    cost: int
    mass: int

    # --- Health ---
    shields: int
    hull: int

    # --- Crew and bunks ---
    required_crew: int
    bunks: int

    # --- Outfits space ---
    outfit_space: int
    weapon_capacity: int
    gun_ports: int
    turret_mounts: int
    engine_capacity: int

    drag: float
    heat_dissipation: float
    fuel_capacity: int
    cargo_space: int


class WeaponCategory(Enum):
    Turrets = "Turrets"
    SecondaryWeapons = "Secondary Weapons"
    Guns = "Guns"


@dataclass(frozen=True)
class Weapon:
    """
    :param name: weapon name.
    :param category: weapon category.
    :param cost: weapon cost.
    :param mass: weapon mass.

    :param inaccuracy: the maximum error, in degrees, in a projectile's firing angle.
    :param lifetime: how long the projectile lasts before it "dies".
    :param reload: how many frames this weapon takes to reload: 1 means it fires every turn.

    :param firing_energy: the energy cost to fire this weapon.
    :param firing_heat: heat produced when this weapon fires.

    :param shield_damage: how much damage a projectile does to shields.
    :param hull_damage: how much damage a projectile does to the hull of ships or minables.

    :param outfit_space: how much generic outfit space this outfit takes up.
    :param weapon_capacity: how much weapon space this weapon takes up.
    :param gun_ports: If the value is -1, then this weapon is a gun (shoots only forward).
        Used to limit amount of guns on a ship.
    :param turret_mounts: If the value is -1, then this weapon is a turrets (shoots 360).
        Used to limit amount of turrets on a ship.
    """

    # --- Common attributs ---
    name: str
    category: WeaponCategory
    cost: int
    mass: int

    # --- Projectile and firing behavior ---
    inaccuracy: float
    lifetime: int
    reload: float

    # --- Cost to fire the weapon ---
    firing_energy: float
    firing_heat: float

    # --- Damage ---
    shield_damage: float
    hull_damage: float

    # --- Required space ---
    outfit_space: int
    weapon_capacity: int
    gun_ports: int
    turret_mounts: int


class OutfitCategory(Enum):
    Systems = "Systems"
    Power = "Power"
    Engines = "Engines"


@dataclass(frozen=True)
class Outfit:
    """
    :param name: outfit name.
    :param category: outfit category.
    :param cost: outfit cost.
    :param mass: outfit mass.

    :param cooling: heat subtracted from ship by this outfit, per frame.

    :param shield_generation: the number of shield points regenerated per frame.
        It takes 1 energy to regenerate 1 unit of shields.
    :param shield_energy: the amount of energy drawed when outfit works at the full rate.

    :param fuel_capacity: he amount of fuel storage provided by this outfit.

    :param required_crew: crew required to operate this outfit.

    :param thrust: acceleration per frame equals `thrust / mass`, and ship's max speed is `thrust / drag`.
    :param thrusting_energy: energy cost per frame of thrusting.
    :param thrusting_heat: heat generated each frame when thrusting.
    :param turn: ship's turn rate is `turn / mass` degrees per frame.
    :param turning_energy: energy cost per frame of turning.
    :param turning_heat: heat generated each frame when turning.
    :param reverse_thrust: reverse thrust equivalent to thrust.
    :param reverse_thrusting_energy: energy cost per frame of reverse thrusting.
    :param reverse_thrusting_heat: heat produced per frame of reverse thrusting.

    :param energy_capacity: how much energy your this outfit can store.
    :param energy_generation: energy generated each frame.
    :param solar_collection: the amount of energy that this outfit provides when ship is 1250 pixels from the star.

    :param energy_consumption: energy consumed each frame.
    :param heat_generation: heat generated each frame.

    :param outfit_space: how much generic outfit space this outfit takes up.
    :param weapon_capacity: how much weapon space this weapon takes up.
    :param engine_capacity: how much engine space an outfit uses.
    """

    # --- Common attributs ---
    name: str
    category: OutfitCategory
    cost: float
    mass: float

    # --- Cooling ---
    cooling: float

    # --- Shield generators and regenerators ---
    shield_generation: float
    shield_energy: float

    # --- Fuel ---
    fuel_capacity: float

    # --- Fuel ---
    required_crew: float

    # --- Engines ---
    # Thrust
    thrust: float
    thrusting_energy: float
    thrusting_heat: float
    # Turn
    turn: float
    turning_energy: float
    turning_heat: float
    # Reverse
    reverse_thrust: float
    reverse_thrusting_energy: float
    reverse_thrusting_heat: float

    # --- Power generators and batteries ---
    energy_capacity: float
    energy_generation: float
    solar_collection: float

    # --- Cost to use the outfit (each frame)
    energy_consumption: float
    heat_generation: float

    # --- Required space ---
    outfit_space: float
    weapon_capacity: float
    engine_capacity: float
