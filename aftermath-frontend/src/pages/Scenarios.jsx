import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Plus, Search, Copy, Play, Info } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { getScenarios, createScenario } from '../services/scenarioService';
import { errMsg } from '../services/api';
import { Page, Loading, ErrorState, Empty, StatusBadge, DemoTag, Modal } from '../components/common/ui';

export default function Scenarios() {
  const nav = useNavigate();
  const s = useAsync(getScenarios);
  const [q, setQ] = useState('');
  const [cat, setCat] = useState('');
  const [dec, setDec] = useState('');
  const [sort, setSort] = useState('name');
  const [sel, setSel] = useState(null);

  const cats = [...new Set((s.data ?? []).map((x) => x.category))];
  const list = (s.data ?? [])
    .filter(
      (x) =>
        (x.name + x.id).toLowerCase().includes(q.toLowerCase()) &&
        (!cat || x.category === cat) &&
        (!dec || x.expected_decision === dec)
    )
    .sort((a, b) =>
      sort === 'name'
        ? a.name.localeCompare(b.name)
        : (b.last_run_at ?? '').localeCompare(a.last_run_at ?? '')
    );

  const dup = async (x) => {
    try {
      await createScenario({ ...x, id: x.id + '-COPY', name: x.name + ' (copy)' });
      toast.success('Scenario duplicated');
      s.reload();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <Page
      title="Security Scenarios"
      sub="Define and test repeatable behavioral boundaries, tool invocations, and invariants for AI agents."
      actions={
        <Link to="/scenarios/new" className="btn-p">
          <Plus size={16} />
          <span>Create Scenario</span>
        </Link>
      }
    >
      {/* Search and Filters Bar */}
      <div className="card space-y-3 p-5 md:p-6">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[220px]">
            <Search
              size={16}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              className="inp pl-11"
              placeholder="Search scenarios by name or ID…"
              aria-label="Search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>

          <select
            className="inp w-auto min-w-[150px]"
            value={cat}
            onChange={(e) => setCat(e.target.value)}
          >
            <option value="">All Categories</option>
            {cats.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>

          <select
            className="inp w-auto min-w-[150px]"
            value={dec}
            onChange={(e) => setDec(e.target.value)}
          >
            <option value="">Any Outcome</option>
            <option>ALLOWED</option>
            <option>DENIED</option>
          </select>

          <select
            className="inp w-auto min-w-[140px]"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="name">Sort: Name</option>
            <option value="date">Sort: Last Run</option>
          </select>
        </div>
      </div>

      {s.loading ? (
        <Loading />
      ) : s.error ? (
        <ErrorState msg={s.error} retry={s.reload} />
      ) : !list.length ? (
        <Empty
          title="No scenarios match the selected filters"
          hint="Try adjusting your filters or create a new security scenario to expand your test coverage."
        />
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {list.map((x) => (
            <div
              key={x.id}
              className="card flex flex-col justify-between space-y-4 hover:border-slate-300 transition-all duration-200"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="pill-black text-[10px] uppercase">{x.category}</span>
                    <h3 className="mt-2 text-lg font-bold text-slate-900">
                      {x.name} {x.demo && <DemoTag />}
                    </h3>
                    <div className="font-mono text-xs text-slate-400">ID: {x.id}</div>
                  </div>
                  <StatusBadge s={x.last_status} />
                </div>

                <p className="mt-3 text-sm text-slate-600 leading-relaxed">{x.description}</p>

                <div className="mt-4 flex flex-wrap items-center gap-2 text-xs font-mono">
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
                    Agent: <span className="font-bold">{x.agent}</span>
                  </span>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
                    Expected: <StatusBadge s={x.expected_decision} />
                  </span>
                  {x.last_run_at && (
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-500">
                      Last: {new Date(x.last_run_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100">
                <button
                  className="btn-p text-xs py-2 px-4"
                  onClick={() => nav('/run?scenario=' + x.id)}
                >
                  <Play size={13} />
                  <span>Run Test</span>
                </button>
                <button
                  className="btn-g text-xs py-2 px-4"
                  onClick={() => setSel(x)}
                >
                  <Info size={13} />
                  <span>Details</span>
                </button>
                <button
                  className="btn-g text-xs py-2 px-4"
                  onClick={() => dup(x)}
                >
                  <Copy size={13} />
                  <span>Duplicate</span>
                </button>
                <button
                  className="btn-g text-xs py-2 px-4 opacity-50 cursor-not-allowed"
                  disabled
                  title="Editing is not supported yet"
                >
                  Edit
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Scenario Details Modal */}
      {sel && (
        <Modal title={sel.name} onClose={() => setSel(null)}>
          <div className="space-y-4 text-sm">
            <p className="text-slate-600 leading-relaxed">{sel.description}</p>
            <div className="rounded-2xl border border-slate-100 bg-slate-50/70 p-4 space-y-2 text-xs font-mono">
              <p>
                <b className="text-slate-900">Synthetic Input:</b> {sel.request}
              </p>
              <p>
                <b className="text-slate-900">Action & Resource:</b> {sel.action} →{' '}
                <span className="text-slate-900 font-semibold">{sel.resource}</span>
              </p>
              <p>
                <b className="text-slate-900">Expected Tool Outcome:</b>{' '}
                {sel.expected_tool_outcome}
              </p>
              <p>
                <b className="text-slate-900">Expected Sandbox State:</b> {sel.expected_state}
              </p>
            </div>
            <div>
              <b className="text-xs font-mono uppercase tracking-wider text-slate-500">
                Security Invariants & Assertions
              </b>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-700">
                {sel.assertions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </div>
          </div>
        </Modal>
      )}
    </Page>
  );
}
