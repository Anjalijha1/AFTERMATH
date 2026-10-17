import { useState } from 'react';
import { StatusBadge, Empty } from '../common/ui';

const F = {
  All: () => true,
  Agent: (e) => e.type.startsWith('agent'),
  Authorization: (e) => e.type.startsWith('authorization'),
  Tool: (e) => e.type.startsWith('tool'),
  State: (e) => e.type.startsWith('state'),
  Errors: (e) => /error|fail/i.test(e.type + (e.status ?? '')),
};

export default function EvidenceTimeline({ events }) {
  const [f, setF] = useState('All');
  const list = events.filter(F[f]);

  return (
    <div className="space-y-4">
      {/* Category Pills */}
      <div className="flex flex-wrap items-center gap-2">
        {Object.keys(F).map((k) => (
          <button
            key={k}
            onClick={() => setF(k)}
            className={`rounded-full px-4 py-1.5 text-xs font-semibold tracking-wide transition-all ${
              f === k
                ? 'bg-black text-white shadow-sm'
                : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            {k}
          </button>
        ))}
      </div>

      {!list.length ? (
        <Empty
          title="No events match this filter"
          hint="Only events received and verified by the deterministic backend are displayed."
        />
      ) : (
        <ol className="relative space-y-4 border-l-2 border-slate-200 ml-3 pl-6">
          {list.map((e) => (
            <li key={e.id} className="card relative transition-all">
              {/* Timeline Node Indicator */}
              <span className="absolute -left-[31px] top-7 flex h-4 w-4 items-center justify-center rounded-full bg-white ring-2 ring-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
              </span>

              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-slate-900">{e.type}</span>
                  {e.decision && <StatusBadge s={e.decision} />}
                </div>
                <span className="font-mono text-xs text-slate-400">
                  {new Date(e.timestamp).toLocaleTimeString()}
                </span>
              </div>

              <p className="mt-2 text-sm text-slate-700 leading-relaxed">{e.description}</p>
              
              <div className="mt-2 flex flex-wrap items-center gap-2 font-mono text-xs text-slate-500">
                <span>Run ID: {e.run_id}</span>
                {e.tool && <span>· Tool: <span className="font-semibold text-slate-800">{e.tool}</span></span>}
                <span>· Observed Evidence</span>
              </div>

              <details className="mt-3 text-xs">
                <summary className="cursor-pointer font-mono font-bold text-slate-900 hover:underline">
                  View Cryptographic / Structured Payload
                </summary>
                <pre className="mt-2 overflow-x-auto rounded-2xl border border-slate-800 bg-[#0B0F17] p-4 font-mono text-[11px] text-emerald-300">
                  {JSON.stringify(e.payload ?? {}, null, 2)}
                </pre>
              </details>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
