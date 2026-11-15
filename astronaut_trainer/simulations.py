import random


def new_telemetry() -> dict[str, float]:
    return {
        "oxygen": round(random.uniform(87, 100), 1), "battery": round(random.uniform(65, 100), 1),
        "fuel": round(random.uniform(72, 100), 1), "cabin_temperature": round(random.uniform(19, 25), 1),
        "cabin_pressure": round(random.uniform(96, 104), 1), "heart_rate": round(random.uniform(68, 104), 1),
        "body_temperature": round(random.uniform(36.3, 37.4), 1), "oxygen_saturation": round(random.uniform(94, 100), 1),
    }


def advance_telemetry(current: dict[str, float]) -> dict[str, float]:
    current["oxygen"] = round(max(0, current["oxygen"] - random.uniform(1, 4)), 1)
    current["battery"] = round(max(0, current["battery"] - random.uniform(0.5, 2.5)), 1)
    current["fuel"] = round(max(0, current["fuel"] - random.uniform(1, 3.5)), 1)
    current["cabin_temperature"] = round(min(39, max(10, current["cabin_temperature"] + random.uniform(-1.2, 1.2))), 1)
    current["cabin_pressure"] = round(min(125, max(65, current["cabin_pressure"] + random.uniform(-2.5, 2.5))), 1)
    current["heart_rate"] = round(min(150, max(45, current["heart_rate"] + random.uniform(-5, 7))), 1)
    current["body_temperature"] = round(min(39, max(35, current["body_temperature"] + random.uniform(-0.2, 0.3))), 1)
    current["oxygen_saturation"] = round(min(100, max(75, current["oxygen_saturation"] - random.uniform(0, 1.5))), 1)
    return current


def telemetry_status(key: str, value: float) -> str:
    if key in {"oxygen", "battery", "fuel", "oxygen_saturation"}:
        critical, warning = ((40, 70) if key == "oxygen" else (15, 40) if key == "battery" else
                             (10, 25) if key == "fuel" else (85, 92))
        if value < critical:
            return "CRITICAL"
        if value < warning:
            return "WARNING"
        return "NORMAL"
    if key in {"cabin_temperature", "body_temperature"}:
        if value < 14 or value > 32:
            return "CRITICAL"
        if value < 18 or value > 28:
            return "WARNING"
        return "NORMAL"
    if key == "cabin_pressure":
        if value < 75 or value > 120:
            return "CRITICAL"
        if value < 90 or value > 110:
            return "WARNING"
    return "NORMAL"


EMERGENCIES = {
    "Oxygen leak": ("Isolate the affected oxygen line", "Increase cabin temperature", "Disable communications"),
    "Low battery": ("Switch to power-saving mode", "Run all nonessential equipment", "Vent cabin air"),
    "Cabin pressure failure": ("Seal the pressure compartment", "Open the airlock", "Increase cabin heating"),
    "High temperature": ("Activate thermal regulation", "Power down life support", "Open exterior hatch"),
    "Communication failure": ("Switch to backup antenna", "End the mission immediately", "Disable navigation"),
}


CORRECT_ACTIONS = {
    "Oxygen leak": "Isolate the affected oxygen line", "Low battery": "Switch to power-saving mode",
    "Cabin pressure failure": "Seal the pressure compartment", "High temperature": "Activate thermal regulation",
    "Communication failure": "Switch to backup antenna",
}


def evaluate_emergency(scenario: str, action: str) -> tuple[bool, str]:
    if action == CORRECT_ACTIONS.get(scenario):
        return True, "Correct response. The immediate hazard is controlled and the crew can continue safely."
    return False, f"That action increases mission risk. The safer first response is: {CORRECT_ACTIONS[scenario]}."


def launch_checklist(fuel: float, checks: dict[str, bool]) -> tuple[bool, str]:
    missing = [label for label, done in checks.items() if not done]
    if fuel < 25:
        return False, "Launch scrubbed: fuel reserve is below the 25% minimum."
    if missing:
        return False, "Launch scrubbed: complete " + ", ".join(missing) + "."
    return True, "All systems nominal. Launch sequence authorized."


def evaluate_eva(repaired: bool, kit_collected: bool, tethered: bool, oxygen: float) -> tuple[bool, str]:
    if not tethered:
        return False, "EVA terminated: safety tether was not secured."
    if oxygen <= 0:
        return False, "EVA terminated: suit oxygen reserve depleted."
    if repaired and kit_collected:
        return True, "Satellite repair complete and replacement kit secured."
    return False, "EVA incomplete: repair and equipment collection are both required."


def communication_report(body: str) -> bool:
    return len(body.strip()) >= 20 and any(word in body.lower() for word in ("status", "systems", "mission", "oxygen", "repair"))