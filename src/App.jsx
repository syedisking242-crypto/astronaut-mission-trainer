import { useEffect, useRef, useState } from 'react'
import {
  advanceTelemetry, campaignFor, communicationReport, dashboardFor, emergencies, evaluateEmergency,
  evaluateEva, evaluateLaunch, makeAstronaut, missions, newTelemetry, saveState, scoreMission,
  telemetryStatus, loadState,
} from './domain.js'

const navItems = [
  ['dashboard', 'Overview', '⌂'], ['registration', 'Crew profiles', '◉'], ['missions', 'Mission manifest', '✳'],
  ['systems', 'Spacecraft systems', '⌁'], ['health', 'Crew health', '♡'], ['emergency', 'Emergency response', '!'],
  ['eva', 'Spacewalk EVA', '⌖'], ['communications', 'Communications', '↗'], ['assessment', 'Flight record', '▤'],
]
const checklistLabels = ['Flight plan verified', 'Crew restraints secured', 'Communications check complete']
const telemetryFields = [
  ['oxygen', 'Oxygen reserve', '%'], ['battery', 'Battery', '%'], ['fuel', 'Fuel reserve', '%'],
  ['cabinTemperature', 'Cabin temperature', '°C'], ['cabinPressure', 'Cabin pressure', 'kPa'],
]

export default function App() {
  const [state, setState] = useState(loadState)
  const [page, setPage] = useState('dashboard')
  const [telemetry, setTelemetry] = useState(newTelemetry)
  const [dialog, setDialog] = useState(null)
  const [notice, setNotice] = useState('')
  const active = state.astronauts.find((person) => person.id === state.activeId) || null

  useEffect(() => saveState(state), [state])
  useEffect(() => {
    if (!notice) return undefined
    const timer = window.setTimeout(() => setNotice(''), 4500)
    return () => window.clearTimeout(timer)
  }, [notice])

  function patchState(updater) {
    setState((current) => typeof updater === 'function' ? updater(current) : { ...current, ...updater })
  }
  function selectAstronaut(id) {
    patchState((current) => ({ ...current, activeId: id }))
  }
  function signOut() {
    selectAstronaut(null)
    setPage('dashboard')
    setNotice('You are signed out. Your crew profile and flight record are saved on this device.')
  }
  function signIn(id) {
    const person = state.astronauts.find((astronaut) => astronaut.id === id)
    selectAstronaut(id)
    setPage('dashboard')
    if (person) setNotice(`Welcome back, ${person.name}.`)
  }
  function addTelemetry(values = telemetry) {
    if (!active) return
    patchState((current) => ({ ...current, telemetry: [...current.telemetry, { astronautId: active.id, values, recordedAt: new Date().toISOString() }].slice(-300) }))
  }
  function completeMission(missionId, success, completion, startedAt, mistakes, details) {
    if (!active) return
    const record = {
      id: crypto.randomUUID(), astronautId: active.id, missionId, status: success ? 'completed' : 'failed',
      score: scoreMission(missionId, success, completion, mistakes), completion, responseSeconds: (Date.now() - startedAt) / 1000,
      mistakes, details, completedAt: new Date().toISOString(),
    }
    patchState((current) => ({ ...current, records: [...current.records, record] }))
    setPage('assessment')
    setNotice(`${success ? 'Mission complete' : 'Mission incomplete'} · ${record.score} points · ${completion}% completion`)
  }
  function openMission(mission) {
    if (!active) {
      setPage('registration')
      return
    }
    if (!campaignFor(state, active.id).unlocked.has(mission.id)) {
      setNotice('Mission locked. Complete the previous campaign mission to continue.')
      return
    }
    setDialog(mission)
  }
  function navigatePage(nextPage) {
    const missionPageIds = { navigation: 'navigation', emergency: 'emergency', eva: 'eva', communications: 'communication' }
    const requiredMission = missionPageIds[nextPage]
    if (requiredMission && active && !campaignFor(state, active.id).unlocked.has(requiredMission)) {
      setNotice('Mission locked. Complete the previous campaign mission to continue.')
      setPage('missions')
      return
    }
    setPage(nextPage)
  }
  function launchMission(mission) {
    setDialog(null)
    if (mission.id === 'launch') { setPage('systems'); setDialog({ id: 'launch-checklist', name: 'Launch Readiness' }) }
    else setPage(mission.id === 'navigation' ? 'navigation' : mission.id === 'emergency' ? 'emergency' : mission.id === 'eva' ? 'eva' : 'communications')
  }

  const dashboard = active ? dashboardFor(state, active.id) : null
  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#overview" onClick={(event) => { event.preventDefault(); setPage('dashboard') }}>
        <span className="brand-mark">✳</span><span><strong>ORBITAL<br />ACADEMY</strong><small>JUNIOR ASTRONAUT TRAINER</small></span>
      </a>
      <div className="nav-caption">MISSION CONTROL</div>
      <nav className="nav-list" aria-label="Main navigation">
        {navItems.map(([id, label, icon]) => <button key={id} className={`nav-item ${page === id ? 'selected' : ''}`} onClick={() => navigatePage(id)}>
          <span className="nav-icon">{icon}</span><span>{label}</span>{id === 'missions' && <span className="nav-count">05</span>}
        </button>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="connection"><span className="live-dot" /> LOCAL FLIGHT RECORD</div>
        <div className="active-crew"><span className="crew-avatar">{active?.name?.slice(0, 1) || '·'}</span><span><b>{active?.name || 'No crew selected'}</b><small>{active?.id || 'Register a profile'}</small></span></div>
      </div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="breadcrumb"><span>FLIGHT OPERATIONS</span><b>/</b><strong>{navItems.find(([id]) => id === page)?.[1] || 'Orbital Navigation'}</strong></div>
        <div className="topbar-right"><span className="date-stamp">SIMULATION ENVIRONMENT <i /> ALL SYSTEMS NOMINAL</span>
          {active && state.astronauts.length > 1 && <select aria-label="Active astronaut" value={active.id} onChange={(event) => selectAstronaut(event.target.value)}>{state.astronauts.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select>}
          {active
            ? <button className="button button-outline" onClick={signOut}>Log out</button>
            : <button className="button button-cyan" onClick={() => setPage('registration')}>Log in</button>}
        </div>
      </header>
      {notice && <div className="toast" role="status">{notice}<button onClick={() => setNotice('')} aria-label="Dismiss message">×</button></div>}
      <div className="content-area">
        {page === 'dashboard' && <Dashboard active={active} data={dashboard} state={state} onNavigate={setPage} onMission={openMission} />}
        {page === 'registration' && <Registration state={state} onCreate={(person) => { patchState((current) => ({ ...current, astronauts: [...current.astronauts, person], activeId: person.id })); setPage('dashboard'); setNotice(`${person.name} cleared for training · ${person.id}`) }} onSelect={signIn} />}
        {page === 'missions' && <MissionManifest active={active} state={state} onMission={openMission} />}
        {page === 'systems' && <Systems telemetry={telemetry} onSample={() => { const updated = advanceTelemetry(telemetry); setTelemetry(updated); addTelemetry(updated) }} onLaunch={() => setDialog({ id: 'launch-checklist', name: 'Launch Readiness' })} />}
        {page === 'health' && <Health state={state} active={active} telemetry={telemetry} onRefresh={() => { const values = newTelemetry(); setTelemetry(values); addTelemetry(values) }} />}
        {page === 'emergency' && (active ? <Emergency onComplete={(success, details, startedAt) => completeMission('emergency', success, success ? 100 : 55, startedAt, success ? 0 : 1, details)} /> : <CrewRequired onRegister={() => setPage('registration')} />)}
        {page === 'eva' && (active ? <Eva onComplete={(success, details, startedAt) => completeMission('eva', success, success ? 100 : 50, startedAt, success ? 0 : 1, details)} /> : <CrewRequired onRegister={() => setPage('registration')} />)}
        {page === 'communications' && (active ? <Communications state={state} active={active} onSend={(items) => patchState((current) => ({ ...current, messages: [...current.messages, ...items] }))} onComplete={(success, details, started) => completeMission('communication', success, success ? 100 : 55, started, success ? 0 : 1, details)} /> : <CrewRequired onRegister={() => setPage('registration')} />)}
        {page === 'assessment' && (active ? <Assessment state={state} active={active} onCertificate={() => downloadCertificate(active, state.records.filter((row) => row.astronautId === active.id).at(-1))} /> : <CrewRequired onRegister={() => setPage('registration')} />)}
        {page === 'navigation' && (active ? <NavigationGame onComplete={(success, completion, details, started) => completeMission('navigation', success, completion, started, success ? 0 : 1, details)} onExit={() => setPage('missions')} /> : <CrewRequired onRegister={() => setPage('registration')} />)}
      </div>
    </main>

    {dialog?.id === 'launch-checklist' && <LaunchModal fuel={telemetry.fuel} onClose={() => setDialog(null)} onSubmit={(checks) => {
      const started = Date.now()
      const result = evaluateLaunch(telemetry.fuel, checks)
      setDialog(null)
      if (!result.success) { completeMission('launch', false, 40, started, 1, { reason: result.message }); return }
      setNotice('Countdown initiated · T-minus 3')
      window.setTimeout(() => setNotice('Liftoff confirmed · Engine status nominal'), 2550)
      window.setTimeout(() => completeMission('launch', true, 100, started, 0, { fuel: telemetry.fuel }), 3400)
    }} />}
    {dialog && dialog.id !== 'launch-checklist' && <MissionBriefing mission={dialog} onClose={() => setDialog(null)} onStart={() => launchMission(dialog)} />}
  </div>
}

function PageHeading({ eyebrow, title, subtitle, action }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{action}</div>
}

function CrewRequired({ onRegister }) {
  return <section className="section-panel empty-state"><span>◉</span><h2>Register an astronaut first.</h2><p>A crew profile is required to begin a mission and save its flight record.</p><button className="button button-cyan" onClick={onRegister}>Open crew registration <span>↗</span></button></section>
}

function Dashboard({ active, data, state, onNavigate, onMission }) {
  const campaign = active ? campaignFor(state, active.id) : { completed: new Set(), unlocked: new Set(['launch']) }
  const completion = data ? Math.round(data.completed / missions.length * 100) : 0
  return <>
    <PageHeading eyebrow="MISSION CONTROL / TRAINING OVERVIEW" title={<>Welcome aboard{active ? `, ${active.name.split(' ')[0]}` : ''}<span className="title-period">.</span></>} subtitle="Your flight record, mission readiness, and crew status in one place." action={<div className="orbit-status"><span className="live-dot" /> SIMULATION LIVE</div>} />
    {!active ? <section className="welcome-panel"><div className="welcome-copy"><div className="eyebrow">CADET INTAKE OPEN</div><h2>Your flight record<br />starts here.</h2><p>Create a crew profile to unlock mission control and save your training results on this device.</p><button className="button button-cyan" onClick={() => onNavigate('registration')}>Create astronaut profile <span>↗</span></button></div><AstronautArt /></section> : <>
      <section className="stat-grid">
        <Stat label="MISSIONS CLEARED" value={`${data.completed} / ${missions.length}`} accent="cyan" note={`${Math.max(0, missions.length - data.completed)} remaining`} />
        <Stat label="TRAINING SCORE" value={data.score.toLocaleString()} accent="green" note="TOTAL POINTS EARNED" />
        <Stat label="MISSION ATTEMPTS" value={data.attempts} accent="amber" note="INCLUDING RE-TRIES" />
        <div className="stat-card progress-stat"><div className="stat-label">CAMPAIGN PROGRESS</div><div className="stat-row"><strong>{completion}<small>%</small></strong><span>{data.completed}/{missions.length} missions</span></div><div className="progress-track"><i style={{ width: `${completion}%` }} /></div></div>
      </section>
      <section className="dashboard-grid">
        <div className="section-panel manifest-panel"><div className="panel-heading"><div><div className="eyebrow">FLIGHT PLAN</div><h2>Mission manifest</h2></div><button className="text-button" onClick={() => onNavigate('missions')}>All missions <span>↗</span></button></div>
          <div className="mini-missions">{missions.map((mission, index) => {
            const cleared = campaign.completed.has(mission.id), unlocked = campaign.unlocked.has(mission.id)
            return <button key={mission.id} className={`mini-mission ${unlocked ? '' : 'is-locked'}`} onClick={() => unlocked && onMission(mission)}>
              <span className={`mission-index ${cleared ? 'done' : ''}`}>{cleared ? '✓' : `0${index + 1}`}</span><span className="mission-name"><b>{mission.name}</b><small>{mission.category}</small></span><span className={`mission-state ${cleared ? 'green' : unlocked ? 'cyan' : ''}`}>{cleared ? 'CLEARED' : unlocked ? 'READY' : 'LOCKED'}</span><span className="row-arrow">{unlocked ? '↗' : '⌑'}</span>
            </button>
          })}</div>
        </div>
        <div className="section-panel profile-panel"><div className="profile-top"><div className="eyebrow">FLIGHT PROFILE</div><span className="profile-seal">✳</span></div><div className="profile-name">{active.name}</div><div className="profile-id">{active.id}</div><div className="profile-divider" />
          <ProfileField label="TRAINING LEVEL" value={active.trainingLevel} /><ProfileField label="AGE" value={`${active.age} years`} /><ProfileField label="ACHIEVEMENT" value={data.completed === missions.length ? 'Mission Specialist' : data.completed ? 'First Orbit' : 'Awaiting first mission'} accent />
          <button className="button button-outline" onClick={() => onNavigate('missions')}>Continue training <span>→</span></button>
        </div>
      </section>
      <section className="lower-strip"><div className="lower-copy"><span className="sun-mark">✦</span><span><b>Training note</b><small>Each mission unlocks after successful completion of the one before it.</small></span></div><button className="text-button" onClick={() => onNavigate('assessment')}>View flight record <span>↗</span></button></section>
    </>}
  </>
}

function Stat({ label, value, note, accent }) {
  return <div className={`stat-card accent-${accent}`}><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-note"><span className="tiny-dot" />{note}</div></div>
}
function ProfileField({ label, value, accent }) { return <div className="profile-field"><small>{label}</small><b className={accent ? 'accent-text' : ''}>{value}</b></div> }
function AstronautArt() { return <div className="astronaut-art" aria-label="Illustration of an astronaut drifting in orbit"><div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" /><div className="art-planet" /><div className="astronaut"><div className="helmet"><div className="visor" /></div><div className="neck" /><div className="suit"><i /><b>✳</b></div><div className="arm arm-left" /><div className="arm arm-right" /><div className="leg leg-left" /><div className="leg leg-right" /></div><span className="art-star star-one">✦</span><span className="art-star star-two">·</span><span className="art-star star-three">✧</span></div> }

function Registration({ state, onCreate, onSelect }) {
  const [form, setForm] = useState({ name: '', age: '', profile: '', trainingLevel: 'Cadet', missionId: 'launch' })
  const [error, setError] = useState('')
  function submit(event) {
    event.preventDefault()
    try { onCreate(makeAstronaut(form)) } catch (reason) { setError(reason.message) }
  }
  return <><PageHeading eyebrow="CREW SERVICES / CADET INTAKE" title="Astronaut registration" subtitle="Create a local training profile. Records stay in this browser." />
    <div className="registration-layout"><form className="section-panel registration-form" onSubmit={submit}><div className="panel-heading"><div><div className="eyebrow">NEW FLIGHT CREDENTIALS</div><h2>Build your crew profile</h2></div><span className="form-ornament">01</span></div>
      <label className="field-label">ASTRONAUT NAME<input required minLength="2" maxLength="60" value={form.name} placeholder="e.g. Ari Orbit" onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
      <label className="field-label">AGE<input required type="number" min="6" max="45" value={form.age} placeholder="6–45" onChange={(event) => setForm({ ...form, age: event.target.value })} /></label>
      <label className="field-label">FLIGHT PROFILE<textarea maxLength="500" rows="3" value={form.profile} placeholder="A few words about this astronaut" onChange={(event) => setForm({ ...form, profile: event.target.value })} /></label>
      <div className="form-row"><label className="field-label">TRAINING LEVEL<select value={form.trainingLevel} onChange={(event) => setForm({ ...form, trainingLevel: event.target.value })}><option>Cadet</option><option>Explorer</option><option>Commander</option></select></label>
        <label className="field-label">INITIAL MISSION<select value={form.missionId} onChange={(event) => setForm({ ...form, missionId: event.target.value })}>{missions.map((mission) => <option key={mission.id} value={mission.id}>{mission.name}</option>)}</select></label></div>
      {error && <div className="form-error" role="alert">{error}</div>}<button className="button button-cyan submit-button">Save astronaut profile <span>↗</span></button>
    </form><div className="registration-aside"><div className="section-panel intake-panel"><div className="eyebrow">INTAKE PARAMETERS</div><h3>One profile.<br />A whole flight log.</h3><div className="intake-rule" /><p>Sign in to a saved crew profile to continue its training. Profiles and mission results stay on this device.</p><div className="intake-stamp">LOCAL<br />RECORD</div></div>
      {state.astronauts.length > 0 && <div className="section-panel existing-panel"><div className="panel-heading"><div><div className="eyebrow">SIGN IN / SAVED CREW</div><h2>Choose a profile</h2></div></div>{state.astronauts.map((person) => <button className="existing-person" key={person.id} onClick={() => onSelect(person.id)}><span className="crew-avatar">{person.name[0]}</span><span><b>{person.name}</b><small>{person.id} · {person.trainingLevel}</small></span><span className="row-arrow">↗</span></button>)}</div>}</div></div>
  </>
}

function MissionManifest({ active, state, onMission }) {
  const campaign = active ? campaignFor(state, active.id) : { completed: new Set(), unlocked: new Set(['launch']) }
  return <><PageHeading eyebrow="FLIGHT OPERATIONS / CAMPAIGN" title="Mission control" subtitle={active ? `${active.name} · Select an available training operation.` : 'Register or select an astronaut to begin the campaign.'} />
    <div className="manifest-list">{missions.map((mission, index) => {
      const cleared = campaign.completed.has(mission.id), unlocked = campaign.unlocked.has(mission.id)
      return <article className={`manifest-card ${!unlocked ? 'locked' : ''}`} key={mission.id}><div className={`manifest-number ${cleared ? 'done' : ''}`}>{cleared ? '✓' : `0${index + 1}`}</div><div className="manifest-info"><div className="eyebrow">{mission.category}</div><h2>{mission.name}</h2><p>{mission.description}</p></div><div className={`manifest-status ${cleared ? 'green' : unlocked ? 'cyan' : ''}`}>{cleared ? 'CLEARED' : unlocked ? 'AVAILABLE' : 'LOCKED'}</div><button className={`button ${unlocked ? 'button-cyan' : 'button-disabled'}`} disabled={!unlocked || !active} onClick={() => onMission(mission)}>{cleared ? 'Replay mission' : unlocked ? 'Brief mission' : 'Locked'} <span>{unlocked ? '↗' : '⌑'}</span></button></article>
    })}</div>
  </>
}

function MissionBriefing({ mission, onClose, onStart }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="briefing-modal" role="dialog" aria-modal="true" aria-labelledby="briefing-title"><button className="modal-close" aria-label="Close briefing" onClick={onClose}>×</button><div className="eyebrow">MISSION BRIEFING / {mission.category.toUpperCase()}</div><h2 id="briefing-title">{mission.name}</h2><p className="briefing-description">{mission.description}</p><div className="briefing-objective"><small>OBJECTIVE</small><p>{briefFor(mission.id).objective}</p></div><div className="briefing-facts"><div><small>MISSION PLAN</small><p>{briefFor(mission.id).instructions}</p></div><div><small>SUCCESS CONDITION</small><p>{briefFor(mission.id).success}</p></div></div><div className="modal-actions"><button className="button button-quiet" onClick={onClose}>Cancel</button><button className="button button-cyan" onClick={onStart}>Start mission <span>↗</span></button></div></section></div>
}
function briefFor(id) {
  return {
    launch: { objective: 'Prepare the spacecraft and reach a safe liftoff.', instructions: 'Verify each pre-launch item and check the simulated fuel reserve.', success: 'Fuel is at least 25% and all three checklist items are complete.' },
    navigation: { objective: 'Pilot to the orbital beacon while avoiding asteroids.', instructions: 'Steer through the field; three collision alerts end the attempt.', success: 'Reach the cyan beacon at the top of the flight area.' },
    emergency: { objective: 'Choose the safest first response to a spacecraft emergency.', instructions: 'Read the alert, compare the actions, then submit one response.', success: 'Select the correct immediate action for the emergency.' },
    eva: { objective: 'Repair the satellite and collect its replacement equipment.', instructions: 'Keep the safety tether secured and monitor suit oxygen.', success: 'Secure tether, remaining oxygen, repair, and equipment collection.' },
    communication: { objective: 'Send a clear spacecraft status report to mission control.', instructions: 'Include mission-relevant detail; mission control replies after a simulated delay.', success: 'At least 20 characters and a relevant status, systems, mission, oxygen, or repair detail.' },
  }[id]
}

function LaunchModal({ fuel, onClose, onSubmit }) {
  const [checks, setChecks] = useState(Object.fromEntries(checklistLabels.map((label) => [label, false])))
  return <div className="modal-backdrop"><section className="briefing-modal launch-modal" role="dialog" aria-modal="true"><button className="modal-close" aria-label="Close checklist" onClick={onClose}>×</button><div className="eyebrow">FLIGHT OPERATIONS / FINAL CHECK</div><h2>Pre-launch checklist</h2><p className="briefing-description">Verify the crew and spacecraft before authorizing liftoff.</p><div className="fuel-readout"><span>SIMULATED FUEL RESERVE</span><b className={fuel < 25 ? 'critical-text' : ''}>{fuel}<small>%</small></b><small>25% minimum</small></div><div className="checklist">{checklistLabels.map((label) => <label key={label} className="check-row"><input type="checkbox" checked={checks[label]} onChange={(event) => setChecks({ ...checks, [label]: event.target.checked })} /><span className="custom-check">✓</span>{label}</label>)}</div><div className="modal-actions"><button className="button button-quiet" onClick={onClose}>Cancel</button><button className="button button-cyan" onClick={() => onSubmit(checks)}>Begin countdown <span>↗</span></button></div></section></div>
}

function Systems({ telemetry, onSample, onLaunch }) {
  return <><PageHeading eyebrow="FLIGHT OPERATIONS / LIVE TELEMETRY" title="Spacecraft systems" subtitle="Simulated flight telemetry. Each sample advances system conditions." action={<button className="button button-cyan" onClick={onSample}>↻ <span>Sample systems</span></button>} />
    <div className="telemetry-grid">{telemetryFields.map(([key, label, unit]) => <TelemetryCard key={key} label={label} value={telemetry[key]} unit={unit} status={telemetryStatus(key, telemetry[key])} />)}</div>
    <section className="section-panel system-footer"><div><div className="eyebrow">FLIGHT OPERATIONS</div><h2>Launch sequence</h2><p>Verify the crew checklist and current simulated fuel reserve to begin countdown.</p></div><button className="button button-outline" onClick={onLaunch}>Open launch checklist <span>→</span></button></section>
    <p className="disclaimer">All spacecraft values are simulated for training. No physical systems are connected.</p>
  </>
}
function TelemetryCard({ label, value, unit, status }) { return <article className={`telemetry-card status-${status.toLowerCase()}`}><div className="telemetry-label">{label}</div><div className="telemetry-value">{value}<small>{unit}</small></div><div className="telemetry-bottom"><span className="telemetry-bar"><i style={{ width: `${Math.min(100, Math.max(4, value))}%` }} /></span><span>{status}</span></div></article> }

function Health({ state, active, telemetry, onRefresh }) {
  const entries = active ? state.telemetry.filter((row) => row.astronautId === active.id).slice(-20) : []
  const values = [['Heart rate', telemetry.heartRate, 'bpm', 55, 120], ['Body temperature', telemetry.bodyTemperature, '°C', 36, 38], ['Oxygen saturation', telemetry.oxygenSaturation, '%', 92, 100]]
  return <><PageHeading eyebrow="CREW SERVICES / WELLNESS MONITOR" title="Crew health" subtitle="Simulated wellness readings and recent training history." action={<button className="button button-cyan" onClick={onRefresh}>↻ <span>New reading</span></button>} />
    <div className="health-cards">{values.map(([label, value, unit, low, high]) => <div key={label} className={`health-reading ${value >= low && value <= high ? 'nominal' : 'monitor'}`}><div className="eyebrow">{label.toUpperCase()}</div><strong>{value}<small>{unit}</small></strong><span><i className="tiny-dot" />{value >= low && value <= high ? 'NOMINAL' : 'MONITOR'}</span></div>)}</div>
    <section className="section-panel chart-panel"><div className="panel-heading"><div><div className="eyebrow">RECENT SIMULATED READINGS</div><h2>Health history</h2></div><span className="chart-legend"><i />Heart rate <i className="legend-green" />Oxygen saturation</span></div>
      {entries.length < 2 ? <div className="empty-chart">Take another reading to build a history graph.</div> : <HealthChart entries={entries} />}
    </section><p className="disclaimer">This is a fictional simulation, not a medical device or source of medical advice.</p>
  </>
}
function HealthChart({ entries }) {
  const heart = entries.map((entry) => entry.values.heartRate), oxygen = entries.map((entry) => entry.values.oxygenSaturation)
  const width = 780, height = 220, pad = 24
  const point = (values, index) => `${pad + index * (width - pad * 2) / Math.max(1, values.length - 1)},${height - pad - (values[index] - 50) / 80 * (height - pad * 2)}`
  return <svg className="health-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Heart rate and oxygen saturation history"><path className="chart-gridline" d={`M${pad} 50H${width - pad} M${pad} 105H${width - pad} M${pad} 160H${width - pad}`} /><polyline points={heart.map(point.bind(null, heart)).join(' ')} className="chart-heart" /><polyline points={oxygen.map(point.bind(null, oxygen)).join(' ')} className="chart-oxygen" /><text x="24" y="18">RECENT SAMPLES</text></svg>
}

function Emergency({ onComplete }) {
  const [scenario, setScenario] = useState(Object.keys(emergencies)[0]), [action, setAction] = useState(''), [feedback, setFeedback] = useState(null), [startedAt] = useState(Date.now())
  function submit() { if (!action) { setFeedback({ correct: false, message: 'Select a corrective action before submitting.' }); return } const result = evaluateEmergency(scenario, action); setFeedback(result); window.setTimeout(() => onComplete(result.correct, { scenario, action }, startedAt), 1800) }
  return <><PageHeading eyebrow="FLIGHT OPERATIONS / SYSTEMS" title="Emergency response" subtitle="Assess the alert and select the safest immediate corrective action." />
    <div className="decision-layout"><section className="section-panel decision-panel"><div className="eyebrow">ACTIVE ALERT</div><label className="field-label">SCENARIO<select value={scenario} onChange={(event) => { setScenario(event.target.value); setAction(''); setFeedback(null) }}>{Object.keys(emergencies).map((item) => <option key={item}>{item}</option>)}</select></label><div className="alert-banner"><span>!</span><div><b>{scenario}</b><small>Immediate crew response required. Select your first action.</small></div></div>
      <div className="eyebrow action-eyebrow">AVAILABLE ACTIONS</div><div className="choice-list">{emergencies[scenario].map((choice, index) => <label className={`choice-row ${action === choice ? 'chosen' : ''}`} key={choice}><input type="radio" name="emergency" value={choice} checked={action === choice} onChange={() => { setAction(choice); setFeedback(null) }} /><span className="choice-index">0{index + 1}</span><b>{choice}</b><span className="choice-radio" /></label>)}</div>
      {feedback && <div className={`feedback-box ${feedback.correct ? 'success' : 'failure'}`}>{feedback.message}</div>}<button className="button button-cyan" onClick={submit}>Submit corrective action <span>↗</span></button></section>
      <aside className="section-panel decision-aside"><div className="eyebrow">RESPONSE PROTOCOL</div><h2>Pause.<br />Assess.<br /><em>Act.</em></h2><div className="intake-rule" /><p>In a spacecraft emergency, the first action should control the immediate hazard while keeping crew and mission safety in view.</p><div className="aside-orbit">✳</div></aside></div>
  </>
}

function Eva({ onComplete }) {
  const [oxygen, setOxygen] = useState(100), [tethered, setTethered] = useState(true), [repaired, setRepaired] = useState(false), [kit, setKit] = useState(false), [startedAt] = useState(Date.now())
  const [feedback, setFeedback] = useState('')
  function work() { if (!tethered) { setFeedback('Secure your safety tether before performing EVA tasks.'); return } if (oxygen <= 0) { setFeedback('Suit oxygen depleted. End the spacewalk.'); return } setOxygen((current) => Math.max(0, current - (10 + Math.floor(Math.random() * 9)))); setFeedback('Task logged. Suit oxygen reserve updated.') }
  function finish() { const result = evaluateEva({ repaired, kitCollected: kit, tethered, oxygen }); setFeedback(result.message); window.setTimeout(() => onComplete(result.success, { oxygenRemaining: oxygen, tethered, repaired, kitCollected: kit }, startedAt), 1600) }
  return <><PageHeading eyebrow="FLIGHT OPERATIONS / EXTRAVEHICULAR ACTIVITY" title="Spacewalk EVA" subtitle="Satellite service task. Track your safety tether and suit oxygen." />
    <div className="eva-layout"><section className="section-panel eva-panel"><div className="eva-top"><div><div className="eyebrow">SUIT TELEMETRY</div><h2>Outside the airlock</h2></div><div className={`oxygen-gauge ${oxygen < 30 ? 'low' : ''}`}><span>SUIT OXYGEN</span><b>{oxygen}<small>%</small></b><i><em style={{ width: `${oxygen}%` }} /></i></div></div>
      <label className="toggle-row"><span className="toggle-symbol">⌖</span><span><b>Safety tether secured</b><small>Required for all EVA work.</small></span><input type="checkbox" checked={tethered} onChange={(event) => setTethered(event.target.checked)} /></label>
      <label className="toggle-row"><span className={`task-check ${repaired ? 'checked' : ''}`}>{repaired ? '✓' : '01'}</span><span><b>Satellite repair completed</b><small>Restore the damaged communications array.</small></span><input type="checkbox" checked={repaired} onChange={(event) => setRepaired(event.target.checked)} /></label>
      <label className="toggle-row"><span className={`task-check ${kit ? 'checked' : ''}`}>{kit ? '✓' : '02'}</span><span><b>Replacement equipment collected</b><small>Secure the repair kit for return to the airlock.</small></span><input type="checkbox" checked={kit} onChange={(event) => setKit(event.target.checked)} /></label>
      {feedback && <div className="feedback-box">{feedback}</div>}<div className="eva-actions"><button className="button button-outline" onClick={work} disabled={oxygen <= 0}>Perform EVA task <span>⌖</span></button><button className="button button-cyan" onClick={finish}>End spacewalk <span>↗</span></button></div></section>
      <aside className="eva-visual"><div className="eva-planet" /><div className="eva-ring" /><div className="eva-astronaut"><span>◉</span><b>✳</b></div><div className="eva-caption"><span className="live-dot" /> EVA IN PROGRESS<small>ORBITAL SERVICE ZONE 04</small></div></aside></div>
  </>
}

function Communications({ state, active, onSend, onComplete }) {
  const [body, setBody] = useState('Mission status: all systems nominal. Crew ready to proceed.'), [sending, setSending] = useState(false)
  const [signal] = useState(() => 58 + Math.floor(Math.random() * 42)), [delay] = useState(() => +(1.2 + Math.random() * 7.3).toFixed(1))
  const missionStartedAt = useRef(Date.now())
  const [messages, setMessages] = useState([])
  const transcript = active ? state.messages.filter((item) => item.astronautId === active.id) : messages
  function transmit(event) {
    event.preventDefault()
    if (!body.trim() || sending) return
    const good = communicationReport(body), sentAt = new Date().toISOString()
    setSending(true)
    const outgoing = { id: crypto.randomUUID(), astronautId: active.id, direction: 'astronaut_to_earth', body: body.trim(), signal, delay, sentAt }
    const replyBody = good ? 'Copy, astronaut. Systems are green. Continue to the next mission objective.' : 'Mission control requests a clear status report with systems or mission details.'
    setMessages((current) => [...current, outgoing])
    onSend([outgoing])
    window.setTimeout(() => {
      const reply = { id: crypto.randomUUID(), astronautId: active.id, direction: 'earth_to_astronaut', body: replyBody, signal, delay, sentAt: new Date().toISOString() }
      setMessages((current) => [...current, reply]); onSend([reply]); setSending(false)
      onComplete(good, { signal, delay, reportClear: good }, missionStartedAt.current)
    }, delay * 1000)
  }
  return <><PageHeading eyebrow="FLIGHT OPERATIONS / RADIO LINK" title="Earth communications" subtitle="Compose a status report. Mission control replies after the simulated transmission delay." />
    <div className="comms-layout"><section className="section-panel comms-panel"><div className="radio-readout"><div><small>SIGNAL STRENGTH</small><b>{signal}<i>%</i></b><div className="signal-bars"><i /><i /><i /><i /><i /></div></div><div className="radio-separator" /><div><small>ONE-WAY DELAY</small><b>{delay}<i>sec</i></b><span>EARTH ↔ ORBIT</span></div><div className="radio-wave">∿ ∿ ∿</div></div>
      <div className="transcript-label"><span className="live-dot" /> TRANSMISSION LOG <small>{transcript.length} MESSAGES</small></div><div className="transcript" aria-live="polite">{transcript.length === 0 ? <div className="transcript-empty">Your radio log is clear.<br />Transmit a status report to begin.</div> : transcript.map((item) => <div className={`message ${item.direction === 'earth_to_astronaut' ? 'incoming' : ''}`} key={item.id}><small>{item.direction === 'earth_to_astronaut' ? 'MISSION CONTROL' : 'TO EARTH'} <i>·</i> {new Date(item.sentAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small><p>{item.body}</p></div>)}{sending && <div className="signal-pending"><span className="pulse-dot" /> SIGNAL SENT · EARTH REPLY ARRIVING IN {delay}s...</div>}</div>
      <form className="transmit-form" onSubmit={transmit}><label className="field-label">OUTGOING TRANSMISSION<textarea maxLength="500" value={body} onChange={(event) => setBody(event.target.value)} rows="3" /></label><div className="transmit-bottom"><small>{body.length}/500 · Include a mission or systems detail</small><button className="button button-cyan" disabled={sending}> {sending ? 'Transmitting…' : 'Transmit to mission control'} <span>↗</span></button></div></form>
    </section><aside className="section-panel comms-aside"><div className="eyebrow">RADIO PROTOCOL</div><h2>Clear signal.<br />Clear status.</h2><p>A useful report is at least 20 characters and includes a relevant detail: status, systems, mission, oxygen, or repair.</p><div className="waveform"><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /></div><span className="aside-frequency">118.7 MHz <i>SIMULATED</i></span></aside></div>
  </>
}

function Assessment({ state, active, onCertificate }) {
  const history = active ? state.records.filter((record) => record.astronautId === active.id).slice().reverse() : []
  return <><PageHeading eyebrow="CREW SERVICES / FLIGHT RECORD" title="Mission assessment" subtitle="Append-only training history and scored mission attempts." action={history.length > 0 && <button className="button button-outline" onClick={onCertificate}>Export certificate <span>↓</span></button>} />
    {history.length === 0 ? <div className="section-panel empty-state"><span>▤</span><h2>No mission attempts recorded.</h2><p>Complete a mission to see scores, outcomes, and your flight record here.</p></div> : <section className="section-panel history-panel"><div className="history-header"><span>MISSION / DATE</span><span>RESULT</span><span>SCORE</span><span>COMPLETION</span><span>TIME</span><span>ERRORS</span></div>{history.map((record) => <div className="history-row" key={record.id}><div><b>{missions.find((mission) => mission.id === record.missionId)?.name}</b><small>{new Date(record.completedAt).toLocaleString()}</small></div><span className={`result-pill ${record.status}`}>{record.status}</span><b>{record.score} pts</b><span>{record.completion}%</span><span>{record.responseSeconds.toFixed(1)}s</span><span>{record.mistakes}</span></div>)}</section>}
  </>
}
function downloadCertificate(active, latest) {
  if (!active || !latest) return
  const mission = missions.find((item) => item.id === latest.missionId)
  const escapeXml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;',
  })[character])
  const issuedOn = new Date(latest.completedAt).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
  const nameFontSize = Math.max(28, Math.min(54, 1100 / (active.name.length * 0.62)))
  const certificate = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="850" viewBox="0 0 1200 850" role="img" aria-labelledby="title description">
  <title id="title">Orbital Academy training certificate for ${escapeXml(active.name)}</title>
  <desc id="description">${escapeXml(latest.status)} result for ${escapeXml(mission?.name || 'Mission training')}, issued ${escapeXml(issuedOn)}.</desc>
  <rect width="1200" height="850" fill="#102535"/>
  <rect x="28" y="28" width="1144" height="794" rx="8" fill="#f8f6ef" stroke="#c6a45a" stroke-width="2"/>
  <rect x="43" y="43" width="1114" height="764" rx="4" fill="none" stroke="#102535" stroke-width="1"/>
  <path d="M75 110h105M1020 110h105M75 740h105M1020 740h105" stroke="#c6a45a" stroke-width="2"/>
  <text x="600" y="112" text-anchor="middle" fill="#217e83" font-family="Arial,sans-serif" font-size="16" font-weight="700" letter-spacing="5">ORBITAL ACADEMY · FLIGHT TRAINING</text>
  <circle cx="600" cy="193" r="44" fill="#102535"/>
  <circle cx="600" cy="193" r="37" fill="none" stroke="#c6a45a" stroke-width="1.5"/>
  <path d="M600 164l8 19 20 1-15 13 5 20-18-11-18 11 5-20-15-13 20-1z" fill="#d8bb73"/>
  <text x="600" y="286" text-anchor="middle" fill="#102535" font-family="Georgia,serif" font-size="43" letter-spacing="3">CERTIFICATE OF ACHIEVEMENT</text>
  <text x="600" y="329" text-anchor="middle" fill="#687780" font-family="Arial,sans-serif" font-size="15" letter-spacing="4">THIS RECOGNITION IS PRESENTED TO</text>
  <text x="600" y="403" text-anchor="middle" fill="#217e83" font-family="Georgia,serif" font-size="${nameFontSize}">${escapeXml(active.name)}</text>
  <path d="M360 426h480" stroke="#c6a45a" stroke-width="1.5"/>
  <text x="600" y="466" text-anchor="middle" fill="#42515a" font-family="Arial,sans-serif" font-size="18">In recognition of participation in a Junior Astronaut Mission Trainer exercise</text>
  <text x="600" y="500" text-anchor="middle" fill="#102535" font-family="Georgia,serif" font-size="26">${escapeXml(mission?.name || 'Mission training')}</text>
  <rect x="330" y="535" width="250" height="82" rx="5" fill="#e9eee9"/>
  <rect x="620" y="535" width="250" height="82" rx="5" fill="#f0eadb"/>
  <text x="455" y="566" text-anchor="middle" fill="#687780" font-family="Arial,sans-serif" font-size="12" font-weight="700" letter-spacing="2">MISSION RESULT</text>
  <text x="455" y="597" text-anchor="middle" fill="#217e83" font-family="Arial,sans-serif" font-size="20" font-weight="700">${escapeXml(latest.status.toUpperCase())}</text>
  <text x="745" y="566" text-anchor="middle" fill="#687780" font-family="Arial,sans-serif" font-size="12" font-weight="700" letter-spacing="2">TRAINING SCORE</text>
  <text x="745" y="597" text-anchor="middle" fill="#102535" font-family="Arial,sans-serif" font-size="20" font-weight="700">${escapeXml(latest.score)} POINTS · ${escapeXml(latest.completion)}%</text>
  <path d="M165 692h240M795 692h240" stroke="#9ba5a5" stroke-width="1"/>
  <text x="285" y="720" text-anchor="middle" fill="#687780" font-family="Arial,sans-serif" font-size="13">${escapeXml(issuedOn)}</text>
  <text x="915" y="720" text-anchor="middle" fill="#687780" font-family="Arial,sans-serif" font-size="13">ASTRONAUT ID · ${escapeXml(active.id)}</text>
  <text x="600" y="776" text-anchor="middle" fill="#217e83" font-family="Arial,sans-serif" font-size="12" font-weight="700" letter-spacing="3">EXPLORE · LEARN · REACH FOR THE STARS</text>
</svg>`
  const link = document.createElement('a')
  const url = URL.createObjectURL(new Blob([certificate], { type: 'image/svg+xml;charset=utf-8' }))
  link.href = url
  link.download = `${active.id}-certificate.svg`
  document.body.append(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function NavigationGame({ onComplete, onExit }) {
  const canvasRef = useRef(null), gameRef = useRef(null), callbackRef = useRef(onComplete), pausedRef = useRef(false)
  const [paused, setPaused] = useState(false), [hits, setHits] = useState(0), [elapsed, setElapsed] = useState(0), [startedAt] = useState(Date.now())
  callbackRef.current = onComplete
  pausedRef.current = paused
  const restart = () => { gameRef.current = createGame(); setHits(0); setElapsed(0); setPaused(false) }
  useEffect(() => { gameRef.current = createGame() }, [])
  useEffect(() => {
    const canvas = canvasRef.current, context = canvas?.getContext('2d')
    if (!canvas || !context) return undefined
    let frame, last = 0, lastDisplayTick = -1
    const keys = new Set()
    const keyDown = (event) => { if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', ' '].includes(event.key)) event.preventDefault(); keys.add(event.key.toLowerCase()); const game = gameRef.current; if (event.key === 'Escape' && game && !game.done) { game.done = true; callbackRef.current(false, Math.max(0, 100 - game.hits * 20), { summary: `${game.hits} collision alert(s), ${game.elapsed.toFixed(1)} seconds`, hits: game.hits }, startedAt) } }
    const keyUp = (event) => keys.delete(event.key.toLowerCase())
    window.addEventListener('keydown', keyDown); window.addEventListener('keyup', keyUp)
    const draw = (timestamp) => {
      frame = requestAnimationFrame(draw)
      const game = gameRef.current
      if (!game) return
      const dt = Math.min(0.04, (timestamp - (last || timestamp)) / 1000); last = timestamp
      const rect = canvas.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2)
      if (canvas.width !== Math.round(rect.width * dpr) || canvas.height !== Math.round(rect.height * dpr)) { canvas.width = Math.round(rect.width * dpr); canvas.height = Math.round(rect.height * dpr) }
      const scaleX = canvas.width / 900, scaleY = canvas.height / 600
      context.setTransform(scaleX, 0, 0, scaleY, 0, 0)
      context.fillStyle = '#061522'; context.fillRect(0, 0, 900, 600)
      game.stars.forEach((star) => { context.fillStyle = `rgba(177,229,232,${star.alpha})`; context.fillRect(star.x, star.y, star.size, star.size) })
      context.fillStyle = '#123b50'; context.beginPath(); context.arc(810, 475, 175, 0, Math.PI * 2); context.fill(); context.strokeStyle = '#347582'; context.lineWidth = 3; context.beginPath(); context.arc(810, 475, 190, 3.5, 5.85); context.stroke()
      context.fillStyle = '#55d6dc'; context.shadowColor = '#55d6dc'; context.shadowBlur = 20; roundRect(context, 420, 42, 60, 42, 9); context.fill(); context.shadowBlur = 0
      if (!pausedRef.current && !game.done) {
        game.elapsed += dt
        const speed = 300 * dt
        if (keys.has('arrowleft') || keys.has('a') || game.touchX < -0.2) game.ship.x -= speed
        if (keys.has('arrowright') || keys.has('d') || game.touchX > 0.2) game.ship.x += speed
        if (keys.has('arrowup') || keys.has('w') || game.touchY < -0.2) game.ship.y -= speed
        if (keys.has('arrowdown') || keys.has('s') || game.touchY > 0.2) game.ship.y += speed
        game.ship.x = Math.max(0, Math.min(862, game.ship.x)); game.ship.y = Math.max(0, Math.min(562, game.ship.y))
        game.asteroids.forEach((rock) => { rock.y += 170 * dt; if (rock.y > 630) { rock.y = -30 - Math.random() * 250; rock.x = 20 + Math.random() * 830 } if (Math.abs(game.ship.x + 19 - rock.x) < 34 && Math.abs(game.ship.y + 19 - rock.y) < 34 && !rock.hit) { rock.hit = true; rock.y = 700; game.hits += 1; setHits(game.hits) } if (rock.y < -100) rock.hit = false })
        if (Math.abs(game.ship.x + 19 - 450) < 55 && Math.abs(game.ship.y + 19 - 63) < 45) { game.done = true; callbackRef.current(true, Math.max(0, 100 - game.hits * 20), { summary: `${game.hits} collision alert(s), ${game.elapsed.toFixed(1)} seconds`, hits: game.hits }, startedAt); return }
        if (game.hits >= 3) { game.done = true; callbackRef.current(false, Math.max(0, 100 - game.hits * 20), { summary: `${game.hits} collision alert(s), ${game.elapsed.toFixed(1)} seconds`, hits: game.hits }, startedAt); return }
        if (Math.floor(game.elapsed * 4) !== lastDisplayTick) { lastDisplayTick = Math.floor(game.elapsed * 4); setElapsed(game.elapsed) }
      }
      game.asteroids.forEach((rock) => { context.fillStyle = '#c97853'; context.beginPath(); context.arc(rock.x + 15, rock.y + 15, 15, 0, Math.PI * 2); context.fill(); context.fillStyle = '#e9a079'; context.fillRect(rock.x + 7, rock.y + 9, 4, 3) })
      context.fillStyle = '#f2eee3'; context.strokeStyle = '#48cfd9'; context.lineWidth = 2; context.shadowColor = '#51d1da'; context.shadowBlur = 15; context.beginPath(); context.moveTo(game.ship.x + 19, game.ship.y); context.lineTo(game.ship.x, game.ship.y + 38); context.lineTo(game.ship.x + 38, game.ship.y + 38); context.closePath(); context.fill(); context.stroke(); context.shadowBlur = 0
      context.fillStyle = '#e7f0f5'; context.font = '14px monospace'; context.fillText(`REACH THE BEACON   /   COLLISION ALERTS ${game.hits}   /   ${game.elapsed.toFixed(1)} SEC`, 20, 25)
      if (pausedRef.current) { context.fillStyle = 'rgba(4, 15, 25, .75)'; context.fillRect(0, 0, 900, 600); context.fillStyle = '#e7f0f5'; context.font = 'bold 34px sans-serif'; context.textAlign = 'center'; context.fillText('FLIGHT PAUSED', 450, 295); context.textAlign = 'left' }
    }
    frame = requestAnimationFrame(draw)
    return () => { cancelAnimationFrame(frame); window.removeEventListener('keydown', keyDown); window.removeEventListener('keyup', keyUp) }
  }, [startedAt])
  function steer(direction, pressed) { if (gameRef.current) { const moves = { left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1] }; [gameRef.current.touchX, gameRef.current.touchY] = pressed ? moves[direction] : [0, 0] } }
  return <><PageHeading eyebrow="FLIGHT OPERATIONS / PILOTING SIMULATION" title="Orbital navigation" subtitle="Steer through the asteroid field and reach the orbital beacon." action={<button className="button button-outline" onClick={onExit}>Exit simulation <span>×</span></button>} />
    <div className="game-toolbar"><div className="game-metric"><small>COLLISION ALERTS</small><b className={hits > 0 ? 'critical-text' : ''}>{hits}<i> / 3</i></b></div><div className="game-metric"><small>FLIGHT TIME</small><b>{elapsed.toFixed(1)}<i> sec</i></b></div><div className="game-actions"><button className="button button-outline" onClick={() => setPaused((value) => !value)}>{paused ? '▶ Resume' : 'Ⅱ Pause'}</button><button className="button button-quiet" onClick={restart}>↻ Restart</button></div></div>
    <div className="canvas-frame"><canvas ref={canvasRef} aria-label="Spacecraft navigation game. Use arrow keys or WASD to steer." /><div className="beacon-label">TARGET BEACON <i>↑</i></div></div>
    <div className="game-foot"><span>STEER WITH ARROW KEYS OR WASD <i>·</i> ESC TO ABORT</span><div className="touch-controls">{['left', 'up', 'down', 'right'].map((direction) => <button key={direction} onPointerDown={() => steer(direction, true)} onPointerUp={() => steer(direction, false)} onPointerLeave={() => steer(direction, false)} aria-label={`Steer ${direction}`}>{direction === 'left' ? '←' : direction === 'up' ? '↑' : direction === 'down' ? '↓' : '→'}</button>)}</div></div>
  </>
}
function createGame() { return { ship: { x: 431, y: 460 }, touchX: 0, touchY: 0, hits: 0, elapsed: 0, done: false, stars: Array.from({ length: 140 }, () => ({ x: Math.random() * 900, y: Math.random() * 600, size: Math.random() * 2 + 0.5, alpha: Math.random() * 0.7 + 0.2 })), asteroids: Array.from({ length: 9 }, () => ({ x: 20 + Math.random() * 830, y: -Math.random() * 600, hit: false })) } }
function roundRect(context, x, y, width, height, radius) { context.beginPath(); context.roundRect(x, y, width, height, radius) }
