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

// BEGIN ARENA PANEL
export const ARENA_LABELS = {REAL:'Connectome',SHUFFLED:'Rewired',SILENCED:'No recurrence',LESIONED:'Lesioned',GREEDY:'Greedy baseline',RANDOM:'Random baseline'}
const ARENA_ACTIONS = ['NORTH','EAST','SOUTH','WEST','EAT','WAIT']

export function arenaSummary(rows=[]) {
  return Object.keys(ARENA_LABELS).flatMap(mode=>{
    const completed=rows.filter(row=>row.mode===mode&&['all_food','energy_exhausted','step_limit'].includes(row.outcome))
    if(!completed.length)return []
    return [{mode,count:completed.length,food:completed.reduce((sum,row)=>sum+row.food,0)/completed.length,
      steps:completed.reduce((sum,row)=>sum+row.steps,0)/completed.length}]
  })
}

export function validateArenaReplay(value) {
  const integer=(n,min,max)=>Number.isInteger(n)&&n>=min&&n<=max
  const point=p=>Array.isArray(p)&&p.length===2&&p.every(n=>integer(n,0,10))
  if(value?.kind!=='arena-replay'||value.version!==1||value.world?.size!==11||!ARENA_LABELS[value.mode]||
    !Array.isArray(value.world.walls)||value.world.walls.length>121||!value.world.walls.every(point)||
    !Array.isArray(value.world.food)||value.world.food.length!==7||!value.world.food.every(point)||
    !Array.isArray(value.frames)||!value.frames.length||value.frames.length>121)throw Error('This is not a supported Flymes arena replay.')
  for(const [index,frame] of value.frames.entries()) {
    if(!integer(frame.step,0,120)||frame.step!==index||!integer(frame.x,0,10)||!integer(frame.y,0,10)||
      !integer(frame.energy,0,32)||!Array.isArray(frame.eaten)||frame.eaten.length>7||
      new Set(frame.eaten).size!==frame.eaten.length||!frame.eaten.every(n=>integer(n,0,6))||
      (frame.action!==null&&!ARENA_ACTIONS.includes(frame.action))||
      !frame.scores||typeof frame.scores!=='object'||Array.isArray(frame.scores)||
      Object.entries(frame.scores).some(([key,n])=>!ARENA_ACTIONS.includes(key)||!Number.isFinite(n)))throw Error('The arena replay contains an invalid frame.')
  }
  return value
}

function ArenaMap({world,frame,trail=[]}) {
  const ref=useRef(null)
  useEffect(()=>{
    if(!world||!frame)return
    const canvas=ref.current
    const paint=()=>{
      const size=canvas.clientWidth,dpr=window.devicePixelRatio||1
      canvas.width=Math.round(size*dpr);canvas.height=Math.round(size*dpr)
      const c=canvas.getContext('2d');c.scale(dpr,dpr)
      const unit=size/world.size
      c.fillStyle='#e9e4d6';c.fillRect(0,0,size,size)
      c.strokeStyle='#d8d0be';c.lineWidth=.5
      for(let i=1;i<world.size;i++){c.beginPath();c.moveTo(i*unit,0);c.lineTo(i*unit,size);c.moveTo(0,i*unit);c.lineTo(size,i*unit);c.stroke()}
      c.fillStyle='#706251'
      for(const [x,y] of world.walls)c.fillRect(x*unit+1,y*unit+1,unit-2,unit-2)
      c.strokeStyle='#9c6332';c.lineWidth=2;c.lineJoin='round';c.beginPath()
      trail.filter(f=>f.step<=frame.step).forEach((f,i)=>{const x=(f.x+.5)*unit,y=(f.y+.5)*unit;i?c.lineTo(x,y):c.moveTo(x,y)})
      c.stroke()
      world.food.forEach(([x,y],i)=>{
        if(frame.eaten.includes(i))return
        c.fillStyle='#44613c';c.beginPath();c.arc((x+.5)*unit,(y+.5)*unit,unit*.18,0,Math.PI*2);c.fill()
        c.strokeStyle='#44613c';c.lineWidth=1.5;c.beginPath();c.moveTo((x+.5)*unit,(y+.36)*unit);c.lineTo((x+.63)*unit,(y+.24)*unit);c.stroke()
      })
      const specimen=document.createElement('canvas');specimen.width=350;specimen.height=300
      drawFly(specimen.getContext('2d'),350,300,flyPose('FINISH',0),0)
      const direction={NORTH:0,EAST:Math.PI/2,SOUTH:Math.PI,WEST:-Math.PI/2}[frame.action]||0
      c.save();c.translate((frame.x+.5)*unit,(frame.y+.5)*unit);c.rotate(direction)
      c.drawImage(specimen,-unit*.8,-unit*.7,unit*1.6,unit*1.4);c.restore()
    }
    paint();const observer=new ResizeObserver(paint);observer.observe(canvas)
    return()=>observer.disconnect()
  },[world,frame,trail])
  return h('canvas',{ref,className:'fa-map',role:'img','aria-label':frame?`Foraging world. Step ${frame.step}. Fly at column ${frame.x}, row ${frame.y}. ${frame.eaten.length} of 7 food collected. Energy ${frame.energy} of 32.`:'Foraging arena'})
}

function saveArenaFile(value,name) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}))
  const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}

function ArenaPanel({ctx}) {
  const [state,setState]=useState(null),[offline,setOffline]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const [mode,setMode]=useState('GREEDY'),[seed,setSeed]=useState(7),[steps,setSteps]=useState(60),[seeds,setSeeds]=useState(3),[lesion,setLesion]=useState(30)
  const [selected,setSelected]=useState(['GREEDY','RANDOM']),[replay,setReplay]=useState(null),[position,setPosition]=useState(0)
  const alive=useRef(true),epoch=useRef(0),file=useRef(null)
  useEffect(()=>{
    alive.current=true;let timer
    const poll=async()=>{
      const version=epoch.current
      try{const next=await ctx.rest('/arena/state',{timeoutMs:5000});if(alive.current&&version===epoch.current){setState(next);setOffline(false)}}
      catch{if(alive.current)setOffline(true)}
      finally{if(alive.current)timer=setTimeout(poll,600)}
    }
    poll();return()=>{alive.current=false;clearTimeout(timer);ctx.rest('/arena',{method:'POST',body:{command:'stop'},timeoutMs:3000}).catch(()=>{})}
  },[ctx])
  const active=['preparing','running','paused','stopping'].includes(state?.status)
  const available=state?.available_modes||['GREEDY','RANDOM']
  const valid=Number.isInteger(seed)&&seed>=0&&seed<=4294967285&&Number.isInteger(steps)&&steps>=10&&steps<=120&&Number.isInteger(seeds)&&seeds>=1&&seeds<=10
  const send=async(command)=>{
    epoch.current++;setBusy(true);setError('')
    if(command==='run'||command==='compare')setReplay(null)
    try{const result=await ctx.rest('/arena',{method:'POST',body:{command,mode,seed,max_steps:steps,seeds,lesion_percent:lesion,modes:selected.filter(m=>available.includes(m))},timeoutMs:15000});if(alive.current){setState(result);setOffline(false)}}
    catch(e){if(alive.current)setError(String(e.message||e))}
    finally{if(alive.current)setBusy(false)}
  }
  const load=async(row)=>{
    setBusy(true);setError('')
    try{const result=validateArenaReplay(await ctx.rest(`/arena/replay/${row.seed}/${row.mode}`,{timeoutMs:15000}));if(alive.current){setReplay(result);setPosition(0)}}
    catch(e){if(alive.current)setError(String(e.message||e))}
    finally{if(alive.current)setBusy(false)}
  }
  const exportReport=async()=>{
    setBusy(true);setError('')
    try{saveArenaFile(await ctx.rest('/arena/report',{timeoutMs:15000}),'flymes-arena-report.json')}
    catch(e){if(alive.current)setError(String(e.message||e))}
    finally{if(alive.current)setBusy(false)}
  }
  const importReplay=async(event)=>{
    try{const chosen=event.target.files?.[0];if(!chosen)return;if(chosen.size>1024*1024)throw Error('Replay files must be smaller than 1 MB.');const value=validateArenaReplay(JSON.parse(await chosen.text()));setReplay(value);setPosition(0);setError('')}
    catch(e){setError(String(e.message||e))}finally{event.target.value=''}
  }
  const frame=replay?replay.frames[position]:state?.frame,world=replay?.world||state?.world
  const currentMode=replay?.mode||state?.mode||mode
  const button=(text,command,disabled=false)=>h('button',{type:'button',disabled:busy||disabled,onClick:()=>send(command)},text)
  return h('article',{className:'flymes fa-panel'},
    h('header',{className:'fm-head'},h('div',null,h('h1',null,'Foraging arena'),h('p',{className:'fm-subhead'},'A small world. Every move is measured.'))),
    h('p',{className:'fm-note'},'No language model or provider calls. The circuit and baselines receive the same scent, obstacle, food, and energy signals.'),
    h('div',{className:'fm-toolbar'},h('span',{className:'fm-state',role:'status'},replay?'RECORDED REPLAY':offline?'DISCONNECTED':(state?.status||'CONNECTING').toUpperCase()),h('span',null,ARENA_LABELS[currentMode])),
    offline&&h('p',{className:'fm-error'},'Companion unavailable. Run scripts/launch.ps1; reconnecting automatically. Recorded replays still work.'),
    error&&h('p',{className:'fm-error',role:'alert'},error),
    state?.error&&h('p',{className:'fm-error',role:'alert'},state.error),
    state?.notice&&h('p',null,state.notice),
    world&&frame?h('figure',{className:'fa-world'},h(ArenaMap,{world,frame,trail:replay?.frames||[]}),h('figcaption',null,'Green dots are food. Brown cells are walls. The fly illustration marks its measured position.')):
      h('div',{className:'fa-empty'},h('h2',null,'Find seven food sites.'),h('p',null,'Each move spends energy. Eating restores it. Choose a controller, then watch a seeded world unfold.')),
    frame&&h('div',{className:'fa-readouts'},h('span',null,h('strong',null,`${frame.eaten.length} / 7`),' food'),h('span',null,h('strong',null,`${frame.energy} / 32`),' energy'),h('span',null,h('strong',null,frame.step),' moves')),
    frame&&h('p',{className:'fa-action'},frame.action?`Last action: ${frame.action.toLowerCase()}`:'At the starting position.'),
    replay&&h('section',{className:'fm-section'},h('label',null,`Replay frame ${position} of ${replay.frames.length-1}`,h('input',{type:'range',min:0,max:replay.frames.length-1,value:position,onChange:e=>setPosition(Number(e.target.value))})),h('div',{className:'fm-controls'},h('button',{type:'button',onClick:()=>setReplay(null)},'Back to experiment'),h('button',{type:'button',onClick:()=>saveArenaFile(replay,'flymes-arena-replay.json')},'Save replay'))),
    h('section',{className:'fm-section'},h('h2',null,'Watch a run'),
      h('label',null,'Controller',h('select',{value:mode,disabled:active||busy,onChange:e=>setMode(e.target.value)},Object.entries(ARENA_LABELS).map(([key,label])=>h('option',{key,value:key,disabled:!available.includes(key)},label)))),
      !state?.dataset_available&&h('p',{className:'fm-note'},'Neural controllers need the prepared MaleCNS dataset. Greedy and random baselines work without it. No synthetic graph is substituted.'),
      state?.dataset&&h('p',{className:'fm-note'},`${state.dataset.mode||'Prepared graph'} · ${state.dataset.neurons??'Unknown'} neurons. Engineered sensory mappings; no learning.`),
      h('div',{className:'fa-fields'},h('label',null,'World seed',h('input',{type:'number',min:0,max:4294967285,value:Number.isFinite(seed)?seed:'',disabled:active||busy,onChange:e=>setSeed(e.target.value===''?NaN:Number(e.target.value))})),h('label',null,'Move limit',h('input',{type:'number',min:10,max:120,value:Number.isFinite(steps)?steps:'',disabled:active||busy,onChange:e=>setSteps(e.target.value===''?NaN:Number(e.target.value))}))),
      h('label',null,`Lesion amount: ${lesion}%`,h('input',{type:'range',min:0,max:100,step:10,value:lesion,disabled:active||busy,onChange:e=>setLesion(Number(e.target.value))})),
      !valid&&h('p',{className:'fm-error'},'Use a nonnegative whole-number seed, 10–120 moves, and 1–10 comparison worlds.'),
      h('div',{className:'fm-controls'},button('Run arena','run',active||offline||!state||!valid||!available.includes(mode)),
        active&&state?.experiment==='single'&&button(state.status==='paused'?'Resume':'Pause',state.status==='paused'?'resume':'pause',!['paused','running'].includes(state.status)||offline),
        active&&button('Stop experiment','stop',state.status==='stopping'))),
    h('section',{className:'fm-section'},h('h2',null,'Compare the same worlds'),h('p',null,'Each controller starts fresh on each world. Food collected is the primary measure. Stopped episodes are excluded from averages.'),
      h('fieldset',{className:'fa-modes',disabled:active||busy},h('legend',null,'Controllers to compare'),Object.entries(ARENA_LABELS).map(([key,label])=>h('label',{key},h('input',{type:'checkbox',checked:selected.includes(key),disabled:!available.includes(key),onChange:e=>setSelected(old=>e.target.checked?[...old,key]:old.filter(m=>m!==key))}),label))),
      h('label',null,'Consecutive world seeds',h('input',{type:'number',min:1,max:10,value:Number.isFinite(seeds)?seeds:'',disabled:active||busy,onChange:e=>setSeeds(e.target.value===''?NaN:Number(e.target.value))})),
      h('div',{className:'fm-controls'},button('Compare controllers','compare',active||offline||!state||!valid||selected.filter(m=>available.includes(m)).length<2)),
      state?.total>0&&h('p',{role:'status'},`${state.progress} of ${state.total} episodes recorded${active?'. Neural comparisons can take several minutes.':'.'}`),
      state?.rows?.length>0&&h('div',{className:'fa-results'},h('table',null,h('caption',null,'Completed episodes only'),h('thead',null,h('tr',null,h('th',{scope:'col'},'Controller'),h('th',{scope:'col'},'Mean food'),h('th',{scope:'col'},'Runs'))),h('tbody',null,arenaSummary(state.rows).map(row=>h('tr',{key:row.mode},h('th',{scope:'row'},ARENA_LABELS[row.mode]),h('td',null,`${row.food.toFixed(2)} / 7`),h('td',null,row.count))))),
        h('details',null,h('summary',null,'Individual episodes and replay'),state.rows.map(row=>h('div',{className:'fa-episode',key:`${row.seed}-${row.mode}`},h('span',null,`${ARENA_LABELS[row.mode]} · world ${row.seed}: ${row.food}/7, ${row.outcome.replaceAll('_',' ')}`),h('button',{type:'button',disabled:active||busy,onClick:()=>load(row)},'Replay'))))),
      h('p',{className:'fm-note'},'A small experiment, not evidence of a biological advantage. Compare multiple seeds and inspect failures.'),
      h('div',{className:'fm-controls'},h('button',{type:'button',disabled:!state?.has_report||busy||offline,onClick:exportReport},'Save report'),h('button',{type:'button',disabled:active||busy,onClick:()=>file.current.click()},'Open replay'),h('input',{ref:file,type:'file',accept:'.json,application/json',hidden:true,onChange:importReplay}))),
    frame&&h('details',{className:'fm-section'},h('summary',null,'Action readouts'),h('p',{className:'fm-note'},'Scores are relative activity, not probabilities. A common action mask prevents entering walls and eating empty cells.'),h('pre',null,JSON.stringify(frame.scores,null,2))))
}

const ARENA_CSS = `
.fm-nav{display:flex;gap:6px;flex-wrap:wrap;padding:10px 14px;border-bottom:1px solid var(--border,#42413d);font:13px var(--font-sans,Segoe UI,sans-serif)}
.fm-nav button{font:inherit;color:var(--text-primary,#ecebe7);background:transparent;border:1px solid transparent;border-radius:4px;padding:8px 10px;cursor:pointer}
.fm-nav button[aria-pressed=true]{border-color:var(--accent,#dfb476);color:var(--accent,#dfb476)}
.fm-nav button:hover{background:var(--surface-hover,#302d27)}.fm-nav button:focus-visible{outline:2px solid var(--accent,#dfb476);outline-offset:2px}
.fa-panel{height:calc(100% - 58px)}.fa-world{margin:16px 0 0}.fa-panel .fa-map{display:block;width:100%;height:auto;aspect-ratio:1;background:#e9e4d6;border-radius:4px}
.fa-world figcaption{font-size:12px;color:var(--text-secondary,#bab5ab);margin-top:8px;line-height:1.5}
.fa-empty{padding:30px 0;border-block:1px solid var(--border,#42413d);margin-block:20px}.fa-empty h2{font-size:22px;margin-bottom:8px}
.fa-readouts{display:flex;justify-content:space-between;gap:8px;margin-top:18px;font-variant-numeric:tabular-nums}.fa-readouts span{display:flex;flex-direction:column;gap:3px;color:var(--text-secondary,#bab5ab)}.fa-readouts strong{font-size:19px;color:var(--text-primary,#ecebe7);font-weight:600}
.fa-action{font-size:15px}.fa-fields{display:grid;grid-template-columns:1fr 1fr;gap:14px}.fa-fields>*{min-width:0}.fa-panel label{display:block;margin:10px 0}
.fa-panel input[type=range]{padding:0;accent-color:var(--accent,#dfb476)}.fa-panel input[type=number]{box-sizing:border-box;width:100%;min-width:0}.fa-panel select{width:100%}
.fa-modes{padding:8px 0;border:0}.fa-modes legend{font-weight:600}.fa-modes label{display:flex;align-items:center;gap:8px}.fa-modes input[type=checkbox]{width:16px;min-height:16px;margin:0;accent-color:var(--accent,#dfb476)}
.fa-results table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;margin-top:18px}.fa-results caption{text-align:left;font-size:12px;color:var(--text-secondary,#bab5ab);padding-bottom:8px}.fa-results th,.fa-results td{text-align:left;padding:10px 4px;border-bottom:1px solid var(--border,#42413d);font-size:12px}.fa-results th{font-weight:500}.fa-results td{white-space:nowrap}
.fa-episode{display:flex;align-items:center;gap:10px;justify-content:space-between;margin-top:12px;font-size:12px}.fa-episode span{min-width:0;overflow-wrap:anywhere}.fa-episode button{flex-shrink:0}
.fa-panel [hidden]{display:none!important}.fa-panel ::selection{background:#dfb476;color:#201b15}.fa-panel{scrollbar-color:#706251 transparent}.fa-panel input{caret-color:var(--accent,#dfb476)}
`

// END ARENA PANEL

export function FlymesPanel({ctx,initialView='native'}) {
  const [view,setView]=useState(initialView)
  return h('div',{style:{height:'100%',minHeight:0}},h('style',null,CSS+ARENA_CSS),
    h('nav',{className:'fm-nav','aria-label':'Flymes modes'},[['native','Hermes task'],['arena','Arena'],['demo','Built-in demo']].map(([key,label])=>h('button',{key,type:'button','aria-pressed':view===key,onClick:()=>setView(key)},label))),
    view==='arena'?h(ArenaPanel,{ctx}):view==='demo'?h(DemoPanel,{ctx}):h(NativePanel,{ctx}))
}

export default {id:'flymes',name:'Flymes',description:'Connectome supervisory controller with measured telemetry and bounded Hermes actions.',defaultEnabled:false,register(ctx){ctx.register({id:'pane',area:'panes',title:'Flymes',data:{placement:'right',width:'440px'},render:()=>h(FlymesPanel,{ctx})});ctx.onDispose(()=>{ctx.rest('/control',{method:'POST',body:{command:'stop',reason:'plugin_disabled'},timeoutMs:3000}).catch(()=>{});ctx.rest('/arena',{method:'POST',body:{command:'stop'},timeoutMs:3000}).catch(()=>{})})}}
