import {demoScenarios} from './demo'
let local=[...demoScenarios]
export const getScenarios=async()=>local
export const createScenario=async(s)=>{local=[{...s,demo:true},...local];return s}
