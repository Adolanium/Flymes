import React from 'react'
import {createRoot} from 'react-dom/client'
import {FlymesPanel} from './plugin.js'

// Browser tests supply an authenticated proxy. This page contains no bearer token.
const ctx={rest:async(path,options={})=>{
  const response=await fetch(`/__arena${path}`,{method:options.method||'GET',
    headers:{'Content-Type':'application/json'},body:options.body?JSON.stringify(options.body):undefined})
  const value=await response.json()
  if(!response.ok)throw Error(typeof value.detail==='string'?value.detail:'Arena request failed')
  return value
}}
createRoot(document.querySelector('#root')).render(<FlymesPanel ctx={ctx} initialView="arena"/> )
