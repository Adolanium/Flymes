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
