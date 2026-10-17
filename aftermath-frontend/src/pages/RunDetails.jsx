import { useParams, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Play, Network, FileDown, CheckCircle2 } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { getRun, getEvents, startRun } from '../services/runService';
import { Page, Loading, ErrorState, StatusBadge, Table, DemoTag } from '../components/common/ui';
import EvidenceTimeline from '../components/evidence/EvidenceTimeline';

export default function RunDetails() {
  const { id = '' } = useParams();
  const r = useAsync(() => getRun(id), [id]);
  const e = useAsync(() => getEvents(id), [id]);

  if (r.loading) return <Loading />;
  if (r.error || !r.data)
    return <ErrorState msg={r.error ?? 'Run not found'} retry={r.reload} />;

  const x = r.data;

  return (
    <Page
      title={`Execution Details // ${x.id}`}
      sub={x.scenario_name}
      actions={
        <>
          <button
            className="btn-p"
            onClick={() =>
              startRun(x.scenario_id)
                .then((n) => toast.success('Started ' + n.id))
                .catch(() => toast.error('Replay failed'))
            }
          >
            <Play size={15} />
            <span>Replay Test</span>
          </button>
          <Link to="/graph" className="btn-g">
            <Network size={15} />
            <span>Consequence Graph</span>
          </Link>
          <button
            className="btn-g opacity-50 cursor-not-allowed"
            disabled
            title="Export not supported by backend"
          >
            <FileDown size={15} />
            <span>Export Report</span>
          </button>
        </>
      }
    >
      {/* High-Contrast Run Overview Cards */}
      <div className="card grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-100 bg-slate-50/60 p-4">
          <div className="font-mono text-xs uppercase tracking-wider text-slate-400">Target Agent</div>
          <div className="mt-1 font-mono font-bold text-slate-900">{x.agent}</div>
        </div>

        <div className="rounded-2xl border border-slate-100 bg-slate-50/60 p-4">
          <div className="font-mono text-xs uppercase tracking-wider text-slate-400">Executed At</div>
          <div className="mt-1 font-mono font-medium text-slate-800">
            {new Date(x.started_at).toLocaleString()}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-100 bg-slate-50/60 p-4">
          <div className="font-mono text-xs uppercase tracking-wider text-slate-400">Execution Duration</div>
          <div className="mt-1 font-mono font-bold text-slate-900">
            {x.duration_ms ? `${x.duration_ms} ms` : '—'}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-100 bg-slate-50/60 p-4">
          <div className="font-mono text-xs uppercase tracking-wider text-slate-400">Authorization Verdict</div>
          <div className="mt-1">
            <StatusBadge s={x.decision} />
          </div>
        </div>

        <div className="rounded-2xl border border-slate-100 bg-slate-50/60 p-4">
          <div className="font-mono text-xs uppercase tracking-wider text-slate-400">Tool Outcome</div>
          <div className="mt-1 font-mono font-semibold text-slate-800">{x.tool_outcome ?? 'Executed'}</div>
        </div>

        <div className="rounded-2xl border border-slate-100 bg-slate-50/60 p-4">
          <div className="font-mono text-xs uppercase tracking-wider text-slate-400">Backend Deterministic Verdict</div>
          <div className="mt-1 flex items-center gap-2">
            <StatusBadge s={x.status} /> {x.demo && <DemoTag />}
          </div>
        </div>
      </div>

      {/* Expected vs Observed Assertions */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Expected vs Observed Assertions</h2>
            <p className="text-xs text-slate-500">Security boundary invariants verified by deterministic engine</p>
          </div>
          <span className="pill-black text-[10px]">VERIFICATION SUITE</span>
        </div>

        {x.assertions?.length ? (
          <Table head={['Assertion Name', 'Expected Value', 'Observed Value', 'Verification Verdict']}>
            {x.assertions.map((a) => (
              <tr key={a.name} className="hover:bg-slate-50/80 transition-colors">
                <td className="px-5 py-4 font-semibold text-slate-900">{a.name}</td>
                <td className="px-5 py-4 font-mono text-xs text-slate-700">{a.expected}</td>
                <td className="px-5 py-4 font-mono text-xs text-slate-700">{a.observed}</td>
                <td className="px-5 py-4">
                  <StatusBadge s={a.status} />
                </td>
              </tr>
            ))}
          </Table>
        ) : (
          <div className="card text-sm text-slate-500">
            No assertion evidence supplied by the backend; this run is not verified.
          </div>
        )}
      </div>

      {/* Evidence Timeline */}
      <div className="space-y-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Deterministic Evidence Timeline</h2>
          <p className="text-xs text-slate-500">Chronological telemetry events captured during execution</p>
        </div>

        {e.loading ? (
          <Loading />
        ) : e.error ? (
          <ErrorState msg={e.error} retry={e.reload} />
        ) : (
          <EvidenceTimeline events={e.data ?? []} />
        )}
      </div>
    </Page>
  );
}
