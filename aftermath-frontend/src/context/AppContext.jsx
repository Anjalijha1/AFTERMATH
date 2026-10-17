import {createContext,useContext,useState} from 'react'
const C=createContext(null)
export const useApp=()=>useContext(C)
export function AppProvider({children}){
 const [workspace,setWorkspace]=useState(null)
 return <C.Provider value={{workspace,setWorkspace}}>{children}</C.Provider>}
