import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, ArrowUpDown, Filter } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { searchRuns } from '../services/evidenceService';
import { Page, Loading, ErrorState, Empty, Table, StatusBadge } from '../components/common/ui';

export default function EvidenceExplorer() {
  const r = useAsync(searchRuns);
  const [q, setQ] = useState('');
  const [st, setSt] = useState('');
  const [dec, setDec] = useState('');
  const [from, setFrom] = useState('');
  const [asc, setAsc] = useState(false);

  if (r.loading) return <Loading />;
  if (r.error) return <ErrorState msg={r.error} retry={r.reload} />;

  const list = (r.data ?? [])
    .filter(
      (x) =>
        (x.id + x.scenario_name).toLowerCase().includes(q.toLowerCase()) &&
        (!st || x.status === st) &&
        (!dec || x.decision === dec) &&
        (!from || x.started_at.slice(0, 10) >= from)
    )
    .sort(
      (a, b) =>
        (asc ? 1 : -1) * a.started_at.localeCompare(b.started_at)
    );

  return (
    <Page
      title="Evidence Explorer"
      sub="Query and inspect deterministic execution evidence, authorization logs, and cryptographic proofs."
    >
      {/* Search and Filters Card */}
      <div className="card space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3 text-xs font-mono font-bold uppercase tracking-wider text-slate-500">
          <Filter size={14} />
          <span>Search & Telemetry Filters</span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[240px]">
            <Search
              size={16}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              className="inp pl-11"
              placeholder="Search by Run ID or Scenario Name…"
              aria-label="Search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>

          <select
            className="inp w-auto min-w-[140px]"
            value={st}
            onChange={(e) => setSt(e.target.value)}
          >
            <option value="">All Results</option>
            {['PASS', 'FAIL', 'ERROR', 'INCONCLUSIVE'].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>

          <select
            className="inp w-auto min-w-[160px]"
            value={dec}
            onChange={(e) => setDec(e.target.value)}
          >
            <option value="">All Authorizations</option>
            <option>ALLOWED</option>
            <option>DENIED</option>
          </select>

          <input
            type="date"
            className="inp w-auto"
            aria-label="From date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />

          <button className="btn-g" onClick={() => setAsc(!asc)}>
            <ArrowUpDown size={15} />
            <span>Sort: {asc ? 'Oldest' : 'Newest'}</span>
          </button>
        </div>
      </div>

      {!list.length ? (
        <Empty
          title="No runs match the specified filters"
          hint="Try adjusting your search criteria or resetting filters to see available evidence records."
        />
      ) : (
        <Table
          head={[
            'Run ID',
            'Scenario',
            'Authorization Verdict',
            'Deterministic Status',
            'Execution Timestamp',
            '',
          ]}
        >
          {list.map((x) => (
            <tr key={x.id} className="hover:bg-slate-50/80 transition-colors">
              <td className="px-5 py-4 font-mono font-medium text-slate-900">{x.id}</td>
              <td className="px-5 py-4 font-medium text-slate-800">{x.scenario_name}</td>
              <td className="px-5 py-4">
                <StatusBadge s={x.decision} />
              </td>
              <td className="px-5 py-4">
                <StatusBadge s={x.status} />
              </td>
              <td className="px-5 py-4 text-xs font-mono text-slate-500">
                {new Date(x.started_at).toLocaleString()}
              </td>
              <td className="px-5 py-4 text-right">
                <Link
                  className="font-mono text-xs font-bold text-slate-950 hover:underline"
                  to={`/runs/${x.id}`}
                >
                  Open Evidence →
                </Link>
              </td>
            </tr>
          ))}
        </Table>
      )}
    </Page>
  );
}
