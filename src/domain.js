export const missions = [
  { id: 'launch', name: 'Launch Readiness', category: 'Flight Operations', description: 'Prepare the spacecraft and complete a safe launch sequence.', baseScore: 100 },
  { id: 'navigation', name: 'Orbital Navigation', category: 'Navigation', description: 'Pilot through an asteroid field and reach the orbital beacon.', baseScore: 120 },
  { id: 'emergency', name: 'Emergency Response', category: 'Systems', description: 'Diagnose a spacecraft alert and choose the safest corrective action.', baseScore: 100 },
  { id: 'eva', name: 'Satellite Repair EVA', category: 'Spacewalk', description: 'Complete a tethered repair and collect the required repair kit.', baseScore: 110 },
  { id: 'communication', name: 'Earth Communications', category: 'Communications', description: 'Send a clear status report and acknowledge mission control instructions.', baseScore: 80 },
]

export const emergencies = {
  'Oxygen leak': ['Isolate the affected oxygen line', 'Increase cabin temperature', 'Disable communications'],
  'Low battery': ['Switch to power-saving mode', 'Run all nonessential equipment', 'Vent cabin air'],
  'Cabin pressure failure': ['Seal the pressure compartment', 'Open the airlock', 'Increase cabin heating'],
  'High temperature': ['Activate thermal regulation', 'Power down life support', 'Open exterior hatch'],
  'Communication failure': ['Switch to backup antenna', 'End the mission immediately', 'Disable navigation'],
}

const correctActions = {
  'Oxygen leak': 'Isolate the affected oxygen line',
  'Low battery': 'Switch to power-saving mode',
  'Cabin pressure failure': 'Seal the pressure compartment',
  'High temperature': 'Activate thermal regulation',
  'Communication failure': 'Switch to backup antenna',
}

const initialState = { astronauts: [], activeId: null, records: [], telemetry: [], messages: [] }
const storageKey = 'orbital-academy-v1'

export function loadState() {
  try {
    return { ...initialState, ...JSON.parse(localStorage.getItem(storageKey) || '{}') }
  } catch {
    return initialState
  }
}

export function saveState(state) {
  localStorage.setItem(storageKey, JSON.stringify(state))
}

export function makeAstronaut({ name, age, profile, trainingLevel, missionId }) {
  const cleanName = name.trim().replace(/\s+/g, ' ')
  const parsedAge = Number(age)
  if (cleanName.length < 2 || cleanName.length > 60) throw new Error('Name must be between 2 and 60 characters.')
  if (!Number.isInteger(parsedAge) || parsedAge < 6 || parsedAge > 45) throw new Error('Astronauts must be between 6 and 45 years old.')
  if (profile.trim().length > 500) throw new Error('Profile must be 500 characters or fewer.')
  if (!['Cadet', 'Explorer', 'Commander'].includes(trainingLevel)) throw new Error('Select Cadet, Explorer, or Commander training.')
  if (!missions.some((mission) => mission.id === missionId)) throw new Error('Select a mission from the training manifest.')
  return {
    id: `JAT-${crypto.randomUUID().slice(0, 6).toUpperCase()}`,
    name: cleanName,
    age: parsedAge,
    profile: profile.trim() || 'Ready for mission training.',
    trainingLevel,
    selectedMissionId: missionId,
    createdAt: new Date().toISOString(),
  }
}

export function dashboardFor(state, astronautId) {
  const astronaut = state.astronauts.find((person) => person.id === astronautId)
  if (!astronaut) return null
  const records = state.records.filter((record) => record.astronautId === astronautId)
  const completed = records.filter((record) => record.status === 'completed')
  return {
    astronaut,
    attempts: records.length,
    completed: completed.length,
    score: records.reduce((sum, record) => sum + record.score, 0),
    progress: records.length ? Math.round(records.reduce((sum, record) => sum + record.completion, 0) / records.length) : 0,
    completedIds: new Set(completed.map((record) => record.missionId)),
  }
}

export function campaignFor(state, astronautId) {
  const completed = new Set(state.records.filter((record) => record.astronautId === astronautId && record.status === 'completed').map((record) => record.missionId))
  const unlocked = new Set(missions.filter((mission, index) => index === 0 || completed.has(missions[index - 1].id)).map((mission) => mission.id))
  return { completed, unlocked }
}

export function scoreMission(missionId, success, completion, mistakes) {
  const mission = missions.find((item) => item.id === missionId)
  const boundedCompletion = Math.max(0, Math.min(100, Math.trunc(completion)))
  const rawScore = success ? mission.baseScore * boundedCompletion / 100 : mission.baseScore * boundedCompletion / 200
  return Math.max(0, Math.trunc(rawScore) - Math.max(0, Math.trunc(mistakes)) * 5)
}

export function newTelemetry() {
  return {
    oxygen: randomBetween(87, 100), battery: randomBetween(65, 100), fuel: randomBetween(72, 100),
    cabinTemperature: randomBetween(19, 25), cabinPressure: randomBetween(96, 104), heartRate: randomBetween(68, 104),
    bodyTemperature: randomBetween(36.3, 37.4), oxygenSaturation: randomBetween(94, 100),
  }
}

export function advanceTelemetry(current) {
  return {
    oxygen: round(Math.max(0, current.oxygen - randomBetween(1, 4))),
    battery: round(Math.max(0, current.battery - randomBetween(0.5, 2.5))),
    fuel: round(Math.max(0, current.fuel - randomBetween(1, 3.5))),
    cabinTemperature: round(clamp(current.cabinTemperature + randomBetween(-1.2, 1.2), 10, 39)),
    cabinPressure: round(clamp(current.cabinPressure + randomBetween(-2.5, 2.5), 65, 125)),
    heartRate: round(clamp(current.heartRate + randomBetween(-5, 7), 45, 150)),
    bodyTemperature: round(clamp(current.bodyTemperature + randomBetween(-0.2, 0.3), 35, 39)),
    oxygenSaturation: round(clamp(current.oxygenSaturation - randomBetween(0, 1.5), 75, 100)),
  }
}

export function telemetryStatus(key, value) {
  const bands = {
    oxygen: [40, 70], battery: [15, 40], fuel: [10, 25], oxygenSaturation: [85, 92],
  }
  if (bands[key]) return value < bands[key][0] ? 'CRITICAL' : value < bands[key][1] ? 'WARNING' : 'NORMAL'
  if (key === 'cabinTemperature' || key === 'bodyTemperature') {
    return value < 14 || value > 32 ? 'CRITICAL' : value < 18 || value > 28 ? 'WARNING' : 'NORMAL'
  }
  if (key === 'cabinPressure') return value < 75 || value > 120 ? 'CRITICAL' : value < 90 || value > 110 ? 'WARNING' : 'NORMAL'
  return 'NORMAL'
}

export function evaluateEmergency(scenario, action) {
  const correct = action === correctActions[scenario]
  return { correct, message: correct ? 'Correct response. The immediate hazard is controlled and the crew can continue safely.' : `That action increases mission risk. The safer first response is: ${correctActions[scenario]}.` }
}

export function evaluateLaunch(fuel, checks) {
  const missing = Object.entries(checks).filter(([, done]) => !done).map(([label]) => label)
  if (fuel < 25) return { success: false, message: 'Launch scrubbed: fuel reserve is below the 25% minimum.' }
  if (missing.length) return { success: false, message: `Launch scrubbed: complete ${missing.join(', ')}.` }
  return { success: true, message: 'All systems nominal. Launch sequence authorized.' }
}

export function evaluateEva({ repaired, kitCollected, tethered, oxygen }) {
  if (!tethered) return { success: false, message: 'EVA terminated: safety tether was not secured.' }
  if (oxygen <= 0) return { success: false, message: 'EVA terminated: suit oxygen reserve depleted.' }
  if (repaired && kitCollected) return { success: true, message: 'Satellite repair complete and replacement kit secured.' }
  return { success: false, message: 'EVA incomplete: repair and equipment collection are both required.' }
}

export function communicationReport(body) {
  return body.trim().length >= 20 && /(status|systems|mission|oxygen|repair)/i.test(body)
}

function randomBetween(min, max) { return round(min + Math.random() * (max - min)) }
function round(value) { return Math.round(value * 10) / 10 }
function clamp(value, min, max) { return Math.min(max, Math.max(min, value)) }