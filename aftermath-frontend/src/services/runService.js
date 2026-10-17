import {demoRuns,demoEvents,demoScenarios} from './demo'
const dr=[...demoRuns]
export const getRuns=async()=>dr
export const startRun=async(scenario_id)=>{
 const s=demoScenarios.find(x=>x.id===scenario_id)
 const r={id:'RUN-D'+Date.now()%100000,scenario_id,scenario_name:s.name,agent:s.agent,decision:s.expected_decision,status:'PASS',started_at:new Date().toISOString(),duration_ms:1500,demo:true,assertions:[{name:'Authorization',expected:s.expected_decision,observed:s.expected_decision,status:'PASS'}]}
 dr.unshift(r);return r}
export const getRun=async(id)=>dr.find(r=>r.id===id)
export const getEvents=async(id)=>[...demoEvents(id)].sort((a,b)=>a.timestamp.localeCompare(b.timestamp))
