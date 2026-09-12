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
