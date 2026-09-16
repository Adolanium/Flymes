import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
const source=await readFile(new URL('./plugin.js',import.meta.url),'utf8')
test('shipping UI text has no Windows-decoded UTF-8 punctuation',()=>{
  assert.doesNotMatch(source, /\u00c2[\u0080-\u00bf]|\u00e2[\u0080-\u00bf\u20ac]|\ufffd/)
})
// Import the actual disk module after replacing its three host capabilities.
const loaded=source.replace(/^import .* from 'react'\r?\n/m,'const h=()=>{},useEffect=()=>{},useRef=()=>{},useState=()=>{}\n').replace(/^import .* from '@hermes\/plugin-sdk'\r?\n/m,'const host={}\n')
const plugin=await import(`data:text/javascript;base64,${Buffer.from(loaded).toString('base64')}`)
test('missing and invalid neural scores remain missing, never invented',()=>{const rows=plugin.scoreRows({SEARCH:0,TEST:.3,REVIEW:NaN});assert.equal(rows.find(x=>x.action==='INSPECT').value,null);assert.equal(rows.find(x=>x.action==='SEARCH').width,0);assert.equal(rows.find(x=>x.action==='TEST').width,100);assert.equal(rows.find(x=>x.action==='REVIEW').value,null)})
test('render budget bounds only the displayed sample',()=>{const result=plugin.telemetryNodes({neural:{nodes:Array.from({length:1000},(_,id)=>({id,activity:0})),edges:Array.from({length:2000},()=>[0,1])}});assert.equal(result.nodes.length,600);assert.equal(result.edges.length,1600);assert.equal(plugin.telemetryNodes(null).nodes.length,0)})
test('arena averages exclude stopped and failed episodes',()=>{
  const rows=plugin.arenaSummary([{mode:'REAL',food:2,steps:10,outcome:'step_limit'},{mode:'REAL',food:7,steps:20,outcome:'all_food'},{mode:'REAL',food:0,steps:2,outcome:'stopped'}])
  assert.equal(rows[0].count,2);assert.equal(rows[0].food,4.5)
})
test('arena replay rejects malformed frames and oversized traces',()=>{
  const value={kind:'arena-replay',version:1,mode:'GREEDY',world:{size:11,walls:[[0,0]],food:Array.from({length:7},(_,i)=>[i+1,1])},frames:[{step:0,x:5,y:5,energy:32,eaten:[],action:null,scores:{}}]}
  assert.equal(plugin.validateArenaReplay(value),value)
  assert.throws(()=>plugin.validateArenaReplay({...value,frames:[{...value.frames[0],energy:Infinity}]}))
  assert.throws(()=>plugin.validateArenaReplay({...value,frames:Array(122).fill(value.frames[0])}))
})
test('registers a real right pane and unload requests backend stop',async()=>{const registrations=[],disposals=[],calls=[];const ctx={register:x=>registrations.push(x),onDispose:x=>disposals.push(x),rest:async(...args)=>calls.push(args)};plugin.default.register(ctx);assert.equal(registrations[0].area,'panes');assert.equal(registrations[0].data.placement,'right');disposals[0]();assert.equal(calls[0][0],'/control');assert.equal(calls[0][1].body.command,'stop')})
