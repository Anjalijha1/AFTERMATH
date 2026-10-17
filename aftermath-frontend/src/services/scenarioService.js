import { demoScenarios } from './demo'
import * as live from './live'

const DEMO = import.meta.env.VITE_DEMO_MODE !== 'false'
let local = [...demoScenarios]

export const getScenarios = DEMO ? async () => local : live.getScenarios
export const createScenario = DEMO
  ? async (s) => {
      local = [{ ...s, demo: true }, ...local]
      return s
    }
  : live.createScenario
