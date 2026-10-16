import {demoWorkspaces} from './demo'
let local=[...demoWorkspaces]
export const getWorkspaces=async()=>local
export const createWorkspace=async(w)=>{local=[{...w,demo:true},...local];return w}
