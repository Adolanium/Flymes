import { createRequire } from 'node:module'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
await import('./embed-avatar.mjs')
await import('./embed-native.mjs')
const here = dirname(fileURLToPath(import.meta.url))
const require = createRequire(process.env.FLYMES_NODE_MODULES ? resolve(process.env.FLYMES_NODE_MODULES, '../package.json') : import.meta.url)
const { build } = require('esbuild')
await build({entryPoints:[resolve(here,'harness.jsx')],bundle:true,format:'esm',outfile:resolve(here,'harness.bundle.js'),nodePaths:process.env.FLYMES_NODE_MODULES?[process.env.FLYMES_NODE_MODULES]:[],plugins:[{name:'host-stub',setup(b){b.onResolve({filter:/^@hermes\/plugin-sdk$/},()=>({path:'host-stub',namespace:'harness'}));b.onLoad({filter:/.*/,namespace:'harness'},()=>({contents:'export const host = {}'}))}}]})
console.log('Built browser harness. Serve desktop/ with a loopback HTTP server.')
