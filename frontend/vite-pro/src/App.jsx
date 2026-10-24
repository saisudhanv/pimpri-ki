import { useEffect, useMemo, useState } from 'react'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './App.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const fmt = (value, suffix = '') => value == null ? '—' : `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 })}${suffix}`
const time = value => value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'

function Card({ label, value, hint, tone = '' }) {
  return <article className={`kpi ${tone}`}><span>{label}</span><strong>{value}</strong><small>{hint}</small></article>
}

function Sparkline({ rows }) {
  const chartData = rows.map(row => ({ ...row, label: time(row.target_time) }))
  if (!chartData.length) return <div className="empty">No chart data available</div>
  return <div className="chart-wrap"><ResponsiveContainer width="100%" height={210}><LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
    <XAxis dataKey="label" tick={{ fill: '#73847e', fontSize: 10 }} axisLine={false} tickLine={false} />
    <YAxis tick={{ fill: '#73847e', fontSize: 10 }} axisLine={false} tickLine={false} />
    <Tooltip contentStyle={{ background: '#132321', border: '1px solid #29433e', fontSize: 11 }} formatter={(value) => [`${value ?? '—'} MW`]} />
    <Line type="monotone" dataKey="forecast_mw" name="Forecast" stroke="#bd9bff" strokeWidth={2} dot={false} connectNulls={false} />
    <Line type="monotone" dataKey="actual_mw" name="Actual" stroke="#31d296" strokeWidth={2} dot={false} connectNulls={false} />
  </LineChart></ResponsiveContainer><div className="legend"><span className="forecast-dot" /> Forecast <span className="actual-dot" /> Actual</div></div>
}

function App() {
  const [cutoff, setCutoff] = useState('10:00')
  const [data, setData] = useState(null)
  const [quality, setQuality] = useState(null)
  const [error, setError] = useState('')
  const [demand, setDemand] = useState('')

  const load = () => Promise.all([fetch(`${API}/api/comparison?cutoff=${cutoff}`).then(r => r.ok ? r.json() : Promise.reject(new Error('Comparison request failed'))), fetch(`${API}/api/accuracy?cutoff=${cutoff}`).then(r => r.json()), fetch(`${API}/api/data-quality`).then(r => r.json())])
    .then(([comparison, accuracy, dq]) => { setData({ ...comparison, accuracy }); setQuality(dq); setError('') }).catch(e => setError(`${e.message}. Start the FastAPI service on port 8000.`))
  useEffect(() => { load() }, [cutoff])
  const rows = data?.rows || []
  const first = rows.find(row => row.forecast_mw != null)
  const residual = demand !== '' && first ? Math.max(0, Number(demand) - first.forecast_mw) : null
  const selectedVintages = useMemo(() => rows.filter(row => row.forecast_mw != null), [rows])

  return <main>
    <header className="topbar"><div className="brand"><div className="brand-mark">↗</div><div><h1>Wind Procurement Intelligence</h1><p>GB national wind generation · decision support</p></div></div><div className="status"><span className="pulse" /> DEMO DATA <button onClick={load}>Refresh</button></div></header>
    <section className="hero"><div><div className="eyebrow">DAY-AHEAD CONTROL ROOM</div><h2>Forecast confidence for the next decision.</h2><p>Reconstruct the forecast actually available at the <b>{cutoff} Europe/London</b> cutoff. This workspace uses an auditable synthetic fixture until Elexon historical retrieval is enabled.</p></div><div className="date-box"><span>DECISION WINDOW</span><strong>01—31 JAN 2026</strong><small>Delivery intervals through 01 Feb 2026</small></div></section>
    {error && <div className="alert">{error}<button onClick={load}>Retry</button></div>}
    <section className="filters"><label>Decision cutoff <input type="time" value={cutoff} onChange={e => setCutoff(e.target.value)} /></label><div className="filter-note">Forecast publication history is preserved · selected vintage is always ≤ cutoff</div></section>
    <section className="kpis"><Card label="Selected forecast" value={fmt(first?.forecast_mw, ' MW')} hint="First available interval" tone="green" /><Card label="Actual generation" value={fmt(first?.actual_mw, ' MW')} hint="Matched Elexon actual" /><Card label="Absolute error" value={fmt(first && first.error_mw != null ? Math.abs(first.error_mw) : null, ' MW')} hint="Forecast − actual" tone="amber" /><Card label="MAE" value={fmt(data?.accuracy?.mae_mw, ' MW')} hint={`${data?.accuracy?.valid_sample_count || 0} valid pairs`} /><Card label="RMSE" value={fmt(data?.accuracy?.rmse_mw, ' MW')} hint="Error volatility" /><Card label="Bias" value={fmt(data?.accuracy?.bias_mw, ' MW')} hint="Positive = overforecast" tone="purple" /></section>
    <section className="grid two"><article className="panel chart-panel"><div className="panel-head"><div><span className="eyebrow">GENERATION TRACE</span><h3>Forecast versus actual</h3></div><span className="tag">HALF-HOURLY · MW</span></div><Sparkline rows={rows} /><div className="chart-labels">{rows.slice(0, 4).map(row => <span key={row.target_time}>{time(row.target_time)}</span>)}</div></article><article className="panel"><div className="panel-head"><div><span className="eyebrow">ACCURACY ANALYSIS</span><h3>Error profile</h3></div></div><div className="error-list">{[['MAPE', data?.accuracy?.mape_percent, '%'], ['WAPE', data?.accuracy?.wape_percent, '%'], ['Valid pairs', data?.accuracy?.valid_sample_count, ''], ['Missing actuals', data?.accuracy?.missing_actual_count, '']].map(([label, value, suffix]) => <div className="metric-row" key={label}><span>{label}</span><b>{fmt(value, suffix)}</b></div>)}</div><p className="caption">MAPE excludes zero-actual periods. Metrics use only the selected cutoff vintage.</p></article></section>
    <section className="grid two"><article className="panel"><div className="panel-head"><div><span className="eyebrow">VINTAGE EXPLORER</span><h3>What was known at cutoff?</h3></div><span className="tag">AUDIT TRAIL</span></div><div className="table-scroll"><table><thead><tr><th>Target</th><th>Publish time</th><th>Forecast</th><th>Actual</th><th>Error</th></tr></thead><tbody>{selectedVintages.map(row => <tr key={row.target_time}><td>{time(row.target_time)}</td><td><b>{time(row.forecast_publish_time)}</b><small className="selected">SELECTED</small></td><td>{fmt(row.forecast_mw, ' MW')}</td><td>{fmt(row.actual_mw, ' MW')}</td><td className={row.error_mw > 0 ? 'positive' : 'negative'}>{fmt(row.error_mw, ' MW')}</td></tr>)}</tbody></table></div><p className="caption">Later publications are intentionally excluded. Each selected publication is retained for auditability.</p></article><article className="panel scenario"><div className="panel-head"><div><span className="eyebrow">HYPOTHETICAL SCENARIO</span><h3>Residual demand lens</h3></div><span className="tag amber-tag">NOT PROCUREMENT</span></div><p>Enter an illustrative demand value to see demand less selected wind. This is not a purchase quantity or market position.</p><label>Hypothetical demand (MW)<input type="number" min="0" placeholder="e.g. 2400" value={demand} onChange={e => setDemand(e.target.value)} /></label>{residual != null && <div className="result"><span>Estimated residual demand</span><strong>{fmt(residual, ' MW')}</strong><small>Using {fmt(first.forecast_mw, ' MW')} selected wind</small></div>}</article></section>
    <section className="quality"><div><span className="eyebrow">DATA QUALITY</span><h3>Source and coverage status</h3></div><div className="quality-items"><span><b>{quality?.retrieval_status || '—'}</b><small>retrieval mode</small></span><span><b>{quality?.forecast_record_count ?? '—'}</b><small>forecast records</small></span><span><b>{quality?.unique_target_intervals ?? '—'}</b><small>target intervals</small></span><span><b>Fixture</b><small>synthetic, not official</small></span></div></section>
    <footer>Wind Procurement Intelligence · Elexon FUELHH + WINDFOR integration boundary · Cutoff is an illustrative, configurable assumption.</footer>
  </main>
}

export default App
