import { useApp } from '../context/AppContext';
import { Page } from '../components/common/ui';
import { LockBadge } from '../components/common/CyberGraphics';

export default function Settings() {
  const { workspace } = useApp();

  return (
    <Page
      title="System Preferences"
      sub="Configure workspace parameters, cryptographic verification logs, and telemetry policies."
    >
      <div className="grid gap-6 md:grid-cols-2">
        <div className="card space-y-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="font-bold text-slate-900">Active Workspace Environment</h3>
              <p className="text-xs text-slate-500">Current target sandbox parameters</p>
            </div>
            <LockBadge />
          </div>

          <label className="block text-xs font-semibold text-slate-700">
            Selected Workspace
            <input
              className="inp mt-1.5 bg-slate-50 font-mono text-xs text-slate-600 cursor-not-allowed"
              disabled
              value={workspace?.name ?? 'No workspace selected'}
              placeholder="Select one in Workspaces"
            />
          </label>

          <label className="block text-xs font-semibold text-slate-700">
            Deterministic Engine Endpoint
            <input
              className="inp mt-1.5 bg-slate-50 font-mono text-xs text-slate-600 cursor-not-allowed"
              disabled
              value="https://api.aftermath.security/v2/sandbox/deterministic"
            />
          </label>

          <p className="text-xs text-slate-500 leading-relaxed">
            All data currently displayed is local sandbox sample data held in client memory. Resetting the session restores initial benchmark test states.
          </p>
        </div>

        <div className="card-dark flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <span className="pill-black text-[10px] uppercase">Security Level</span>
              <span className="font-mono text-xs text-emerald-400">DEFENSE 2030</span>
            </div>

            <h3 className="mt-4 text-xl font-bold text-white">Autonomous Agent Zero-Trust Guardrails</h3>
            <p className="mt-2 text-xs text-slate-400 leading-relaxed">
              Every tool invocation is intercepted and validated against immutable security invariants. Unauthorized state mutations are deterministically rejected at runtime.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-white/5 p-4 text-xs font-mono space-y-2 text-slate-300">
            <div className="flex justify-between">
              <span>Policy Enforcement:</span>
              <span className="text-emerald-400 font-bold">STRICT_DETERMINISTIC</span>
            </div>
            <div className="flex justify-between">
              <span>Telemetry Cryptographic Hash:</span>
              <span className="text-slate-400">SHA256_ACTIVE</span>
            </div>
          </div>
        </div>
      </div>
    </Page>
  );
}
