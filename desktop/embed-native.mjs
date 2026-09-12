import {readFile,writeFile} from 'node:fs/promises'
const path=new URL('./plugin.js',import.meta.url)
const source=await readFile(path,'utf8')
const panel=await readFile(new URL('./native-panel.js',import.meta.url),'utf8')
const marker=/\/\/ BEGIN NATIVE PANEL[\s\S]*?\/\/ END NATIVE PANEL/
if(!marker.test(source))throw Error('Native panel marker missing')
await writeFile(path,source.replace(marker,`// BEGIN NATIVE PANEL\n${panel}\n// END NATIVE PANEL`),'utf8')
