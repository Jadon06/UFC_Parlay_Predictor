import { useState, useRef } from 'react'
import type { DragEvent, ChangeEvent } from 'react'
import './index.css'

type AppState = 'idle' | 'loading' | 'result' | 'error'

type ParlayLeg = {
  fighter1: string
  fighter2: string
  bet: string
  method?: string | null
  round?: number | null
}

type PredictionResult = {
  probability: number
  leg_probs: Record<string, ParlayLeg>
}

async function fetchPrediction(file: File): Promise<PredictionResult> {
  const formData = new FormData()
  formData.append('image', file)

  const response = await fetch('https://ufc-parlay-predictor.onrender.com/predict', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) throw new Error(`Server error: ${response.status}`)

  const data = await response.json()
  console.log('API response:', data)
  return data as PredictionResult
}

function getProbabilityColor(prob: number): string {
  if (prob >= 0.7) return '#22c55e'
  if (prob >= 0.5) return '#c9a84c'
  return '#d20a0a'
}

function getProbabilityLabel(prob: number): string {
  if (prob >= 0.75) return 'Strong Hit'
  if (prob >= 0.6) return 'Likely Hit'
  if (prob >= 0.5) return 'Slight Edge'
  if (prob >= 0.35) return 'Risky Play'
  return 'Long Shot'
}

export default function App() {
  const [state, setState] = useState<AppState>('idle')
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const processFile = async (file: File) => {
    if (!file.type.startsWith('image/')) {
      setErrorMsg('Please upload an image file.')
      setState('error')
      return
    }
    setPreview(URL.createObjectURL(file))
    setState('loading')
    setErrorMsg('')
    try {
      const data = await fetchPrediction(file)
      setResult(data)
      setState('result')
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Something went wrong.')
      setState('error')
    }
  }

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) processFile(file)
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) processFile(file)
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const reset = () => {
    setState('idle')
    setResult(null)
    setPreview(null)
    setErrorMsg('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const dollarGroups = [
    { top: '4%',  left: '3%',  signs: 2, size: 18 },
    { top: '8%',  left: '88%', signs: 1, size: 22 },
    { top: '12%', left: '55%', signs: 3, size: 14 },
    { top: '18%', left: '15%', signs: 1, size: 26 },
    { top: '22%', left: '72%', signs: 2, size: 16 },
    { top: '28%', left: '42%', signs: 1, size: 20 },
    { top: '33%', left: '92%', signs: 3, size: 13 },
    { top: '38%', left: '7%',  signs: 2, size: 18 },
    { top: '44%', left: '63%', signs: 1, size: 24 },
    { top: '50%', left: '28%', signs: 3, size: 15 },
    { top: '55%', left: '82%', signs: 1, size: 19 },
    { top: '60%', left: '48%', signs: 2, size: 17 },
    { top: '65%', left: '12%', signs: 1, size: 23 },
    { top: '70%', left: '77%', signs: 3, size: 14 },
    { top: '75%', left: '35%', signs: 2, size: 20 },
    { top: '80%', left: '95%', signs: 1, size: 16 },
    { top: '85%', left: '58%', signs: 3, size: 13 },
    { top: '90%', left: '22%', signs: 2, size: 21 },
    { top: '94%', left: '68%', signs: 1, size: 18 },
    { top: '15%', left: '33%', signs: 2, size: 15 },
    { top: '47%', left: '5%',  signs: 1, size: 25 },
    { top: '62%', left: '50%', signs: 2, size: 14 },
  ]

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden', backgroundColor: '#ffffff' }}>

      {/* Diagonal background */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none' }}>
        <div style={{ position: 'absolute', inset: 0, backgroundColor: '#ffffff' }} />
        <div style={{ position: 'absolute', inset: 0, backgroundColor: '#d20a0a', clipPath: 'polygon(0 0, 100% 0, 100% 50%, 0 50%)' }} />
      </div>

      {/* Dollar signs background */}
      {dollarGroups.map((g, i) => {
        const topPct = parseFloat(g.top)
        const onRed = topPct < 50
        return (
          <div key={i} style={{ position: 'fixed', top: g.top, left: g.left, display: 'flex', gap: '3px', pointerEvents: 'none', zIndex: 0, opacity: onRed ? 0.25 : 0.12 }}>
            {Array.from({ length: g.signs }).map((_, j) => (
              <span key={j} style={{ fontSize: `${g.size}px`, color: onRed ? '#ffffff' : '#d20a0a', fontWeight: 900, lineHeight: 1, userSelect: 'none' }}>$</span>
            ))}
          </div>
        )
      })}


      {/* Header */}
      <header style={{ borderBottom: '1px solid rgba(0,0,0,0.1)', backgroundColor: 'transparent', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '900px', margin: '0 auto', padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontFamily: 'Sternbach, system-ui', fontWeight: 'bold', fontStyle: 'italic', fontSize: '22px', letterSpacing: '0.5px' }}>
              <span style={{ color: 'white' }}>UFC</span><span style={{ color: 'white' }}>PREDICT</span>
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#22c55e', display: 'inline-block', animation: 'pulse 2s infinite' }} />
            <span style={{ fontSize: '11px', color: 'white', letterSpacing: '0.15em', textTransform: 'uppercase' }}>Live Model</span>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="main-padding" style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative', zIndex: 1 }}>

        {/* Hero text */}
        <div className="animate-fade-in-up hero-margin" style={{ maxWidth: '560px', width: '100%', textAlign: 'center' }}>
          <div style={{ display: 'inline-block', backgroundColor: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.4)', borderRadius: '999px', padding: '4px 16px', marginBottom: '24px' }}>
            <span style={{ color: 'white', fontSize: '11px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase' }}>
              AI-Powered Parlay Analysis
            </span>
          </div>
          <h1 className="hero-title" style={{ color: 'white' }}>
            Will Your Parlay <span style={{ color: '#22c55e' }}>Hit</span><span style={{ color: 'white' }}>?</span>
          </h1>
          <p className="hero-sub" style={{ color: 'white', lineHeight: 1.6 }}>
            Upload your parlay screenshot and our model will predict your chances of cashing out.
          </p>
        </div>

        {/* Card */}
        <div className="animate-fade-in-up" style={{ maxWidth: '520px', width: '100%', animationDelay: '0.15s', opacity: 0 }}>

          {(state === 'idle' || state === 'error') && (
            <div
              onClick={() => fileInputRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={() => setIsDragging(false)}
              className={`upload-padding ${isDragging ? 'drop-zone-active' : ''}`}
              style={{
                position: 'relative',
                cursor: 'pointer',
                borderRadius: '16px',
                border: '2px dashed #111111',
                backgroundColor: 'transparent',
                textAlign: 'center',
                transition: 'all 0.25s ease',
              }}
            >
              {/* Corner accents */}
              {['tl','tr','bl','br'].map(pos => (
                <div key={pos} style={{
                  position: 'absolute',
                  width: '20px', height: '20px',
                  top: pos.startsWith('t') ? 0 : 'auto',
                  bottom: pos.startsWith('b') ? 0 : 'auto',
                  left: pos.endsWith('l') ? 0 : 'auto',
                  right: pos.endsWith('r') ? 0 : 'auto',
                  borderTop: pos.startsWith('t') ? '2px solid #111111' : 'none',
                  borderBottom: pos.startsWith('b') ? '2px solid #111111' : 'none',
                  borderLeft: pos.endsWith('l') ? '2px solid #111111' : 'none',
                  borderRight: pos.endsWith('r') ? '2px solid #111111' : 'none',
                  borderTopLeftRadius: pos === 'tl' ? '14px' : 0,
                  borderTopRightRadius: pos === 'tr' ? '14px' : 0,
                  borderBottomLeftRadius: pos === 'bl' ? '14px' : 0,
                  borderBottomRightRadius: pos === 'br' ? '14px' : 0,
                }} />
              ))}

              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
                <div style={{ width: '64px', height: '64px', borderRadius: '50%', backgroundColor: 'transparent', border: '1px solid #111111', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <svg width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="#111111" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                  </svg>
                </div>
                <div>
                  <p style={{ color: '#111111', fontWeight: 600, fontSize: '17px', margin: '0 0 4px' }}>Upload your parlay screenshot</p>
                  <p style={{ color: '#111111', fontSize: '14px', margin: 0 }}>
                    <span style={{ color: '#d20a0a', textDecoration: 'underline', textUnderlineOffset: '3px' }}>
                      Tap to choose from photo library
                    </span>
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#111111' }}>
                  {['JPG', 'PNG', 'GIF', 'WEBP'].map(fmt => (
                    <span key={fmt} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <span style={{ color: '#22c55e' }}>✓</span> {fmt}
                    </span>
                  ))}
                </div>
                {state === 'error' && (
                  <div style={{ width: '100%', backgroundColor: 'rgba(210,10,10,0.1)', border: '1px solid rgba(210,10,10,0.4)', borderRadius: '10px', padding: '10px 16px', color: '#ff6b6b', fontSize: '13px' }}>
                    {errorMsg}
                  </div>
                )}
              </div>
              <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/gif,image/webp" capture={undefined} style={{ display: 'none' }} onChange={handleFileChange} />
            </div>
          )}

          {state === 'loading' && (
            <div className="animate-glow" style={{ borderRadius: '16px', border: '1px solid #111111', backgroundColor: 'transparent', padding: '48px 32px', textAlign: 'center' }}>
              {preview && (
                <div style={{ position: 'relative', marginBottom: '32px' }}>
                  <img src={preview} alt="preview" style={{ width: '100%', maxHeight: '140px', objectFit: 'contain', borderRadius: '10px', opacity: 0.3, filter: 'blur(3px)' }} />
                  <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div className="spinner-ring" />
                  </div>
                </div>
              )}
              {!preview && <div className="spinner-ring" style={{ margin: '0 auto 24px' }} />}
              <p style={{ color: '#111111', fontWeight: 600, fontSize: '17px', margin: '0 0 24px' }}>Analysing your parlay…</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxWidth: '280px', margin: '0 auto' }}>
                {['Reading fighters', 'Running predictions', 'Calculating odds'].map((label, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div className="shimmer-line" style={{ height: '8px', flex: 1, borderRadius: '999px', animationDelay: `${i * 0.3}s` }} />
                    <span style={{ fontSize: '11px', color: '#111111', width: '120px', textAlign: 'left' }}>{label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {state === 'result' && result !== null && (
            <div style={{ borderRadius: '16px', border: '1px solid #111111', backgroundColor: 'transparent', overflow: 'hidden' }}>
              {preview && (
                <div style={{ position: 'relative', height: '100px', overflow: 'hidden' }}>
                  <img src={preview} alt="parlay" style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.15 }} />
                </div>
              )}
              <div className="result-padding" style={{ textAlign: 'center' }}>
                {/* Probability */}
                <p style={{ color: '#111111', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.15em', margin: '0 0 12px' }}>Parlay Win Probability</p>
                <div className="animate-count-up">
                  <span className="prob-size" style={{ fontWeight: 900, lineHeight: 1, color: getProbabilityColor(result.probability) }}>
                    {Math.round(result.probability * 100)}%
                  </span>
                </div>
                <div style={{
                  display: 'inline-block', marginTop: '16px', padding: '6px 20px', borderRadius: '999px', fontSize: '13px', fontWeight: 700, letterSpacing: '0.05em',
                  color: getProbabilityColor(result.probability),
                  border: `1px solid ${getProbabilityColor(result.probability)}44`,
                  backgroundColor: `${getProbabilityColor(result.probability)}11`,
                }}>
                  {getProbabilityLabel(result.probability)}
                </div>

                {/* Progress bar */}
                <div style={{ marginTop: '24px', width: '100%', backgroundColor: 'rgba(0,0,0,0.15)', borderRadius: '999px', height: '8px', overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', borderRadius: '999px',
                    width: `${Math.round(result.probability * 100)}%`,
                    background: `linear-gradient(90deg, #d20a0a 0%, #b91c1c 20%, #166534 30%, #15803d 50%, #16a34a 70%, #22c55e 85%, #4ade80 100%)`,
                    transition: 'width 1s ease',
                  }} />
                </div>

                {/* Leg breakdown */}
                <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '10px', textAlign: 'left' }}>
                  {Object.entries(result.leg_probs).map(([probStr, leg], idx) => {
                    const prob = parseFloat(probStr)
                    const accent = getProbabilityColor(prob)
                    return (
                      <div key={idx} style={{
                        borderRadius: '10px',
                        border: `1px solid ${accent}44`,
                        backgroundColor: `${accent}0d`,
                        padding: '12px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}>
                        <div>
                          <p style={{ color: '#111111', fontSize: '13px', fontWeight: 700, margin: '0 0 2px', lineHeight: 1.3 }}>{leg.fighter1}</p>
                          {leg.fighter2 && leg.fighter2 !== 'NA' && (
                            <p style={{ color: '#555555', fontSize: '11px', margin: '0 0 6px' }}>vs {leg.fighter2}</p>
                          )}
                          <span style={{
                            display: 'inline-block', marginTop: leg.fighter2 && leg.fighter2 !== 'NA' ? 0 : '6px',
                            padding: '2px 8px', borderRadius: '999px', fontSize: '10px', fontWeight: 600,
                            color: accent, border: `1px solid ${accent}44`, backgroundColor: `${accent}11`,
                          }}>{leg.bet}{leg.method ? ` · ${leg.method}` : ''}{leg.round ? ` · R${leg.round}` : ''}</span>
                        </div>
                        <span style={{ fontSize: '18px', fontWeight: 900, color: accent, marginLeft: '12px', whiteSpace: 'nowrap' }}>
                          {Math.round(prob * 100)}%
                        </span>
                      </div>
                    )
                  })}
                </div>

                <button
                  onClick={reset}
                  style={{
                    marginTop: '24px', width: '100%', padding: '12px', borderRadius: '10px',
                    border: '1px solid #111111', backgroundColor: 'transparent', color: '#111111',
                    fontSize: '14px', fontWeight: 500, cursor: 'pointer', transition: 'all 0.2s ease',
                  }}
                  onMouseOver={e => { (e.target as HTMLButtonElement).style.borderColor = '#d20a0a'; (e.target as HTMLButtonElement).style.color = 'white' }}
                  onMouseOut={e => { (e.target as HTMLButtonElement).style.borderColor = '#111111'; (e.target as HTMLButtonElement).style.color = '#111111' }}
                >
                  Analyse Another Parlay
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Stats strip */}
        {state === 'idle' && (
          <div className="animate-fade-in-up" style={{ maxWidth: '520px', width: '100%', marginTop: '28px', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', animationDelay: '0.3s', opacity: 0 }}>
            {[
              { value: '10K+', label: 'Fights Trained', size: 20 },
              { value: 'UFCStats.com', label: 'Data Source', size: 13 },
              { value: 'XGBoost', label: 'Model', size: 20 },
            ].map(stat => (
              <div key={stat.label} style={{ backgroundColor: 'transparent', border: '1px solid #111111', borderRadius: '12px', padding: '16px', textAlign: 'center' }}>
                <p style={{ color: '#111111', fontWeight: 900, fontSize: `${stat.size}px`, margin: '0 0 4px' }}>{stat.value}</p>
                <p style={{ color: '#111111', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0 }}>{stat.label}</p>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid rgba(0,0,0,0.1)', padding: '24px', textAlign: 'center', position: 'relative', zIndex: 1 }}>
        <p style={{ color: '#d20a0a', fontSize: '11px', letterSpacing: '0.15em', textTransform: 'uppercase', margin: 0 }}>
          UFC Predict • For entertainment purposes only
        </p>
      </footer>
    </div>
  )
}
