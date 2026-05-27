
from rich.columns import Columns
from rich.console import Console, Group
from rich.rule import Rule

from es_optimizer.database.loader import load
from es_optimizer.database.models import Outfit, Weapon, WeaponCategory
from es_optimizer.optimizer import Settings, SolutionResult, get_solution
from es_optimizer.report import (
    get_capacity_table,
    get_dps_table,
    get_heat_and_energy_table,
    get_movement_table,
    get_shield_table,
    get_shopping_list_table,
)


def main():
    console = Console()
    db = load()

    target_ship = db.ships["Aerie"]

    assert target_ship.outfits is not None
    baseline_outfits = {
        o: count for o, count in target_ship.outfits.items() if isinstance(o, Outfit)
    }
    baseline_weapons = {
        o: count for o, count in target_ship.outfits.items() if isinstance(o, Weapon)
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

    settings = Settings(
        combat_intensity=0.5,
        burst_time=30,
        heat_safety_factor=0.95,
        enemy_paper_DPS=1500,
        combat_efficiency=0.02,
        target_top_speed=422.195,  # units/sec
        target_acceleration=205.52770,  # units/sec²
        target_turn_rate=90,  # deg/sec
        shield_dps_weight=1000,
        hull_dps_weight=0.5,
        cost_weight=0.000_000_001,
        required_weapons={},
    )

    solutions: dict[str, SolutionResult] = {
        "Baseline": baseline,
        "Optimized": get_solution(db, target_ship, settings),
    }

    console.print(Rule(f"{target_ship.name}: Baseline vs Optimized"))
    console.print(get_shopping_list_table(solutions))
    console.print(
        Columns(
            [
                Group(
                    get_movement_table(solutions, target_ship),
                    get_dps_table(solutions),
                    get_shield_table(solutions),
                ),
                Group(
                    get_capacity_table(solutions, target_ship),
                    get_heat_and_energy_table(solutions, target_ship),
                ),
            ]
        )
    )


if __name__ == "__main__":
    main()
