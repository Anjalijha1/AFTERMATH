import {useEffect,useState} from 'react'
import {errMsg} from '../services/api'
export function useAsync(fn,deps=[]){
 const [data,setData]=useState(null);const [loading,setL]=useState(true);const [error,setE]=useState(null);const [n,setN]=useState(0)
 useEffect(()=>{let ok=true;setL(true);setE(null);fn().then(d=>ok&&setData(d)).catch(e=>ok&&setE(errMsg(e))).finally(()=>ok&&setL(false));return()=>{ok=false}},[...deps,n]) // eslint-disable-line
 return {data,loading,error,reload:()=>setN(x=>x+1)}}
