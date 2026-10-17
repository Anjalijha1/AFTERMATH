import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { createScenario } from '../services/scenarioService';
import { errMsg } from '../services/api';
import { Page } from '../components/common/ui';

const fields = [
  ['name', 'Scenario Name', true],
  ['description', 'Description', true],
  ['category', 'Category', true],
  ['agent', 'Target Agent', true],
  ['request', 'Synthetic Ticket / Request Prompt', true],
  ['action', 'Requested Action / Tool', true],
  ['resource', 'Target Resource', true],
  ['expected_tool_outcome', 'Expected Tool Outcome', true],
  ['expected_state', 'Expected Sandbox State', true],
  ['assertions', 'Security Invariants & Assertions (one per line)', true],
];

export default function CreateScenario() {
  const nav = useNavigate();
  const [v, setV] = useState({ expected_decision: 'DENIED' });
  const [err, setErr] = useState({});
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const e = {};
    fields.forEach(([k, , r]) => {
      if (r && !v[k]?.trim()) e[k] = 'This field is required';
    });
    setErr(e);
    if (Object.keys(e).length) return;

    setBusy(true);
    try {
      await createScenario({
        id: 'SCN-' + (Date.now() % 100000),
        name: v.name,
        description: v.description,
        category: v.category,
        agent: v.agent,
        request: v.request,
        action: v.action,
        resource: v.resource,
        expected_decision: v.expected_decision,
        expected_tool_outcome: v.expected_tool_outcome,
        expected_state: v.expected_state,
        assertions: v.assertions.split('\n').filter(Boolean),
      });
      toast.success('Scenario saved successfully');
      nav('/scenarios');
    } catch (x) {
      toast.error(errMsg(x));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page
      title="Create Security Scenario"
      sub="Configure structured scenario parameters for AI-agent deterministic evaluation."
    >
      <div className="card space-y-6">
        <div className="border-b border-slate-100 pb-4">
          <h2 className="text-base font-bold text-slate-900">Scenario Configuration</h2>
          <p className="text-xs text-slate-500">
            Authorization policies and safety guardrails will be evaluated against these specifications.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {fields.map(([k, l]) => (
            <label
              key={k}
              className={`block text-xs font-semibold text-slate-700 ${
                k === 'assertions' || k === 'description' ? 'md:col-span-2' : ''
              }`}
            >
              <div className="mb-1.5 flex items-center justify-between">
                <span>{l} *</span>
                {err[k] && <span className="font-mono text-rose-600">{err[k]}</span>}
              </div>
              {k === 'assertions' || k === 'description' ? (
                <textarea
                  className="inp min-h-[90px] py-3 font-normal"
                  rows={3}
                  placeholder={`Enter ${l.toLowerCase()}…`}
                  onChange={(e) => setV({ ...v, [k]: e.target.value })}
                />
              ) : (
                <input
                  className="inp font-normal"
                  placeholder={`Enter ${l.toLowerCase()}…`}
                  onChange={(e) => setV({ ...v, [k]: e.target.value })}
                />
              )}
            </label>
          ))}

          <label className="block text-xs font-semibold text-slate-700">
            <div className="mb-1.5">Expected Authorization Decision *</div>
            <select
              className="inp"
              value={v.expected_decision}
              onChange={(e) => setV({ ...v, expected_decision: e.target.value })}
            >
              <option>DENIED</option>
              <option>ALLOWED</option>
            </select>
          </label>
        </div>

        <div className="flex items-center gap-3 border-t border-slate-100 pt-6">
          <button className="btn-p" disabled={busy} onClick={submit}>
            {busy ? 'Saving Scenario…' : 'Save Scenario'}
          </button>
          <button className="btn-g" onClick={() => nav('/scenarios')}>
            Cancel
          </button>
        </div>
      </div>
    </Page>
  );
}
