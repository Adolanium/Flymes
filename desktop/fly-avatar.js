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
