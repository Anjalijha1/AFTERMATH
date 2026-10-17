import { getRuns } from './runService';
// No dedicated evidence-search endpoint is proposed; the explorer filters runs client-side.
export const searchRuns = getRuns;
