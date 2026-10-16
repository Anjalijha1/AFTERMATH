import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { CheckCircle2, Circle, ArrowRight, Play, ShieldAlert, Cpu } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { useApp } from '../context/AppContext';
import { getScenarios } from '../services/scenarioService';
import { startRun, getRun, getEvents, getRuns } from '../services/runService';
import { errMsg } from '../services/api';
import { Page, Loading, StatusBadge, DemoTag } from '../components/common/ui';

const stages = [
  ['Scenario initialized', /scenario_init/],
  ['Agent action proposed', /agent_action/],
  ['Governed tool invocation initiated', /tool_execution_started/],
  ['Authorization decision received', /authorization_/],
  ['Tool execution completed or denied', /tool_executed|authorization_denied/],
  ['Sandbox state verified', /state_verified/],
  ['Deterministic evaluation completed', /test_completed/],
];

export default function RunTest() {
  const [sp] = useSearchParams();
  const { workspace } = useApp();
  const s = useAsync(getScenarios);
  const [sid, setSid] = useState(sp.get('scenario') ?? '');
  const [run, setRun] = useState(null);
  const [ev, setEv] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const t = useRef();
  const sc = s.data?.find((x) => x.id === sid);

  const poll = (id) => {
    window.clearInterval(t.current);
    const tick = async () => {
      try {
        const r = await getRun(id);
        setRun(r);
        setEv(await getEvents(id).catch(() => []));
        if (r.status !== 'RUNNING' && r.status !== 'PENDING')
          window.clearInterval(t.current);
      } catch (e) {
        setErr(errMsg(e));
        window.clearInterval(t.current);
      }
    };
    tick();
    t.current = window.setInterval(tick, 2000);
  };

  useEffect(() => () => window.clearInterval(t.current), []);

  const go = async (id = sid) => {
    if (busy || !id) return;
    setBusy(true);
    setErr('');
    try {
      const r = await startRun(id, workspace?.id);
      setRun(r);
      poll(r.id);
    } catch (e) {
      setErr(errMsg(e));
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const replay = async () => {
    const rs = await getRuns();
    const l = rs.filter((r) => r.scenario_id === sid)[0];
    l ? go(l.scenario_id) : toast('No previous run for this scenario');
  };

  if (s.loading) return <Loading />;

  return (
    <Page
      title="Run Security Test"
      sub={`Active Workspace: ${workspace?.name ?? 'Default Sandbox'} · Continuous Telemetry Polling (2s)`}
    >
      <div className="card space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">Select Security Test Scenario</h2>
            <p className="text-xs text-slate-500">Pick an AI agent scenario to execute in the deterministic sandbox</p>
          </div>
          <span className="pill-black text-[10px]">EXECUTION RUNNER</span>
        </div>

        <div className="space-y-4">
          <select
            className="inp text-sm font-medium"
            aria-label="Scenario"
            value={sid}
            onChange={(e) => setSid(e.target.value)}
          >
            <option value="">Select scenario…</option>
            {s.data?.map((x) => (
              <option key={x.id} value={x.id}>
                {x.name} ({x.category})
              </option>
            ))}
          </select>

          {sc && (
            <div className="rounded-2xl border border-slate-200/90 bg-slate-50/70 p-5 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono text-xs font-bold text-slate-900">
                  {sc.name} {sc.demo && <DemoTag />}
                </span>
                <span className="font-mono text-xs text-slate-500">ID: {sc.id}</span>
              </div>
              <p className="text-sm text-slate-600 leading-relaxed">{sc.description}</p>
              <div className="flex flex-wrap items-center gap-3 pt-1 text-xs">
                <span className="rounded-full bg-white px-3 py-1 font-mono text-slate-700 shadow-sm border border-slate-200">
                  Agent: <span className="font-bold">{sc.agent}</span>
                </span>
                <span className="rounded-full bg-white px-3 py-1 font-mono text-slate-700 shadow-sm border border-slate-200">
                  Expected Decision: <StatusBadge s={sc.expected_decision} />
                </span>
                <span className="rounded-full bg-white px-3 py-1 font-mono text-slate-700 shadow-sm border border-slate-200">
                  Sandbox: {sc.expected_state}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Buttons */}
        <div className="flex flex-wrap items-center gap-3 pt-2">
          <button
            className="btn-p group"
            disabled={!sid || busy}
            onClick={() => go()}
          >
            <Play size={16} className={busy ? 'animate-spin' : ''} />
            <span>{busy ? 'Initiating Sandbox…' : 'Run Security Test'}</span>
            <ArrowRight size={15} className="transition-transform group-hover:translate-x-1" />
          </button>
          <button className="btn-g" disabled={!sid} onClick={replay}>
            Replay Previous Run
          </button>
          <Link to="/evidence" className="btn-g">
            View Evidence Explorer
          </Link>
          <button
            className="btn-g opacity-50 cursor-not-allowed"
            disabled
            title="Cancellation not supported by backend"
          >
            Cancel
          </button>
        </div>
      </div>

      {err && (
        <div className="card border-rose-200 bg-rose-50/60 p-5 text-sm text-rose-800">
          <b>Execution Error:</b> {err}
        </div>
      )}

      {run && (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Run status summary */}
          <div className="card space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <span className="font-mono text-sm font-bold text-slate-900">
                Run: {run.id} {run.demo && <DemoTag />}
              </span>
              <StatusBadge s={run.status} />
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between py-1 text-xs">
                <span className="text-slate-500 font-mono">Agent Target:</span>
                <span className="font-mono font-medium text-slate-900">{run.agent}</span>
              </div>
              <div className="flex justify-between py-1 text-xs">
                <span className="text-slate-500 font-mono">Decision Verdict:</span>
                <StatusBadge s={run.decision} />
              </div>
              <div className="flex justify-between py-1 text-xs">
                <span className="text-slate-500 font-mono">Latest Event:</span>
                <span className="font-mono font-medium text-slate-800">{ev.at(-1)?.type ?? 'scenario_init'}</span>
              </div>
            </div>

            <div className="pt-2">
              <Link
                className="btn-p w-full text-center"
                to={`/runs/${run.id}`}
              >
                Inspect Full Evidence Result →
              </Link>
            </div>
          </div>

          {/* Stepper stages */}
          <div className="card space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900">Deterministic Pipeline Stages</h3>
              <span className="font-mono text-xs text-slate-500">{stages.length} Stages</span>
            </div>

            <ul className="space-y-2.5 text-sm">
              {stages.map(([label, re]) => {
                const done = ev.some((e) => re.test(e.type));
                return (
                  <li
                    key={label}
                    className={`flex items-center gap-3 rounded-xl p-2.5 transition-colors ${
                      done ? 'bg-emerald-50/70 text-slate-900' : 'text-slate-400'
                    }`}
                  >
                    {done ? (
                      <CheckCircle2 size={18} className="text-emerald-600 shrink-0" />
                    ) : (
                      <Circle size={18} className="text-slate-300 shrink-0" />
                    )}
                    <span className={`text-xs font-medium ${done ? 'font-semibold text-slate-900' : 'text-slate-500'}`}>
                      {label}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
    </Page>
  );
}
