import { useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { RotateCcw, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { getScenarios } from '../services/scenarioService';
import { getRuns, startRun } from '../services/runService';
import { Page, Loading, ErrorState, Table, StatusBadge } from '../components/common/ui';

export default function RegressionLab() {
  const s = useAsync(getScenarios);
  const r = useAsync(getRuns);
  const [sel, setSel] = useState([]);
  const [busy, setBusy] = useState(false);

  if (s.loading || r.loading) return <Loading />;
  if (s.error || r.error)
    return <ErrorState msg={s.error || r.error} retry={() => { s.reload(); r.reload(); }} />;

  const runs = r.data ?? [];

  const run = async () => {
    setBusy(true);
    for (const id of sel) {
      try {
        await startRun(id);
      } catch {
        toast.error('Replay failed: ' + id);
      }
    }
    setBusy(false);
    r.reload();
    toast.success('Replays submitted');
  };

  return (
    <Page
      title="Regression Lab"
      sub="Continuous regression detection. Replay saved scenarios and compare current verdict against previous baseline."
      actions={
        <button
          className="btn-p"
          disabled={!sel.length || busy}
          onClick={run}
        >
          <RotateCcw size={16} className={busy ? 'animate-spin' : ''} />
          <span>Replay Selected ({sel.length})</span>
        </button>
      }
    >
      <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-xs text-slate-500 shadow-sm">
        <span className="font-mono font-bold text-slate-800">PIPELINE INFO:</span>
        <span>Selected scenarios are evaluated sequentially through deterministic agent governance.</span>
      </div>

      <Table head={['', 'Scenario', 'Previous Run', 'Current Run', 'Regression Flag', 'Last Evaluated', '']}>
        {(s.data ?? []).map((sc) => {
          const l = runs
            .filter((x) => x.scenario_id === sc.id)
            .sort((a, b) => b.started_at.localeCompare(a.started_at));
          const [c, p] = [l[0], l[1]];
          const reg = !!c && !!p && p.status === 'PASS' && c.status === 'FAIL';

          return (
            <tr key={sc.id} className="hover:bg-slate-50/80 transition-colors">
              <td className="px-5 py-4">
                <input
                  type="checkbox"
                  aria-label={sc.name}
                  className="h-4 w-4 rounded border-slate-300 text-black focus:ring-black"
                  checked={sel.includes(sc.id)}
                  onChange={(e) =>
                    setSel(
                      e.target.checked
                        ? [...sel, sc.id]
                        : sel.filter((i) => i !== sc.id)
                    )
                  }
                />
              </td>
              <td className="px-5 py-4">
                <div className="font-semibold text-slate-900">{sc.name}</div>
                <div className="font-mono text-xs text-slate-400">{sc.id}</div>
              </td>
              <td className="px-5 py-4">
                <StatusBadge s={p?.status} />
              </td>
              <td className="px-5 py-4">
                <StatusBadge s={c?.status} />
              </td>
              <td className="px-5 py-4">
                {reg ? (
                  <span className="inline-flex items-center gap-1 rounded-full border border-rose-300 bg-rose-50 px-2.5 py-0.5 text-xs font-bold text-rose-800">
                    <AlertTriangle size={12} />
                    REGRESSION
                  </span>
                ) : c && p ? (
                  <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800">
                    <CheckCircle2 size={12} />
                    Clean
                  </span>
                ) : (
                  <span className="text-xs font-mono text-slate-400">—</span>
                )}
              </td>
              <td className="px-5 py-4 text-xs font-mono text-slate-500">
                {c ? new Date(c.started_at).toLocaleDateString() : '—'}
              </td>
              <td className="px-5 py-4 text-right">
                {c && (
                  <Link
                    className="font-mono text-xs font-bold text-slate-950 hover:underline"
                    to={`/runs/${c.id}`}
                  >
                    Details →
                  </Link>
                )}
              </td>
            </tr>
          );
        })}
      </Table>
    </Page>
  );
}
