import { createElement as h, useEffect, useRef, useState } from 'react'
import { host } from '@hermes/plugin-sdk'

export const ACTIONS = ['SEARCH', 'INSPECT', 'IMPLEMENT', 'TEST', 'REVIEW', 'FINISH']
export const valueText = value => value === null || value === undefined ? 'Unavailable' : typeof value === 'object' ? JSON.stringify(value) : String(value)
export const numeric = value => typeof value === 'number' && Number.isFinite(value)
export function scoreRows(scores = {}) {
  const max = Math.max(0, ...Object.values(scores).filter(numeric))
  return ACTIONS.map(action => ({ action, value: numeric(scores[action]) ? scores[action] : null, width: max > 0 && numeric(scores[action]) ? Math.max(0, scores[action] / max * 100) : 0 }))
}
export function telemetryNodes(state) {
  const neural = state?.neural || state?.decision?.neural || (Array.isArray(state?.decision?.sample) ? {nodes:state.decision.sample,edges:state.decision.sample_edges,layout:'schematic'} : {})
  const nodes = Array.isArray(neural.nodes) ? neural.nodes.slice(0, 600) : []
  return { ...neural, nodes, edges: Array.isArray(neural.edges) ? neural.edges.slice(0, 1600) : [] }
}
// BEGIN FLY AVATAR
// An articulated action avatar. Motion illustrates software state, not biology.
export const FLY_BEHAVIORS = {
  SEARCH: 'Walking and exploring', INSPECT: 'Probing with its front legs',
  IMPLEMENT: 'Working with its front legs', TEST: 'Hovering with beating wings',
  REVIEW: 'Turning and grooming', FINISH: 'Settling and folding its wings',
}

export function flyPose(action, time) {
  const t = time, walk = action === 'SEARCH', hover = action === 'TEST'
  return {
    x: walk ? Math.sin(t * .55) * 45 : hover ? Math.sin(t * 1.7) * 10 : 0,
    y: walk ? Math.cos(t * .8) * 18 : hover ? -14 + Math.sin(t * 2.4) * 5 : 0,
    angle: walk ? Math.sin(t * .55) * .7 : action === 'REVIEW' ? Math.sin(t * .7) * .38 : Math.sin(t * 1.1) * .025,
    gait: walk ? t * 8 : t * 2,
    wings: hover ? .95 + Math.sin(t * 55) * .65 : action === 'FINISH' ? .08 : .2 + Math.sin(t * 2) * .025,
    probe: action === 'INSPECT' ? Math.sin(t * 5) : action === 'IMPLEMENT' ? Math.sin(t * 11) : action === 'REVIEW' ? Math.sin(t * 6) : 0,
    walk, hover,
  }
}

function drawFly(c, w, height, pose, time) {
  c.clearRect(0, 0, w, height)
  const scale = Math.min(w / 350, height / 300)
  c.save(); c.translate(w / 2, height / 2); c.scale(scale, scale)
  // Ground shadow makes walking and hovering visually distinct.
  c.save(); c.translate(pose.x, 32); c.scale(1, .35)
  const shadow = c.createRadialGradient(0, 0, 2, 0, 0, 75)
  shadow.addColorStop(0, pose.hover ? 'rgba(23,20,16,.1)' : 'rgba(23,20,16,.23)'); shadow.addColorStop(1, 'rgba(23,20,16,0)')
  c.fillStyle = shadow; c.beginPath(); c.arc(0, 0, 75, 0, Math.PI * 2); c.fill(); c.restore()
  c.translate(pose.x, pose.y); c.rotate(pose.angle)
  const line = (points, color, width) => { c.strokeStyle = color; c.lineWidth = width; c.lineCap = 'round'; c.lineJoin = 'round'; c.beginPath(); points.forEach(([x,y],i)=>i ? c.lineTo(x,y) : c.moveTo(x,y)); c.stroke() }
  const oval = (x,y,rx,ry,color,rotation=0) => { c.fillStyle=color;c.beginPath();c.ellipse(x,y,rx,ry,rotation,0,Math.PI*2);c.fill() }
  const shell = (x,y,rx,ry,light,dark) => { const g=c.createRadialGradient(x-rx*.4,y-ry*.3,2,x,y,ry*1.3);g.addColorStop(0,light);g.addColorStop(1,dark);oval(x,y,rx,ry,g) }
  // Six articulated legs, alternating tripod gait when walking.
  for (const side of [-1,1]) for (let leg=0;leg<3;leg++) {
    const phase=pose.gait+leg*Math.PI+(side===1?Math.PI:0)
    const stride=pose.walk?Math.sin(phase)*13:0
    const front=leg===0, working=front?pose.probe:0
    const root=[side*14,-21+leg*24]
    const knee=[side*(43+leg*3-working*7),-49+leg*49+stride]
    const ankle=[side*(66+leg*3-working*17),-79+leg*77+stride+working*10]
    line([root,knee,ankle,[ankle[0]+side*10,ankle[1]-7]],'#3d3022',3.2)
    line([root,knee,ankle],'#ae8450',1.2)
    oval(...knee,2.4,2.4,'#4b3826')
    for(let bristle=0;bristle<4;bristle++) { const f=.25+bristle*.16;const x=knee[0]+(ankle[0]-knee[0])*f,y=knee[1]+(ankle[1]-knee[1])*f;line([[x,y],[x+side*4,y-3]],'#66513a',.65) }
  }
  shell(0,40,25,48,'#d0a15b','#493124')
  c.save();c.beginPath();c.ellipse(0,40,25,48,0,0,Math.PI*2);c.clip()
  for(let band=0;band<5;band++){c.fillStyle='#392c23';c.beginPath();c.ellipse(0,28+band*12,28,6,0,0,Math.PI);c.fill()}
  c.restore()
  // Wings hinge at the thorax. Veins move with each wing, not a flat photo.
  for(const side of [-1,1]) {
    c.save();c.translate(side*12,-17);c.rotate(-side*pose.wings)
    c.scale(side,1)
    const wing=()=>{c.beginPath();c.moveTo(0,0);c.bezierCurveTo(36,-10,67,49,52,91);c.bezierCurveTo(38,113,10,57,0,0)}
    wing();c.fillStyle=pose.hover?'rgba(208,221,216,.46)':'rgba(221,229,217,.72)';c.fill();c.strokeStyle='rgba(99,98,75,.7)';c.lineWidth=1;c.stroke()
    c.save();wing();c.clip()
    for(let vein=0;vein<4;vein++) line([[2,3],[14+vein*9,34],[20+vein*10,96]],'rgba(115,113,86,.5)',.65)
    line([[8,28],[35,38],[53,58]],'rgba(115,113,86,.5)',.65)
    line([[15,53],[39,63],[50,83]],'rgba(115,113,86,.5)',.65)
    c.restore();c.restore()
  }
  shell(0,-12,23,31,'#b68b52','#44332a')
  line([[0,-38],[-2,5]],'rgba(239,209,159,.38)',1)
  for(let i=0;i<22;i++){const a=i*2.4,r=Math.sqrt(i/22);const x=Math.cos(a)*20*r,y=-12+Math.sin(a)*26*r;line([[x,y],[x+x*.15,y-4]],'#4b3a2a',.7)}
  shell(0,-49,20,16,'#ad8a59','#4e3a26')
  for(const side of [-1,1]) {
    shell(side*15,-51,10,14,'#da6a40','#6c231f')
    c.save();c.beginPath();c.ellipse(side*15,-51,10,14,0,0,Math.PI*2);c.clip()
    for(let row=-3;row<=3;row++)for(let col=-2;col<=2;col++)oval(side*15+col*4+(row%2)*2,-51+row*4,.65,.65,'rgba(255,209,150,.28)')
    c.restore()
    const twitch=Math.sin(time*4+side)*3
    line([[side*5,-60],[side*11,-72],[side*(19+twitch),-78]],'#5a4229',1.5)
    for(let j=0;j<4;j++)line([[side*12,-72],[side*(17+j*2),-77-j*2]],'#5a4229',.6)
  }
  c.restore()
}

function FlyAvatar({ state, stale }) {
  const canvasRef=useRef(null), current=useRef(null)
  const [preview,setPreview]=useState(''),[motion,setMotion]=useState(true),[reducedMotion,setReducedMotion]=useState(false)
  const action=preview||state?.decision?.action||state?.decision?.selected_action||''
  const replay=state?.label==='REPLAY'
  const moving=motion && !reducedMotion && (!!preview || (!stale && state?.status==='running'))
  current.current={action,moving}
  useEffect(()=>{
    const canvas=canvasRef.current,c=canvas.getContext('2d'),reduced=window.matchMedia('(prefers-reduced-motion: reduce)')
    const updatePreference=()=>setReducedMotion(reduced.matches)
    updatePreference();reduced.addEventListener('change',updatePreference)
    let frame=0,last=0,time=0,previousAction='',lastDraw=0
    const draw=stamp=>{
      const value=current.current
      if(value.action!==previousAction){time=0;previousAction=value.action}
      if(last && value.moving && !reduced.matches && !document.hidden)time+=Math.min((stamp-last)/1000,.05)
      last=stamp
      if(stamp-lastDraw>=30){
        const rect=canvas.getBoundingClientRect(),ratio=Math.min(window.devicePixelRatio||1,2)
        if(canvas.width!==Math.round(rect.width*ratio)||canvas.height!==Math.round(rect.height*ratio)){canvas.width=Math.round(rect.width*ratio);canvas.height=Math.round(rect.height*ratio)}
        c.setTransform(ratio,0,0,ratio,0,0)
        drawFly(c,rect.width,rect.height,flyPose(value.action,time),time)
        lastDraw=stamp
      }
      frame=requestAnimationFrame(draw)
    }
    frame=requestAnimationFrame(draw)
    return()=>{cancelAnimationFrame(frame);reduced.removeEventListener('change',updatePreference)}
  },[])
  return h('div',{className:'fm-avatar'},
    h('div',{className:'fm-avatar-stage'},h('canvas',{ref:canvasRef,role:'img','aria-label':`Animated fly: ${FLY_BEHAVIORS[action]||'resting'}. ${moving?'Motion enabled':'Motion paused'}.`}),
      h('div',{className:'fm-avatar-caption'},h('span',null,preview?'MOTION PREVIEW':stale?'CONNECTION LOST':replay?'RECORDED ACTION':state?.status==='running'?'ACTION AVATAR':'AT REST'),h('span',null,preview||action||'IDLE'))),
    h('div',{className:'fm-avatar-toolbar'},h('span',null,FLY_BEHAVIORS[action]||'Waiting for an action'),reducedMotion?h('span',null,'Reduced motion'):h('button',{type:'button',onClick:()=>setMotion(!motion),'aria-pressed':!motion},motion?'Pause motion':'Play motion')),
    h('details',{className:'fm-motion-preview'},h('summary',null,'Try the movements'),h('p',{className:'fm-note'},'Preview the animation without running a task.'),h('div',{className:'fm-controls'},Object.keys(FLY_BEHAVIORS).map(a=>h('button',{type:'button',key:a,'aria-pressed':preview===a,onClick:()=>{setPreview(a);setMotion(true)}},a.toLowerCase())),h('button',{type:'button',onClick:()=>setPreview(''),disabled:!preview},'Follow run'))),
    h('p',{className:'fm-note'},preview?'Preview only. The run and its selected action are unchanged.':'Motion illustrates the selected action; it is not simulated fly motor output.'))
}

// END FLY AVATAR
const ACTION_LABELS = {SEARCH:'Finding the next lead',INSPECT:'Inspecting the code',IMPLEMENT:'Making a change',TEST:'Running the tests',REVIEW:'Reviewing the result',FINISH:'Finishing the task'}
export const CSS = `
.flymes .fm-avatar{margin:0 0 18px}.flymes .fm-avatar-stage{background:#e9e4d6;color:#4f493e;position:relative;border-radius:4px;overflow:hidden}.flymes .fm-avatar-stage canvas{height:300px;width:100%;display:block}.flymes .fm-avatar-caption{display:flex;justify-content:space-between;padding:0 14px 12px;font:10px Consolas,monospace;letter-spacing:.06em}.flymes .fm-avatar-toolbar{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px 0;font-size:12px}.flymes .fm-avatar-toolbar button{font-size:11px;min-height:28px;padding:3px 7px}.flymes .fm-motion-preview summary{font-size:11px}.flymes .fm-motion-preview button[aria-pressed=true]{border-color:var(--fm-accent);color:var(--fm-accent)}.flymes .fm-error p{color:inherit}

.flymes{--fm-accent:#dfb476;--fm-bg:var(--background,#1b1d20);--fm-text:var(--ui-text-primary,#f0eee8);--fm-muted:var(--ui-text-secondary,#bcbdbb);--fm-rule:var(--ui-stroke-primary,#41444a);height:100%;overflow:auto;box-sizing:border-box;background:var(--fm-bg);color:var(--fm-text);font:13px/1.5 var(--font-sans,Segoe UI,sans-serif);scrollbar-color:var(--fm-rule) var(--fm-bg);padding:22px;min-width:260px}
.flymes *{box-sizing:border-box}.flymes ::selection{background:#946b2a;color:white}.flymes h1{font-size:26px;letter-spacing:-.045em;margin:0;font-weight:650}.flymes h2{font-size:14px;margin:0 0 12px;font-weight:600}.flymes p{margin:6px 0 12px;color:var(--fm-muted)}.flymes button,.flymes input,.flymes select{font:inherit;color:inherit;border:1px solid var(--fm-rule);background:transparent;border-radius:5px;min-height:36px;padding:6px 10px}.flymes button{cursor:pointer}.flymes button:hover:not(:disabled){background:var(--fm-rule)}.flymes button:disabled{opacity:.4;cursor:not-allowed}.flymes :focus-visible{outline:2px solid var(--fm-accent);outline-offset:3px}.flymes input{width:100%;caret-color:var(--fm-accent)}.flymes input::placeholder{color:var(--fm-muted)}.flymes select{max-width:100%;background:var(--fm-bg)}.flymes label{display:block;color:var(--fm-muted);margin:10px 0 5px}.flymes .fm-head,.flymes .fm-line{display:flex;justify-content:space-between;align-items:center;gap:12px}.flymes .fm-state{font:600 10px/1.5 var(--font-mono,Consolas,monospace);letter-spacing:.07em}.flymes .fm-live{color:var(--fm-accent)}.flymes .fm-section{padding:18px 0;border-top:1px solid var(--fm-rule)}.flymes .fm-neural{position:relative;margin:12px 0;background:#111417;border:1px solid #353b40;overflow:hidden}.flymes canvas{display:block;width:100%;height:220px}.flymes .fm-caption{padding:8px 10px;font-size:11px;color:#b7bdc0;display:flex;justify-content:space-between;gap:8px}.flymes .fm-empty{position:absolute;inset:0 0 30px;display:grid;place-content:center;padding:28px;text-align:center;color:#b7bdc0}.flymes .fm-action{font-size:28px;font-weight:600;letter-spacing:-.035em;line-height:1.15;margin:10px 0 12px;text-wrap:balance}.flymes .fm-scores{display:grid;gap:9px;margin:14px 0}.flymes .fm-score{display:grid;grid-template-columns:83px 1fr 58px;gap:10px;align-items:center;font:11px var(--font-mono,Consolas,monospace)}.flymes .fm-track{height:4px;background:var(--fm-rule)}.flymes .fm-fill{height:4px;background:#92999e}.flymes .fm-score[data-selected=true] .fm-fill{background:var(--fm-accent)}.flymes .fm-score output{text-align:right}.flymes .fm-controls{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}.flymes .fm-primary{background:var(--fm-accent);border-color:var(--fm-accent);color:#17191b;font-weight:600}.flymes .fm-primary:hover:not(:disabled){background:#edc68f}.flymes .fm-error{color:#edaaa1;overflow-wrap:anywhere}.flymes dl{display:grid;grid-template-columns:1fr auto;gap:7px 12px;margin:0}.flymes dt{color:var(--fm-muted)}.flymes dd{margin:0;max-width:220px;overflow-wrap:anywhere;text-align:right;font-variant-numeric:tabular-nums}.flymes summary{cursor:pointer;font-weight:500;min-height:30px}.flymes pre{font:11px/1.6 var(--font-mono,Consolas,monospace);white-space:pre-wrap;overflow-wrap:anywhere;max-height:280px;overflow:auto}.flymes .fm-history{list-style:none;padding:0;margin:0}.flymes .fm-history li{padding:9px 0;border-bottom:1px solid var(--fm-rule)}.flymes .fm-note{font-size:11px}.flymes .fm-mode{font:600 10px var(--font-mono,Consolas,monospace);color:var(--fm-accent)}.flymes .fm-sensitive{overflow-wrap:anywhere}
.flymes .fm-subhead{margin:2px 0 0;font-size:12px}.flymes .fm-presentation{font-size:11px;min-height:30px;padding:4px 8px}.flymes .fm-toolbar{display:flex;align-items:center;justify-content:space-between;margin:18px 0 12px;gap:10px}.flymes .fm-specimen{margin:0 0 18px;background:#f2eddf;color:#403b33;position:relative;overflow:hidden;border-radius:3px}.flymes .fm-specimen img{display:block;width:100%;height:auto;object-fit:contain}.flymes .fm-specimen figcaption{display:flex;align-items:baseline;justify-content:space-between;gap:8px;padding:0 16px 13px;font-size:10px}.flymes .fm-specimen em{font:italic 15px Georgia,serif}.flymes .fm-mechanism{display:grid;grid-template-columns:1fr 20px 1fr;align-items:center;gap:8px;padding-bottom:18px}.flymes .fm-mechanism strong{display:block;font-size:12px;font-weight:600}.flymes .fm-mechanism span{font-size:11px;color:var(--fm-muted)}.flymes .fm-mechanism .fm-arrow{color:var(--fm-accent);font-size:20px}.flymes .fm-decision-meta{font-size:11px;color:var(--fm-muted);display:flex;justify-content:space-between;gap:8px}.flymes .fm-result{display:flex;justify-content:space-between;gap:12px;padding-top:12px;font-size:12px;color:var(--fm-muted)}.flymes .fm-result output{color:var(--fm-text);text-align:right}.flymes .fm-details{margin-top:14px}.flymes .fm-controls-section h2{margin-bottom:0}.flymes footer{padding-top:8px;color:var(--fm-muted)}.flymes[data-presentation=true] .fm-action{font-size:32px}.flymes[data-presentation=true] .fm-specimen img{height:auto}.flymes[data-presentation=true] .fm-section{padding:16px 0}.flymes[data-presentation=true] .fm-controls{margin-bottom:0}@media(max-width:340px){.flymes{padding:14px}.flymes .fm-score{grid-template-columns:76px 1fr 42px;gap:6px}.flymes .fm-specimen img,.flymes[data-presentation=true] .fm-specimen img{height:auto}.flymes .fm-specimen em{font-size:13px}.flymes .fm-action,.flymes[data-presentation=true] .fm-action{font-size:26px}}
`

function NeuralView({ state, stale }) {
  const ref = useRef(null)
  const neural = telemetryNodes(state)
  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const draw = () => {
      const rect = canvas.getBoundingClientRect(), ratio = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = rect.width * ratio; canvas.height = rect.height * ratio
      const c = canvas.getContext('2d'); c.scale(ratio, ratio); c.clearRect(0, 0, rect.width, rect.height)
      const count = neural.nodes.length
      const points = neural.nodes.map((node, i) => {
        if (neural.layout === 'anatomical' && numeric(node.x) && numeric(node.y)) return [node.x * (rect.width - 32) + 16, node.y * (rect.height - 32) + 16]
        const angle = i * 2.39996323, r = Math.sqrt((i + .5) / Math.max(1, count))
        return [rect.width / 2 + Math.cos(angle) * r * rect.width * .43, rect.height / 2 + Math.sin(angle) * r * rect.height * .4]
      })
      c.strokeStyle = '#333c43'; c.lineWidth = .45
      neural.edges.forEach(edge => { const a = points[edge[0]], b = points[edge[1]]; if(a && b){c.beginPath();c.moveTo(...a);c.lineTo(...b);c.stroke()} })
      neural.nodes.forEach((node, i) => {const activity = numeric(node.activity) ? Math.max(0, Math.min(1, node.activity)) : 0; c.fillStyle = stale || node.silenced ? '#626b72' : `rgb(${116 + activity * 100},${126 + activity * 39},${132 - activity * 51})`;c.beginPath();c.arc(...points[i], activity > .1 && !stale ? 2.2 : 1.35,0,Math.PI * 2);c.fill()})
    }
    draw(); const resize = new ResizeObserver(draw); resize.observe(canvas)
    return () => resize.disconnect()
  }, [state, stale])
  return h('div',{className:'fm-neural'},h('canvas',{ref,'aria-label':`${neural.nodes.length} measured neuron samples, ${neural.layout === 'anatomical' ? 'anatomical projection' : 'schematic layout'}`,role:'img'}),!neural.nodes.length && h('div',{className:'fm-empty'},'Awaiting neural telemetry',h('small',null,'Activity appears only after a measured simulation step.')),h('div',{className:'fm-caption'},h('span',null,neural.layout === 'anatomical' ? 'Anatomical projection' : 'Schematic layout'),h('span',null,`${neural.nodes.length} rendered samples${stale ? ' · frozen' : ''}`)))
}
const definitionList = values => h('dl',null,Object.entries(values).flatMap(([key,value])=>[h('dt',{key:key+'k'},key),h('dd',{key},valueText(value))]))

function DemoPanel({ ctx }) {
  const [state,setState]=useState(null),[error,setError]=useState(''),[pollError,setPollError]=useState(''),[busy,setBusy]=useState(''),[received,setReceived]=useState(0),[now,setNow]=useState(Date.now()),[presentation,setPresentation]=useState(false),[mode,setMode]=useState('REAL'),[percent,setPercent]=useState(10),[population,setPopulation]=useState(''),[seed,setSeed]=useState(42),[checkpoint,setCheckpoint]=useState('')
  const alive=useRef(true)
  useEffect(()=>{alive.current=true;let timer,clock;const poll=async()=>{try{const next=await ctx.rest('/state',{timeoutMs:5000});if(alive.current){setState(next);setReceived(Date.now());setPollError('')}}catch(e){if(alive.current)setPollError(String(e.message||e))}finally{if(alive.current)timer=setTimeout(poll,1000)}};poll();clock=setInterval(()=>setNow(Date.now()),1000);return()=>{alive.current=false;clearTimeout(timer);clearInterval(clock);ctx.rest('/control',{method:'POST',body:{command:'stop',reason:'panel_unmounted'},timeoutMs:3000}).catch(()=>{})}},[ctx])
  const command=async(name,extra={})=>{setBusy(name);setError('');try{const result=await ctx.rest('/control',{method:'POST',body:{command:name,request_id:crypto.randomUUID(),...extra},timeoutMs:['start','compare','replay'].includes(name)?60000:15000});if(!alive.current)return;if(result?.checkpoint_id)setCheckpoint(result.checkpoint_id);else if(result?.checkpoints?.length)setCheckpoint(result.checkpoints.at(-1));if(result?.status)setState(result);else setState(await ctx.rest('/state',{timeoutMs:5000}));setReceived(Date.now())}catch(e){if(alive.current)setError(String(e.message||e))}finally{if(alive.current)setBusy('')}}
  const stale=!received || now-received>5000 || !!pollError, running=state?.status==='running', replay=state?.label==='REPLAY', decision=state?.decision || {}, selected=decision.action || decision.selected_action, dataset=state?.dataset || {}, disabled=!!busy || stale
  const button=(label,name,extra={},props={})=>h('button',{type:'button',disabled,onClick:()=>command(name,extra),...props},busy===name?'Working…':label)
  const testResult=state?.last_test ?? (state?.observation?.tests_passed !== undefined ? `${state.observation.tests_passed ?? '?'} passed / ${state.observation.tests_failed ?? '?'} failed` : 'Unavailable')
  return h('article',{className:'flymes','data-presentation':presentation},h('style',null,CSS),
    h('header',{className:'fm-head'},h('div',null,h('h1',null,'Flymes'),h('p',{className:'fm-subhead'},'A fly in the loop.'))),
    h('div',{className:'fm-toolbar'},h('span',{className:'fm-state '+(!stale?'fm-live':''),'aria-live':'polite'},stale?'DISCONNECTED':replay?'RECORDED REPLAY':running?'LIVE':(state?.status||'IDLE').toUpperCase()),h('span',{className:'fm-mode'},state?.mode==='HEURISTIC'?'HEURISTIC CONTROL':`${state?.mode||mode} CONNECTOME`)),
    (error||pollError||state?.error)&&h('div',{className:'fm-error',role:'alert'},h('p',null,pollError?'Connection interrupted. Retrying automatically.':'The last operation failed.'),!presentation&&h('details',null,h('summary',null,'Error details'),h('pre',null,error||pollError||state.error))),
    h(FlyAvatar,{state,stale}),
    h('div',{className:'fm-mechanism'},h('div',null,h('strong',null,state?.mode==='HEURISTIC'?'Heuristic selects':'Connectome selects'),h('span',null,'The next action')),h('span',{className:'fm-arrow','aria-hidden':true},'→'),h('div',null,h('strong',null,'Hermes executes'),h('span',null,'One bounded step'))),
    h('section',{className:'fm-section'},h('div',{className:'fm-decision-meta'},h('span',null,selected?'Selected action':'Ready when you are'),h('span',null,numeric(state?.step)?`STEP ${state.step}`:'NO STEPS YET')),h('div',{className:'fm-action','data-selected':!!selected},selected?(ACTION_LABELS[selected]||selected):'Let the fly choose.'),h('p',{className:'fm-note'},stale?'Connection lost. Showing the last received frame.':!selected?'Prepare a task, then step through its decisions.':`${selected} · ${replay?'Recorded decision':running?'Run in progress':`Run ${state?.status||'idle'}`}`),
    h('div',{className:'fm-result'},h('span',null,'Last test result'),h('output',null,valueText(testResult))),
    !presentation&&h('details',{className:'fm-details'},h('summary',null,'How this action was selected'),h('div',{className:'fm-scores'},scoreRows(decision.scores).map(row=>h('div',{className:'fm-score',key:row.action,'data-selected':row.action===selected},h('span',null,row.action),h('div',{className:'fm-track'},h('div',{className:'fm-fill',style:{width:`${row.width}%`}})),h('output',null,row.value===null?'—':row.value.toFixed(4))))),h('p',{className:'fm-note'},(decision.mode||state?.mode)==='HEURISTIC'?'Heuristic action scores; neural activity is reference only. ':'Relative neural readouts, not confidence. ',decision.valid_actions?.length===1?'Only one action was available.':''),h(NeuralView,{state,stale}))),
  h('section',{className:'fm-section fm-controls-section'},h('h2',null,'Run controls'),!presentation&&h('details',null,h('summary',null,'Task and experiment'),definitionList({'Dedicated workspace':state?.workspace,'Task':state?.task||'Backend-configured demo task'}),h('label',null,'Controller',h('select',{value:mode,onChange:e=>setMode(e.target.value),disabled:running},['REAL','SHUFFLED','SILENCED','HEURISTIC','LESIONED'].map(v=>h('option',{key:v},v))))),h('div',{className:'fm-controls'},button(state?.status==='paused'?'Run':'Prepare run',state?.status==='paused'?'resume':'start',{mode},{className:'fm-primary',disabled:disabled||running||replay}),button('Pause','pause',{}, {disabled:disabled||!running}),button('Step','step',{mode},{disabled:disabled||state?.status!=='paused'||replay}),button('Stop','stop',{}, {disabled:false})),!presentation&&h('p',{className:'fm-note'},'Closing this panel requests stop.'),!presentation&&definitionList({'Simulated time':numeric(state?.simulation_time)?`${state.simulation_time.toFixed(3)} s`:null,'Wall time':numeric(state?.wall_time)?`${state.wall_time.toFixed(1)} s`:null,'Simulation health':state?.health,'Last test':state?.last_test ?? (state?.observation?.tests_passed !== undefined ? `${state.observation.tests_passed ?? '?'} passed / ${state.observation.tests_failed ?? '?'} failed` : null)})),
  !presentation&&h('section',{className:'fm-section'},h('details',null,h('summary',null,'Sensory channels'),h('p',{className:'fm-note'},'Measured task observations. Missing values are unavailable.'),definitionList(state?.observation||{}),state?.decision?.encoder&&h('details',null,h('summary',null,'Derived encoder features'),h('pre',null,JSON.stringify(state.decision.encoder,null,2))))),
  !presentation&&h('section',{className:'fm-section'},h('details',null,h('summary',null,'Interventions and replay'),h('p',null,'Pause, checkpoint, then compare the same observation. Open-loop comparisons do not execute a coding task.'),h('div',{className:'fm-controls'},button('Checkpoint','checkpoint',{}, {disabled:disabled||running})),h('label',null,'Checkpoint ID',h('input',{value:checkpoint,onChange:e=>setCheckpoint(e.target.value),placeholder:'Returned by checkpoint'})),h('label',null,'Silence neurons (%)',h('input',{type:'number',min:0,max:100,value:percent,onChange:e=>setPercent(Number(e.target.value))})),h('label',null,'Annotated population (optional)',h('input',{value:population,onChange:e=>setPopulation(e.target.value),placeholder:'Exact type or class from loaded annotations'})),h('p',{className:'fm-note'},'Silencing applies to the next LESIONED readout. Unknown population names are rejected.'),h('label',null,'Intervention seed',h('input',{type:'number',min:0,value:seed,onChange:e=>setSeed(Number(e.target.value))})),h('div',{className:'fm-controls'},button('Silence neurons','lesion',{percent,seed,...(population?{population}:{})},{disabled:disabled||running}),button('Restore neurons','clear_lesions',{}, {disabled:disabled||running}),button('Compare readouts','compare',{seed},{disabled:disabled||running}),button('Replay readouts','replay',{checkpoint_id:checkpoint},{disabled:disabled||running||!checkpoint})),state?.comparisons&&h('div',null,h('h2',null,'Open-loop sensitivity'),definitionList(Object.fromEntries(Object.entries(state.comparisons.results||{}).map(([name,result])=>[name,result.action||result.selected_action]))),h('details',null,h('summary',null,'Scores and evidence'),h('pre',null,JSON.stringify(state.comparisons,null,2)))))),
  !presentation&&h('section',{className:'fm-section'},h('details',null,h('summary',null,'Dataset and run'),definitionList({'Dataset':dataset.version||dataset.name||dataset.dataset,'Simulation scope':dataset.mode||dataset.scope,'Retained neurons':dataset.neurons??dataset.neuron_count,'Directed connections':dataset.connections??dataset.edge_count,'Individual synapses':dataset.synapses,'Run ID':state?.run_id,'Model/provider':state?.model,'Workspace':state?.workspace,'Telemetry received':received?new Date(received).toLocaleTimeString():null}),h('p',{className:'fm-note'},'Synapse counts become model weights through documented assumptions. This simulation does not understand code.'))),
  !presentation&&h('section',{className:'fm-section'},h('details',null,h('summary',null,`Decision history · ${state?.history?.length||0}`),h('ol',{className:'fm-history'},(state?.history||[]).slice(-30).reverse().map((entry,i)=>h('li',{key:entry.step??i},h('details',null,h('summary',null,`Step ${entry.step} · ${entry.selected_action||entry.action||'Unknown'}`),h('pre',null,JSON.stringify(entry,null,2)))))))),h('footer',{className:'fm-note'},'Fruit-fly wiring. Fixed decoder. Measured decisions.'))
}

// BEGIN NATIVE PANEL
function NativePanel({ctx}) {
  const [state,setState]=useState(null),[session,setSession]=useState(''),[workspace,setWorkspace]=useState(''),[mode,setMode]=useState('REAL'),[error,setError]=useState(''),[offline,setOffline]=useState(false),[busy,setBusy]=useState(''),[presentation,setPresentation]=useState(false)
  const mounted=useRef(true)
  const [reviewEach,setReviewEach]=useState(false)
  useEffect(()=>{
    mounted.current=true;let timer
    const poll=async()=>{
      try {
        const selected=host.state?.focusedStoredSessionId?.get?.()||''
        if(mounted.current)setSession(selected)
        const result=await ctx.rest('/native/state',{timeoutMs:5000})
        if(mounted.current){setState(result);setOffline(!!result.offline)}
      }catch(e){if(mounted.current)setOffline(true)}
      finally{if(mounted.current)timer=setTimeout(poll,1200)}
    };poll();return()=>{mounted.current=false;clearTimeout(timer)}
  },[ctx])
  const send=async(command,extra={})=>{
    setBusy(command);setError('')
    try{
      const result=await ctx.rest('/native',{method:'POST',body:{command,session_id:command==='enable'?session:state?.session_id,...extra},timeoutMs:command==='enable'||command==='compare'?120000:15000})
      if(mounted.current){setState(result);setOffline(false)}
    }catch(e){if(mounted.current)setError(String(e.message||e))}
    finally{if(mounted.current)setBusy('')}
  }
  const selected=state?.decision?.action,active=!!state?.session_id&&!['released','idle','disabled'].includes(state?.status)
  const visual={...state,status:state?.inflight?'running':state?.status==='active'?'paused':state?.status}
  const button=(title,command,extra={},disabled=false)=>h('button',{type:'button',disabled:disabled||!!busy||state?.label==='REPLAY',key:title,onClick:()=>send(command,extra)},busy===command?'Working...':title)
  return h('article',{className:'flymes','data-presentation':presentation},
    h('header',{className:'fm-head'},h('div',null,h('h1',null,'Flymes'),h('p',{className:'fm-subhead'},'Fly Mode for Hermes tasks'))),
    h('div',{className:'fm-toolbar'},h('span',{className:'fm-state'},offline?'DISCONNECTED':state?.label==='REPLAY'?'RECORDED REPLAY':(state?.status||'READY').toUpperCase()),h('span',{className:'fm-mode'},state?.mode||mode)),
    offline&&h('p',{className:'fm-error',role:'status'},'Companion unavailable. Retrying. Enabled sessions keep their tool gate until you return control.'),
    error&&h('details',{className:'fm-error',open:true},h('summary',null,'Operation failed'),h('pre',null,error)),
    state?.notice&&h('p',null,state.notice),
    active&&session&&session!==state?.session_id&&h('p',{className:'fm-error'},'Fly Mode belongs to a different conversation. Return to that conversation, or return control before enabling another.'),
    h(FlyAvatar,{state:visual,stale:offline}),
    h('section',{className:'fm-section'},h('div',{className:'fm-decision-meta'},h('span',null,'Selected next action'),h('span',null,`STEP ${state?.step||0}`)),
      h('div',{className:'fm-action'},selected?(ACTION_LABELS[selected]||selected):'Give Hermes a task.'),
      h('p',null,state?.selected?.reason||'Hermes proposes alternatives. The controller selects one exact tool call.'),
      state?.selected&&h('p',{className:'fm-note'},`Tool: ${state.selected.tool}`),
      !presentation&&h('details',null,h('summary',null,'Decision and neural activity'),h('div',{className:'fm-scores'},scoreRows(state?.decision?.scores).map(row=>h('div',{className:'fm-score',key:row.action,'data-selected':row.action===selected},h('span',null,row.action),h('div',{className:'fm-track'},h('div',{className:'fm-fill',style:{width:`${row.width}%`}})),h('output',null,row.value===null?'—':row.value.toFixed(4))))),h(NeuralView,{state,stale:offline}),h('pre',null,JSON.stringify(state?.selected||{},null,2)))),
    h('section',{className:'fm-section'},h('h2',null,'Session control'),
      !active&&h('div',null,h('p',null,'Open a Hermes conversation, enable Fly Mode here, then send your coding task in that conversation.'),
        h('label',null,'Task directory',h('input',{value:workspace,onChange:e=>setWorkspace(e.target.value),placeholder:'Absolute path to your repository'})),
        h('label',null,'Controller',h('select',{value:mode,onChange:e=>setMode(e.target.value)},['REAL','SHUFFLED','SILENCED','LESIONED','HERMES'].map(m=>h('option',{key:m},m)))),
        h('label',null,h('input',{type:'checkbox',checked:reviewEach,onChange:e=>setReviewEach(e.target.checked),style:{width:'auto',minHeight:0,marginRight:8}}),'Pause before each selected tool'),
        h('p',{className:'fm-note'},session?`Selected session: ${session}`:'Send a first message in Hermes to create a session, then enable Fly Mode.'),
        button('Enable Fly Mode','enable',{workspace:workspace.trim(),mode,review_each:reviewEach},!session||!workspace.trim()||offline)),
      active&&h('div',null,!presentation&&definitionList({'Controlled session':state?.session_id,'Task directory':state?.workspace}),h('div',{className:'fm-controls'},button('Pause selection','pause',{},state?.status==='paused'||offline),button('Resume selection','resume',{},state?.status!=='paused'||offline))),
      state?.session_id&&h('div',{className:'fm-controls'},h('button',{type:'button',disabled:state?.label==='REPLAY',onClick:()=>send('release'),className:'fm-primary'},'Return control to Hermes')),
      h('p',{className:'fm-note'},'Hermes still applies its normal tool permissions. Pause blocks new selections; it does not cancel a tool already running.')),
    !presentation&&active&&h('section',{className:'fm-section'},h('details',null,h('summary',null,'Compare the same decision'),h('p',null,'Enable “Pause before each selected tool” for an intervention. Compare alternatives from the same saved neural state and proposals. No alternative tools execute during comparison.'),button('Compare readouts','compare',{lesion_percent:30},offline||!state?.pending),state?.comparisons?.length>0&&h('div',null,h('pre',null,JSON.stringify(state.comparisons,null,2)),h('p',null,'Apply a controller while paused, resume selection, then tell Hermes to continue. It must fetch the updated selection.'),h('div',{className:'fm-controls'},['REAL','SHUFFLED','SILENCED','LESIONED','HERMES'].map(m=>button(`Use ${m}`,'apply_comparison',{mode:m,lesion_percent:30},state?.status!=='paused'||offline)))))),
    !presentation&&h('section',{className:'fm-section'},h('details',null,h('summary',null,`Decision history · ${state?.history?.length||0}`),h('pre',null,JSON.stringify(state?.history||[],null,2)))),
    h('footer',{className:'fm-note'},'Calls and results appear in the normal Hermes conversation. Motion illustrates actions, not neural motor output.'))
}

// END NATIVE PANEL

export function FlymesPanel({ctx}) {
  return h('div',{style:{height:'100%',minHeight:0}},h('style',null,CSS),h(NativePanel,{ctx}))
}

export default {id:'flymes',name:'Flymes',description:'Connectome supervisory controller with measured telemetry and bounded Hermes actions.',defaultEnabled:false,register(ctx){ctx.register({id:'pane',area:'panes',title:'Flymes',data:{placement:'right',width:'440px'},render:()=>h(FlymesPanel,{ctx})});ctx.onDispose(()=>{ctx.rest('/control',{method:'POST',body:{command:'stop',reason:'plugin_disabled'},timeoutMs:3000}).catch(()=>{})})}}
