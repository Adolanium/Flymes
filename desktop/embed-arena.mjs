import {readFile,writeFile} from 'node:fs/promises'
const path=new URL('./plugin.js',import.meta.url)
const source=await readFile(path,'utf8')
const panel=await readFile(new URL('./arena-panel.js',import.meta.url),'utf8')
const marker=/\/\/ BEGIN ARENA PANEL[\s\S]*?\/\/ END ARENA PANEL/
if(!marker.test(source))throw Error('Arena panel marker missing')
await writeFile(path,source.replace(marker,`// BEGIN ARENA PANEL\n${panel}\n// END ARENA PANEL`),'utf8')
