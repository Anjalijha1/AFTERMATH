import { useAsync } from '../hooks/useAsync';
import { getRuns, getEvents } from '../services/runService';
import { Page, Loading, ErrorState, DemoTag } from '../components/common/ui';
import ConsequenceGraph from '../components/graph/ConsequenceGraph';
import { demoEvents } from '../services/demo';

export default function ConsequenceGraphPage() {
  const g = useAsync(async () => {
    const r = await getRuns();
    if (!r.length) return { ev: demoEvents('EXAMPLE'), example: true };
    return { ev: await getEvents(r[0].id), example: false };
  });

  if (g.loading) return <Loading />;
  if (g.error || !g.data)
    return <ErrorState msg={g.error ?? 'No data'} retry={g.reload} />;

  return (
    <Page
      title="Consequence Graph"
      sub="Observed action flow, tool execution hierarchy, and deterministic state transitions."
    >
      {g.data.example && (
        <div className="flex items-center gap-2 rounded-2xl border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-900">
          <DemoTag />
          <span>Example consequence graph rendered: no live execution telemetry recorded yet.</span>
        </div>
      )}
      <ConsequenceGraph events={g.data.ev} />
    </Page>
  );
}
