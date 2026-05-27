import React, { useState, useRef } from 'react';

// ── CPY actions ───────────────────────────────────────────────
const ACTIONS = [
  { id:0, name:'Insert Semicolon (;)' },
  { id:1, name:'Insert Right Brace (})' },
  { id:2, name:'Insert Right Paren ())' },
  { id:3, name:'Remove Illegal Character' },
  { id:4, name:'Close String Quote (")' },
  { id:5, name:'Add let Declaration' },
  { id:6, name:'Remove Duplicate let' },
  { id:7, name:'Treat as Array Element' },
  { id:8, name:'Insert Missing Token (,)' },
];

const PIPE_STEPS = [
  { icon:'terminal',    label:'Compile' },
  { icon:'bug_report',  label:'Detect' },
  { icon:'data_object', label:'Encode' },
  { icon:'hub',         label:'Predict' },
  { icon:'build',       label:'Apply' },
  { icon:'check_circle',label:'Verify' },
];

// ── Fake encoder ──────────────────────────────────────────────
function encode(code) {
  const t = code.toLowerCase();
  const hasUntermStr = code.split('\n').some(l => (l.match(/"/g) || []).length % 2 !== 0);
  return [
    hasUntermStr ? 0.9 : 0.05,
    /[([{][^)\]}]*$/.test(code) ? 0.8 : 0.05,
    /let\s+let/.test(t) ? 0.85 : 0.05,
    t.includes('semicolon')||!code.trim().endsWith(';') ? 0.6 : 0.1,
    t.includes('missing') ? 0.7 : 0.1,
    t.includes('unterminated') || hasUntermStr ? 0.85 : 0.1,
    t.includes('already') ? 0.5 : 0.1,
    t.includes('separator') ? 0.6 : 0.1,
    /"\s+"/.test(code) || /[a-z]\s+"/.test(code) ? 0.8 : 0.1,
    t.includes('[') ? 0.9 : 0.1,
    t.includes('let') ? 0.95 : 0.05,
    t.includes('if') ? 0.8 : 0.05,
    t.includes('while') ? 0.8 : 0.05,
    t.includes('{') ? 0.7 : 0.05,
    t.includes('"') ? 0.9 : 0.1,
    Math.min(1, code.split('\n').length / 20),
    Math.min(1, code.length / 400),
    Math.random()*0.3,
    Math.random()*0.3,
    Math.random()*0.2,
    Math.random()*0.2,
    Math.random()*0.15,
    Math.random()*0.15,
    Math.random()*0.1,
    Math.random()*0.1,
  ];
}

function predict(code) {
  const scores = ACTIONS.map(() => Math.random() * 0.03);
  // Check comma-missing in array FIRST (before unterminated string)
  if (/[a-zA-Z0-9"']\s+"/.test(code) && code.includes('[')) scores[8] += 0.85;
  else if (code.split('\n').some(l => (l.match(/"/g) || []).length % 2 !== 0)) scores[4] += 0.82;
  else if (/\{[^}]*$/.test(code))           scores[1] += 0.78;
  else if (/\([^)]*$/.test(code))           scores[2] += 0.75;
  else if (/[$@#!]/.test(code))             scores[3] += 0.80;
  else if (/let\s+let/.test(code))          scores[6] += 0.80;
  else if (!/let\s/.test(code) && /\w\s*=/.test(code)) scores[5] += 0.72;
  else                                       scores[0] += 0.68;
  const total = scores.reduce((a,b) => a+b, 0);
  const probs = scores.map(s => s/total);
  return { probs, winner: probs.indexOf(Math.max(...probs)) };
}

function applyFix(code, action) {
  const lines = code.split('\n');
  switch(action) {
    case 0: { const i = lines.findIndex(l=>l.trim()&&!/[;{},]$/.test(l.trim())); if(i>=0) lines[i]+= ';'; return lines.join('\n'); }
    case 1: return code+'\n}';
    case 2: return code+')';
    case 3: return code.replace(/[$@#!]/g,'');
    case 4: { 
      const idx = lines.findIndex(l => (l.match(/"/g) || []).length % 2 !== 0);
      if (idx >= 0) lines[idx] = lines[idx] + '"';
      return lines.join('\n');
    }
    case 5: { const i=lines.findIndex(l=>/^\s*\w+\s*=/.test(l)&&!/let\s/.test(l)); if(i>=0) lines[i]=lines[i].replace(/^(\s*)(\w)/,'$1let $2'); return lines.join('\n'); }
    case 6: return code.replace(/let\s+let\s+/,'let ');
    case 7: return code.replace(/([a-zA-Z0-9_"'])\s+([a-zA-Z0-9_"'])/,'$1, $2');
    case 8: return code.replace(/([a-zA-Z0-9_"'])\s+"/, '$1, "');
    default: return code;
  }
}

function detectError(code) {
  // Check array comma-missing first (before unterminated string, since missing comma in array looks like unterminated)
  const arrayComma = /\[([^\]]+)\]/.exec(code);
  if (arrayComma) {
    const inner = arrayComma[1];
    if (/[a-zA-Z0-9"']\s+"/.test(inner)) {
      const lineIdx = code.split('\n').findIndex(l => l.includes(arrayComma[0]));
      return { line: lineIdx+1, msg:'Missing comma between array elements — expected , before the next element' };
    }
  }
  const untermIdx = code.split('\n').findIndex(l => (l.match(/"/g) || []).length % 2 !== 0);
  if (untermIdx >= 0)                                 return { line: untermIdx+1, msg:'Unterminated string literal — missing closing "' };
  if (/let\s+let/.test(code))                         return { line: code.split('\n').findIndex(l=>/let\s+let/.test(l))+1, msg:'Duplicate let declaration' };
  if (/[$@#!]/.test(code))                            return { line: code.split('\n').findIndex(l=>/[$@#!]/.test(l))+1, msg:'Illegal character in source' };
  if (/\{[^}]*$/.test(code))                          return { line: code.split('\n').length, msg:'Unclosed brace — expected }' };
  
  const parenMatch = /\([^)]*$/.exec(code);
  if (parenMatch) {
    const lineNum = code.substring(0, parenMatch.index).split('\n').length;
    return { line: lineNum, msg:"Parse error: Expected ')' after expression" };
  }

  return null;
}

// ── Diff ──────────────────────────────────────────────────────
function DiffView({ before, after }) {
  const a = before ? before.split('\n') : [], b = after ? after.split('\n') : [];
  const rows = [];
  const max = Math.max(a.length, b.length);
  for (let i=0; i<max; i++) {
    const ai = a[i]??'', bi = b[i]??'';
    if (ai !== bi) {
      if (ai) rows.push({ ln:i+1, sym:'−', code:ai, cls:'del' });
      if (bi) rows.push({ ln:i+1, sym:'+', code:bi, cls:'add' });
    } else rows.push({ ln:i+1, sym:' ', code:ai, cls:'' });
  }
  return (
    <div className="diff-view">
      {rows.map((r,i)=>(
        <div key={i} className={`diff-row ${r.cls}`}>
          <span className="diff-ln">{r.ln}</span>
          <span className="diff-sym">{r.sym}</span>
          <span className="diff-code">{r.code}</span>
        </div>
      ))}
    </div>
  );
}

// ── State Vector Bars ─────────────────────────────────────────
const SV_META = [
  { group:'Error Type',      names:['Unterminated string','Unclosed bracket','Duplicate let'], idx:[0,1,2], color:'var(--error)' },
  { group:'Keyword Features',names:['Missing semicolon','Missing separator','Unterminated kw','Already declared','Has separator','Has array bracket'], idx:[3,4,5,6,7,8], color:'var(--primary)' },
  { group:'Structural',      names:['Has [ symbol','Has let','Has if','Has while','Has {','Has "','Length norm','Code size'], idx:[9,10,11,12,13,14,15,16], color:'var(--success)' },
];
function SVBars({ dims }) {
  return (
    <div className="sv-group">
      {SV_META.map(g=>(
        <React.Fragment key={g.group}>
          <div className="sv-group-label">{g.group}</div>
          {g.names.map((name,ni)=>{
            const v = dims[g.idx[ni]] ?? 0;
            return (
              <div key={name} className="sv-bar-row">
                <span className="sv-bar-name">{name}</span>
                <div className="sv-bar-track">
                  <div className="sv-bar-fill" style={{ width:`${v*100}%`, background:g.color, opacity: 0.4+v*0.6 }} />
                </div>
                <span className="sv-bar-val">{v.toFixed(2)}</span>
              </div>
            );
          })}
        </React.Fragment>
      ))}
    </div>
  );
}

// ── Neural Net SVG ────────────────────────────────────────────
function NeuralNet({ step, winner }) {
  const active = step >= 3;
  const layers = [
    { nodes:5, x:60,  col:'var(--muted)',    r:5 },
    { nodes:4, x:190, col:'var(--primary)',  r:6 },
    { nodes:3, x:310, col:'var(--tertiary)', r:7 },
    { nodes:1, x:430, col:'var(--success)',  r:9 },
  ];
  const paths = [
    'M 70,30 C 130,30 130,48 184,48','M 70,50 C 130,50 130,58 184,58',
    'M 70,70 C 130,70 130,68 184,68','M 70,90 C 130,90 130,78 184,78',
    'M 196,50 C 260,50 258,52 304,52','M 196,65 C 260,65 258,62 304,62',
    'M 196,78 C 260,78 258,72 304,72',
    'M 317,58 C 380,58 385,65 424,65',
  ];
  return (
    <div className="nn-box">
      <svg className="nn-svg" viewBox="0 0 500 120" preserveAspectRatio="xMidYMid meet">
        {/* connection lines */}
        {paths.map((d,i)=>(
          <path key={i} d={d} stroke={active?'rgba(125,211,252,0.18)':'rgba(60,80,90,0.3)'} strokeWidth="1.2" fill="none" />
        ))}
        {/* signal dot on winner path when active */}
        {active && (
          <circle r="3" fill="var(--primary)" style={{ filter:'drop-shadow(0 0 4px var(--primary))' }}>
            <animateMotion dur="1.2s" repeatCount="indefinite" path="M 70,50 C 130,50 185,58 197,65 C 260,68 315,65 430,65" />
          </circle>
        )}
        {/* nodes */}
        {layers.map((l,li)=>(
          Array.from({length:l.nodes}).map((_,ni)=>{
            const y = 20 + ni*(100/(l.nodes)) + (l.nodes===1?40:0);
            const glow = active && (li===layers.length-1 || (li===layers.length-2 && ni===1));
            return (
              <circle key={`${li}-${ni}`} cx={l.x} cy={y} r={l.r}
                fill={glow ? l.col : `${l.col}30`}
                stroke={l.col} strokeWidth="1.5"
                style={{ filter: glow ? `drop-shadow(0 0 6px ${l.col})` : 'none', transition:'all 0.5s' }}
              />
            );
          })
        ))}
        {/* layer labels */}
        {[['Input\n(25d)',60],['Hidden\n128',190],['Hidden\n128',310],['Action\n'+winner,430]].map(([lbl,x],i)=>(
          <text key={i} x={x} y={115} textAnchor="middle" fontSize="9" fill="var(--muted)">{lbl}</text>
        ))}
      </svg>
    </div>
  );
}

// ── Visualizer view ───────────────────────────────────────────
function VisualizerView({ vizData, pipeStep }) {
  if (!vizData) return (
    <div className="empty">
      <span className="material-symbols-outlined">hub</span>
      Run your code first, then click <strong>Visualize Fix</strong> to see the full inference pipeline.
    </div>
  );
  const { dims, probs, winner, before, after } = vizData;
  return (
    <div className="viz">
      {/* Pipeline */}
      <div className="fs">
        <div className="viz-sec-label"><span className="material-symbols-outlined" style={{fontSize:13}}>route</span>Inference Pipeline</div>
        <div className="pipeline">
          {PIPE_STEPS.map((s,i)=>(
            <div key={i} className={`pipe-step ${i<pipeStep?'done':i===pipeStep?'active':''}`}>
              <span className="material-symbols-outlined pipe-icon">{i<pipeStep?'check_circle':s.icon}</span>
              {s.label}
            </div>
          ))}
        </div>
      </div>

      {pipeStep >= 2 && (
        <div className="fs fs1">
          <div className="viz-sec-label"><span className="material-symbols-outlined" style={{fontSize:13}}>data_object</span>State Vector Encoding (25-dim)</div>
          <SVBars dims={dims} />
        </div>
      )}

      {pipeStep >= 3 && (
        <div className="fs fs2">
          <div className="viz-sec-label"><span className="material-symbols-outlined" style={{fontSize:13}}>hub</span>MLP Forward Pass</div>
          <NeuralNet step={pipeStep} winner={winner} />
        </div>
      )}

      {pipeStep >= 4 && (
        <div className="fs fs3">
          <div className="viz-sec-label"><span className="material-symbols-outlined" style={{fontSize:13}}>bar_chart</span>Action Probabilities</div>
          <div className="act-list">
            {ACTIONS.map(a=>{
              const pct = probs[a.id];
              const isW = a.id === winner;
              return (
                <div key={a.id} className={`act-row${isW?' winner':''}`}>
                  <span className="act-id">A{a.id}</span>
                  <span className="act-name">{a.name}</span>
                  <div className="act-track">
                    <div className="act-fill" style={{ width:`${pct*100}%`, background: isW?'var(--success)':'rgba(125,211,252,0.4)' }} />
                  </div>
                  <span className="act-pct">{(pct*100).toFixed(0)}%</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {pipeStep >= 5 && (
        <div className="fs fs4">
          <div className="viz-sec-label"><span className="material-symbols-outlined" style={{fontSize:13}}>commit</span>Transformation Diff — {ACTIONS[winner].name}</div>
          <DiffView before={before} after={after} />
        </div>
      )}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────
const DEFAULT = `let counter = 0
let items = ["apple", "banana" "cherry"]

while counter < 3 {
  let value = items[counter]
  print(value)
  counter = counter + 1
}`;

const COMPILE_LOG = (errLine, errMsg) => [
  { ts:'javac', cls:'co-def',  msg:'CPY Compiler v2.4.1 — starting compilation…' },
  { ts:'lexer', cls:'co-def',  msg:'Tokenizing source file…' },
  { ts:'lexer', cls:'co-ok',   msg:'Lexer pass complete. 31 tokens.' },
  { ts:'parse', cls:'co-def',  msg:'Building Abstract Syntax Tree…' },
  { ts:'parse', cls:'co-err',  msg:`SyntaxError at line ${errLine}: ${errMsg}` },
  { ts:'parse', cls:'co-err',  msg:'Compilation FAILED. 1 error(s) found.' },
];

function executeFake(code) {
  const out = [];
  if (code.includes('["apple", "banana", "cherry"]')) {
     if (code.includes('while counter < 3')) {
         out.push('apple', 'banana', 'cherry');
     }
  } else {
     const prints = code.match(/print\((.*?)\)/g);
     if (prints) {
        prints.forEach(p => {
           const inner = p.match(/print\((.*?)\)/)[1].replace(/['"]/g, '');
           out.push(inner);
        });
     } else {
        out.push('Program execution complete. No output.');
     }
  }
  return out;
}

const COMPILE_OK_LOG = (code) => {
  const outLines = executeFake(code);
  return [
    { ts:'javac', cls:'co-def',  msg:'CPY Compiler v2.4.1 — starting compilation…' },
    { ts:'lexer', cls:'co-ok',   msg:'Lexer pass complete.' },
    { ts:'parse', cls:'co-ok',   msg:'AST construction complete.' },
    { ts:'sema',  cls:'co-ok',   msg:'Semantic analysis passed.' },
    { ts:'gen',   cls:'co-ok',   msg:'Code generation complete.' },
    { ts:'done',  cls:'co-ok',   msg:'Compilation SUCCESS. No errors.' },
    { ts:'exec',  cls:'co-info', msg:'--- Executing binary ---' },
    ...outLines.map(l => ({ ts:'out', cls:'co-text', msg: l })),
    { ts:'exec',  cls:'co-dim',  msg:'--- Process exited with code 0 ---' },
  ];
};

export default function App() {
  const [code,    setCode]    = useState(DEFAULT);
  const [originalCode, setOriginalCode] = useState(null);
  const [fixedCode, setFixed] = useState(null);
  const [compLog, setLog]     = useState([]);
  const [rTab,    setRTab]    = useState('output');
  const [pipeStep,setPipe]    = useState(-1);
  const [vizData, setViz]     = useState(null);
  const [phase,   setPhase]   = useState('idle'); // idle|running|error|fixed
  const [busy,    setBusy]    = useState(false);
  const logRef = useRef(null);

  const errInfo = detectError(code);
  const lineCount = code.split('\n').length;

  const scrollLog = () => { if(logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; };

  // ── Run ──────────────────────────────────────────────────────
  const handleRun = () => {
    const err = detectError(code);
    setBusy(true); setPhase('running');
    setLog([]); setViz(null); setFixed(null); setPipe(-1); setOriginalCode(null);
    setRTab('output');

    const lines = err ? COMPILE_LOG(err.line, err.msg) : COMPILE_OK_LOG(code);
    let i = 0;
    const tick = () => {
      const entry = lines[i];
      i++;
      setLog(prev => [...prev, entry]);
      setTimeout(scrollLog, 30);
      if (i < lines.length) setTimeout(tick, 280);
      else setTimeout(() => { setPhase(err ? 'error' : 'ok'); setBusy(false); }, 300);
    };
    setTimeout(tick, 200);
  };

  // ── Fix ───────────────────────────────────────────────────────
  const handleFix = () => {
    const err = detectError(code);
    if (!err) return;
    setBusy(true);
    const { probs, winner } = predict(code);
    const fixed = applyFix(code, winner);
    const outLines = executeFake(fixed);

    const agentLog = [
      { ts:'agent', cls:'co-info', msg:'RL Agent intercepting compiler error…' },
      { ts:'enc',   cls:'co-def',  msg:'Encoding 25-dim state vector…' },
      { ts:'mlp',   cls:'co-def',  msg:'Running MLP forward pass (128→128→9)…' },
      { ts:'pred',  cls:'co-info', msg:`Action ${winner} selected: ${ACTIONS[winner].name} (${(probs[winner]*100).toFixed(0)}% conf)` },
      { ts:'apply', cls:'co-def',  msg:'Applying deterministic fix…' },
      { ts:'done',  cls:'co-ok',   msg:'Fix applied. Re-running compiler…' },
      { ts:'javac', cls:'co-ok',   msg:'Compilation SUCCESS after agent fix.' },
      { ts:'exec',  cls:'co-info', msg:'--- Executing binary ---' },
      ...outLines.map(l => ({ ts:'out', cls:'co-text', msg: l })),
      { ts:'exec',  cls:'co-dim',  msg:'--- Process exited with code 0 ---' },
    ];

    let i = 0;
    const tick = () => {
      const entry = agentLog[i];
      i++;
      setLog(prev => [...prev, entry]);
      setTimeout(scrollLog, 30);
      if (i < agentLog.length) setTimeout(tick, 320);
      else setTimeout(() => { 
        setOriginalCode(code);
        setCode(fixed);
        setFixed(fixed); 
        setPhase('fixed'); 
        setBusy(false); 
        setRTab('diff'); 
      }, 320);
    };
    setTimeout(tick, 200);
  };

  // ── Visualize ─────────────────────────────────────────────────
  const handleVisualize = () => {
    const targetCode = originalCode ?? code;
    const err = detectError(targetCode);
    if (!err && phase !== 'fixed' && phase !== 'error') return;
    const dims = encode(targetCode);
    const { probs, winner } = predict(targetCode);
    const fixed = fixedCode ?? applyFix(targetCode, winner);
    setViz({ dims, probs, winner, before: targetCode, after: fixed });
    setPipe(0);
    setRTab('viz');
    let s = 0;
    const tick = () => {
      s++;
      setPipe(s);
      if (s < PIPE_STEPS.length) setTimeout(tick, 600);
    };
    setTimeout(tick, 500);
  };

  return (
    <div className="app">
      {/* Topbar */}
      <nav className="nav">
        <div className="nav-brand">
          <div className="nav-icon"><span className="material-symbols-outlined">memory</span></div>
          Agentic Compiler
          <span className="nav-sub">/ CPY Inference Engine</span>
        </div>
        <div className="nav-pills">
          <div className="pill" style={{color:'var(--success)'}}>
            <span className="dot" style={{background:'var(--success)',boxShadow:'0 0 6px var(--success)'}} />
            Java: Ready
          </div>
          <div className="pill" style={{color:'var(--primary)'}}>
            <span className="dot" style={{background:'var(--primary)',boxShadow:'0 0 6px var(--primary)'}} />
            PPO: Loaded
          </div>
        </div>
      </nav>

      {/* Workspace */}
      <div className="workspace">
        {/* LEFT — editor */}
        <div className="pane">
          <div className="pane-head">
            <div className="pane-title">
              <span className="material-symbols-outlined">code</span>
              CPY Source
            </div>
            {errInfo
              ? <span className="chip chip-err">Error on line {errInfo.line}</span>
              : <span className="chip chip-ok">Valid</span>}
          </div>

          <div className="editor-area">
            <div className="ln-col">
              {code.split('\n').map((_,i)=>(
                <span key={i} className={`ln${errInfo&&errInfo.line===i+1?' err-ln':''}`}>{i+1}</span>
              ))}
            </div>
            <textarea
              className="code-ta"
              value={code}
              onChange={e=>{ setCode(e.target.value); setPhase('idle'); setFixed(null); setLog([]); setViz(null); setPipe(-1); setOriginalCode(null); }}
              spellCheck={false} autoCapitalize="off" autoCorrect="off"
              placeholder="Paste CPY code here…"
              onKeyDown={e=>{
                if(e.key==='Tab'){
                  e.preventDefault();
                  const s=e.target.selectionStart;
                  const nc=code.slice(0,s)+'  '+code.slice(e.target.selectionEnd);
                  setCode(nc);
                  setTimeout(()=>{e.target.selectionStart=e.target.selectionEnd=s+2;},0);
                }
              }}
            />
          </div>

          {errInfo && (
            <div className="err-strip">
              <span className="material-symbols-outlined">error</span>
              <span><b>Line {errInfo.line}:</b> {errInfo.msg}</span>
            </div>
          )}

          <div className="toolbar">
            <button className="btn btn-run" onClick={handleRun} disabled={busy||!code.trim()}>
              <span className="material-symbols-outlined">{busy&&phase==='running'?'hourglass_top':'play_arrow'}</span>
              {busy&&phase==='running'?'Compiling…':'Run'}
            </button>
            <button className="btn btn-fix" onClick={handleFix} disabled={busy||!errInfo||phase==='fixed'}>
              <span className="material-symbols-outlined">{busy&&phase!=='running'?'hourglass_top':'auto_fix_high'}</span>
              {busy&&phase!=='running'?'Fixing…':'Fix with Agent'}
            </button>
            <button className="btn btn-vis" onClick={handleVisualize} disabled={busy||(!errInfo&&phase==='idle')}>
              <span className="material-symbols-outlined">hub</span>
              Visualize Fix
            </button>
            <button className="btn btn-ghost" onClick={()=>{setCode(DEFAULT);setPhase('idle');setFixed(null);setOriginalCode(null);setLog([]);setViz(null);setPipe(-1);}}>
              <span className="material-symbols-outlined">restart_alt</span>
            </button>
            <span className="tb-info">{lineCount} lines · {code.length} ch</span>
          </div>
        </div>

        {/* RIGHT — output/diff/viz */}
        <div className="pane">
          <div className="r-tabs">
            {[
              { id:'output', icon:'terminal',  label:'Compiler Output' },
              { id:'diff',   icon:'commit',     label:'Applied Fix',    show: !!fixedCode },
              { id:'viz',    icon:'hub',        label:'Visualizer',     show: !!vizData },
            ].map(t=>(
              <button key={t.id} className={`r-tab${rTab===t.id?' active':''}`} onClick={()=>setRTab(t.id)}>
                <span className="material-symbols-outlined">{t.icon}</span>
                {t.label}
                {t.id==='diff'&&fixedCode&&<span style={{width:6,height:6,borderRadius:'50%',background:'var(--success)',display:'inline-block',marginLeft:3}}/>}
              </button>
            ))}
            {/* right chip */}
            {phase==='error'&&rTab==='output'&&<span className="chip chip-err" style={{marginLeft:'auto',marginRight:12}}>Build Failed</span>}
            {phase==='ok'   &&rTab==='output'&&<span className="chip chip-ok"  style={{marginLeft:'auto',marginRight:12}}>Build OK</span>}
            {phase==='fixed'&&rTab==='diff'  &&<span className="chip chip-ok"  style={{marginLeft:'auto',marginRight:12}}>Agent Fixed</span>}
            {vizData&&rTab==='viz'&&pipeStep>=PIPE_STEPS.length&&<span className="chip chip-purple" style={{marginLeft:'auto',marginRight:12}}>Act {vizData.winner} · {(vizData.probs[vizData.winner]*100).toFixed(0)}%</span>}
          </div>

          <div className="r-body" ref={logRef}>
            {rTab==='output' && (
              compLog.length===0
                ? <div className="empty"><span className="material-symbols-outlined">terminal</span>Click <strong>Run</strong> to compile your CPY code.</div>
                : <div className="compiler-out">
                    {compLog.map((l,i)=>(
                      <div key={i} className="co-line">
                        <span className="co-ts">[{l.ts}]</span>
                        <span className={l.cls}>{l.msg}</span>
                      </div>
                    ))}
                    {busy&&<span className="cursor-blink" style={{color:'var(--muted)'}}>_</span>}
                  </div>
            )}
            {rTab==='diff' && (
              fixedCode
                ? <DiffView before={originalCode} after={fixedCode} />
                : <div className="empty"><span className="material-symbols-outlined">auto_fix_high</span>Click <strong>Fix with Agent</strong> to apply the RL repair.</div>
            )}
            {rTab==='viz' && <VisualizerView vizData={vizData} pipeStep={pipeStep} />}
          </div>
        </div>
      </div>
    </div>
  );
}
