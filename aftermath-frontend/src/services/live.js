// Live backend bridge (Member 1 FastAPI). Used when VITE_DEMO_MODE is not 'true'.
// Maps backend shapes (/api/...) to the shapes the pages already render.
const BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

const req = async (path, opts = {}) => {
  const r = await fetch(BASE + path, { headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!r.ok) {
    let msg = `HTTP ${r.status}`;
    try { msg = (await r.json()).error?.message || msg; } catch { /* keep status */ }
    throw new Error(msg);
  }
  return r.json();
};

const dec = (d) => (d === 'allowed' ? 'ALLOWED' : 'DENIED');
const cat = (a) => (a === 'change_account_email' ? 'Records' : 'Refunds');
const runStatus = (v) =>
  v.status === 'completed' ? v.verdict ?? 'ERROR' : v.status === 'failed' ? 'ERROR' : 'RUNNING';

export const getScenarios = async () =>
  (await req('/api/scenarios?limit=100')).items.map((x) => ({
    id: x.scenario_id,
    name: x.name,
    description: x.ticket,
    category: cat(x.action),
    agent: 'support-agent',
    request: x.ticket,
    action: x.action,
    resource: x.action === 'issue_refund' ? 'refunds' : 'customers',
    expected_decision: dec(x.expected_decision),
    expected_tool_outcome: x.expected_decision === 'allowed' ? 'Executed' : 'Blocked',
    expected_state: x.expected_decision === 'allowed' ? 'Expected state change occurs' : 'Sandbox unchanged',
    assertions: [
      x.expected_decision === 'allowed' ? 'Action must be authorized' : 'Action must be denied',
      'Protected state must not mutate',
    ],
    last_status: null,
    last_run_at: x.created_at,
    builtin: x.builtin,
  }));

export const createScenario = async (s) => {
  const amounts = (String(s.request).match(/\d+(?:\.\d{1,2})?/g) || []).map(Number);
  const isEmail = /email/i.test(s.action) || /email/i.test(s.resource);
  const body = {
    scenario_id: (s.name || 'scenario').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40).padEnd(3, '_'),
    name: s.name.slice(0, 80),
    action: isEmail ? 'change_account_email' : 'issue_refund',
    amount_minor: isEmail ? 0 : Math.round((amounts.length ? Math.max(...amounts) : 0) * 100) || 100,
    ticket: s.request,
    expected_decision: s.expected_decision === 'ALLOWED' ? 'allowed' : 'blocked',
  };
  await req('/api/scenarios', { method: 'POST', body: JSON.stringify(body) });
  return s;
};

const mapRun = (v) => ({
  id: v.run_id,
  scenario_id: v.input?.scenario_id ?? v.scenario_id,
  scenario_name: v.input?.scenario_id ?? v.scenario_id ?? '',
  agent: 'support-agent',
  decision: v.result ? dec(v.result.decision) : undefined,
  status: runStatus(v),
  started_at: v.started_at ?? v.created_at,
  duration_ms:
    v.started_at && v.finished_at
      ? Math.max(0, Date.parse(v.finished_at) - Date.parse(v.started_at))
      : undefined,
  tool_outcome: v.result ? (v.result.decision === 'allowed' ? 'Executed' : 'Blocked') : undefined,
  execution_mode: v.execution_mode,
  assertions: (v.result?.checks ?? []).map((c) => ({
    name: c.check,
    expected: 'true',
    observed: String(c.ok),
    status: c.ok ? 'PASS' : 'FAIL',
  })),
});

export const getRuns = async () =>
  (await req('/api/runs?limit=100')).items.map((r) =>
    mapRun({ ...r, input: { scenario_id: r.scenario_id }, verdict: r.verdict }),
  );

export const getRun = async (id) => mapRun(await req(`/api/runs/${id}`));

export const startRun = async (scenario_id) => {
  const r = await req('/api/runs', { method: 'POST', body: JSON.stringify({ scenario_id }) });
  return { id: r.run_id, scenario_id, status: 'RUNNING', execution_mode: r.execution_mode };
};

export const getEvents = async (id) =>
  (await req(`/api/runs/${id}/events`)).items.map((e) => ({
    id: `${id}-${e.sequence}`,
    run_id: id,
    type: e.event_type || e.kind,
    timestamp: e.timestamp,
    description: e.message,
    tool: e.data?.tool,
    decision: e.data?.decision ? dec(e.data.decision) : undefined,
    payload: e.data,
  }));
