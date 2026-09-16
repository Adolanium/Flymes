import assert from 'node:assert/strict'
import {spawn} from 'node:child_process'
import {mkdtemp,readFile,mkdir,rm} from 'node:fs/promises'
import {createServer} from 'node:net'
import {tmpdir} from 'node:os'
import {dirname,resolve,join} from 'node:path'
import {fileURLToPath} from 'node:url'
import {chromium} from 'playwright'

const here=dirname(fileURLToPath(import.meta.url)),root=resolve(here,'..')
const scratch=await mkdtemp(join(tmpdir(),'flymes-arena-browser-'))
const socket=createServer();await new Promise(done=>socket.listen(0,'127.0.0.1',done))
const port=socket.address().port;await new Promise(done=>socket.close(done))
const python=process.env.FLYMES_TEST_PYTHON||resolve(root,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python')
const code="from pathlib import Path; import sys,uvicorn; from flymes.server import create_app; root=Path.cwd(); uvicorn.run(create_app(root,Path(sys.argv[2])/'missing', 'test-arena-'*5,state_root=Path(sys.argv[2])/'state'),host='127.0.0.1',port=int(sys.argv[1]),log_level='error')"
const child=spawn(python,['-c',code,String(port),scratch],{cwd:root,windowsHide:true,env:{...process.env,HERMES_HOME:join(scratch,'home')},stdio:['ignore','pipe','pipe']})
let logs='',browser
child.stdout.on('data',data=>logs+=data);child.stderr.on('data',data=>logs+=data)
const headers={Authorization:'Bearer '+'test-arena-'.repeat(5),'Content-Type':'application/json'}
try{
  for(let attempt=0;;attempt++){
    try{if((await fetch(`http://127.0.0.1:${port}/arena/state`,{headers})).ok)break}catch{}
    if(attempt>100)throw Error('Companion did not start: '+logs)
    await new Promise(done=>setTimeout(done,100))
  }
  browser=await chromium.launch({headless:true})
  const page=await browser.newPage({viewport:{width:440,height:1100},reducedMotion:'reduce'})
  const errors=[];page.on('pageerror',error=>errors.push(error.message))
  await page.route('http://flymes.test/**',async route=>{
    const url=new URL(route.request().url())
    if(url.pathname.startsWith('/__arena/')){
      const response=await fetch(`http://127.0.0.1:${port}${url.pathname.slice(8)}`,{method:route.request().method(),headers,body:route.request().postData()||undefined})
      return route.fulfill({status:response.status,contentType:'application/json',body:await response.text()})
    }
    const name=url.pathname==='/'?'arena-harness.html':url.pathname.slice(1)
    if(!['arena-harness.html','arena-harness.bundle.js'].includes(name))return route.fulfill({status:404,body:''})
    return route.fulfill({contentType:name.endsWith('.js')?'text/javascript':'text/html',body:await readFile(join(here,name))})
  })
  await page.goto('http://flymes.test/')
  await page.waitForFunction(()=>document.querySelector('.fa-panel .fm-state')?.textContent==='IDLE')
  assert.equal(await page.getByRole('option',{name:'Connectome',exact:true}).getAttribute('disabled'),'')
  await page.getByLabel('Move limit',{exact:true}).fill('10')
  await page.getByRole('button',{name:'Run arena',exact:true}).click()
  await page.getByRole('button',{name:'Pause',exact:true}).waitFor()
  await page.getByRole('button',{name:'Pause',exact:true}).click()
  await page.getByRole('button',{name:'Resume',exact:true}).waitFor()
  await page.getByRole('button',{name:'Resume',exact:true}).click()
  await page.waitForFunction(()=>document.querySelector('.fa-panel .fm-state')?.textContent==='COMPLETED')
  await page.getByRole('button',{name:'Compare controllers',exact:true}).click()
  await page.waitForFunction(()=>document.querySelector('.fa-panel')?.textContent.includes('6 of 6 episodes recorded'))
  assert.equal(await page.locator('.fa-results tbody tr').count(),2)
  const reportPromise=page.waitForEvent('download')
  await page.getByRole('button',{name:'Save report',exact:true}).click()
  const reportDownload=await reportPromise
  const report=JSON.parse(await readFile(await reportDownload.path(),'utf8'))
  assert.equal(report.rows.length,6)
  assert.equal(report.graph_sha256,null)
  await page.getByText('Individual episodes and replay',{exact:true}).click()
  await page.getByRole('button',{name:'Replay',exact:true}).first().click()
  await page.waitForFunction(()=>document.querySelector('.fa-panel .fm-state')?.textContent==='RECORDED REPLAY')
  await page.getByLabel('Replay frame 0 of 10',{exact:true}).fill('7')
  await page.locator('.fa-panel').evaluate(el=>el.scrollTop=0)
  await mkdir(join(here,'review'),{recursive:true})
  for(const width of [440,360]){
    await page.setViewportSize({width,height:1100})
    await page.screenshot({path:join(here,`review/arena-${width}.png`)})
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)
    assert.equal(await page.locator('.fa-panel').evaluate(el=>el.scrollWidth>el.clientWidth),false)
  }
  const replayPromise=page.waitForEvent('download')
  await page.getByRole('button',{name:'Save replay',exact:true}).click()
  const downloaded=await replayPromise
  const replay=await readFile(await downloaded.path())
  await page.getByRole('button',{name:'Back to experiment',exact:true}).click()
  await page.locator('input[type=file]').setInputFiles({name:'replay.json',mimeType:'application/json',buffer:replay})
  await page.waitForFunction(()=>document.querySelector('.fa-panel .fm-state')?.textContent==='RECORDED REPLAY')
  assert.deepEqual(errors,[])
  console.log('PASS: live arena, pause/resume, paired comparison, report export, replay save/import, and 440/360 px layouts')
}finally{
  if(browser)await browser.close()
  child.kill()
  await new Promise(done=>{if(child.exitCode!==null)done();else child.once('exit',done)})
  // scratch is an absolute directory created by mkdtemp for this test only.
  assert.ok(scratch.startsWith(join(tmpdir(),'flymes-arena-browser-')))
  await rm(scratch,{recursive:true,force:true})
}
