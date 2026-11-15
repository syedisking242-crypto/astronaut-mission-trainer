from dataclasses import dataclass


@dataclass(frozen=True)
class Mission:
    id: str
    name: str
    category: str
    description: str
    base_score: int


MISSIONS = (
    Mission("launch", "Launch Readiness", "Flight Operations", "Prepare the spacecraft and complete a safe launch sequence.", 100),
    Mission("navigation", "Orbital Navigation", "Navigation", "Pilot through an asteroid field and reach the orbital beacon.", 120),
    Mission("emergency", "Emergency Response", "Systems", "Diagnose a spacecraft alert and choose the safest corrective action.", 100),
    Mission("eva", "Satellite Repair EVA", "Spacewalk", "Complete a tethered repair and collect the required repair kit.", 110),
    Mission("communication", "Earth Communications", "Communications", "Send a clear status report and acknowledge mission control instructions.", 80),
)


MISSION_BRIEFINGS = {
    "launch": {
        "objective": "Prepare the spacecraft and reach a safe liftoff.",
        "instructions": "Verify each pre-launch item, check the simulated fuel reserve, then start the countdown.",
        "controls": "Use the checklist boxes and Begin countdown button.",
        "success": "Fuel is at least 25% and all three checklist items are complete.",
        "failure": "Fuel is below 25% or any checklist item is incomplete.",
    },
    "navigation": {
        "objective": "Pilot to the orbital beacon while avoiding asteroids.",
        "instructions": "Steer carefully through the field. Three collision alerts end the attempt.",
        "controls": "Arrow keys move the spacecraft; ESC exits the simulation.",
        "success": "Reach the cyan beacon at the top of the flight area.",
        "failure": "Three asteroid collisions or exiting before reaching the beacon.",
    },
    "emergency": {
        "objective": "Choose the safest first response to a spacecraft emergency.",
        "instructions": "Read the alert, compare the available corrective actions, and submit one response.",
        "controls": "Choose a scenario, select one response, then submit it.",
        "success": "Select the correct immediate action for the emergency.",
        "failure": "Choose an action that increases mission risk.",
    },
    "eva": {
        "objective": "Repair the satellite and collect its replacement equipment.",
        "instructions": "Keep the safety tether secured, complete both tasks, and watch suit oxygen as you work.",
        "controls": "Check off completed tasks, use Perform EVA task to spend oxygen, then end the spacewalk.",
        "success": "The tether is secured, oxygen remains, and repair plus equipment collection are complete.",
        "failure": "The tether is unsecured, oxygen is depleted, or an objective remains incomplete.",
    },
    "communication": {
        "objective": "Send a clear spacecraft status report to mission control.",
        "instructions": "Include a status and a mission or system detail. Wait for mission control's delayed reply.",
        "controls": "Edit the message and select Transmit to mission control.",
        "success": "The report is at least 20 characters and includes status, systems, mission, oxygen, or repair.",
        "failure": "The report is too short or omits mission-relevant detail.",
    },
}