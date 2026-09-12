import {readFile,writeFile} from 'node:fs/promises'
const path=new URL('./plugin.js',import.meta.url)
const source=await readFile(path,'utf8')
const avatar=await readFile(new URL('./fly-avatar.js',import.meta.url),'utf8')
const marker=/\/\/ BEGIN FLY AVATAR[\s\S]*?\/\/ END FLY AVATAR/
if(!marker.test(source))throw Error('Fly avatar marker missing')
await writeFile(path,source.replace(marker,`// BEGIN FLY AVATAR\n${avatar}\n// END FLY AVATAR`),'utf8')
