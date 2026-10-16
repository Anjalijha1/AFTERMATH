import { useState } from 'react';
import { ReactFlow, Background, Controls, Handle, Position } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const color = {
  pass: 'border-emerald-500 bg-emerald-50 text-emerald-950 ring-2 ring-emerald-400/20',
  fail: 'border-rose-500 bg-rose-50 text-rose-950 ring-2 ring-rose-400/20',
  neutral: 'border-slate-300 bg-white text-slate-800 shadow-sm',
};

function EvNode({ data }) {
  const d = data;
  return (
    <div
      className={`rounded-2xl border-2 px-4 py-2.5 font-mono text-xs font-semibold shadow-sm transition-all ${
        color[d.kind] ?? color.neutral
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-400 !w-2 !h-2" />
      <div className="flex items-center gap-1.5">
        <span
          className={`h-2 w-2 rounded-full ${
            d.kind === 'pass'
              ? 'bg-emerald-500'
              : d.kind === 'fail'
              ? 'bg-rose-500'
              : 'bg-slate-400'
          }`}
        />
        <span>{d.label}</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-slate-400 !w-2 !h-2" />
    </div>
  );
}

const types = { ev: EvNode };

export default function ConsequenceGraph({ events }) {
  const [sel, setSel] = useState(null);

  const nodes = events.map((e, i) => ({
    id: e.id,
    type: 'ev',
    position: { x: e.type.includes('denied') ? 220 : 0, y: i * 95 },
    data: {
      label: e.type,
      kind: e.type.includes('denied')
        ? 'fail'
        : e.type === 'state_verified' || e.type === 'tool_executed'
        ? 'pass'
        : 'neutral',
      ev: e,
    },
  }));

  const edges = events.slice(1).map((e, i) => ({
    id: 'e' + i,
    source: events[i].id,
    target: e.id,
    label: 'flow',
    style: { stroke: '#94A3B8', strokeWidth: 2 },
  }));

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
      <div className="card h-[65vh] min-h-[460px] overflow-hidden p-0">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={types}
          fitView
          colorMode="light"
          onNodeClick={(_, n) => setSel(n)}
        >
          <Background color="#CBD5E1" gap={18} size={1} />
          <Controls showFitView className="!rounded-xl !border-slate-200 !shadow-sm" />
        </ReactFlow>
      </div>

      <div className="card flex flex-col justify-between text-sm">
        <div>
          <div className="border-b border-slate-100 pb-3">
            <h3 className="font-bold text-slate-900">Execution Node Details</h3>
            <p className="text-xs text-slate-500">Inspect payload and state mutations</p>
          </div>

          {sel ? (
            <div className="mt-4 space-y-3 font-mono text-xs">
              <div className="rounded-xl bg-slate-50 p-3 border border-slate-200">
                <div className="text-slate-400 uppercase text-[10px]">Event Type</div>
                <div className="font-bold text-slate-900 text-sm mt-0.5">{sel.data.label}</div>
              </div>
              <div className="rounded-xl border border-slate-800 bg-[#0B0F17] p-3 text-emerald-300 overflow-x-auto max-h-[300px]">
                <pre>{JSON.stringify(sel.data.ev, null, 2)}</pre>
              </div>
            </div>
          ) : (
            <div className="mt-8 text-center text-slate-400 space-y-2">
              <p className="text-xs">Click any graph node to inspect verified telemetry payload.</p>
              <p className="text-[11px] text-slate-400">Edges denote observed chronological event order.</p>
            </div>
          )}
        </div>

        <div className="mt-4 border-t border-slate-100 pt-3 text-[11px] font-mono text-slate-400">
          Deterministic Flow Verification
        </div>
      </div>
    </div>
  );
}
