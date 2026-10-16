import { useState } from 'react';
import toast from 'react-hot-toast';
import { Plus, Check, FolderKanban, Server, Bot } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { useApp } from '../context/AppContext';
import { getWorkspaces, createWorkspace } from '../services/workspaceService';
import { errMsg } from '../services/api';
import { Page, Loading, ErrorState, Empty, Modal, DemoTag } from '../components/common/ui';

export default function Workspaces() {
  const { workspace, setWorkspace } = useApp();
  const w = useAsync(getWorkspaces);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: '', description: '', sandbox: 'sandbox-db', agent: '' });
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (!f.name.trim() || !f.agent.trim())
      return toast.error('Name and agent are required');
    setBusy(true);
    try {
      await createWorkspace({ ...f, id: 'ws-' + Date.now(), scenarios: 0 });
      toast.success('Workspace created');
      setOpen(false);
      w.reload();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page
      title="Workspaces"
      sub="Isolated execution environments for testing autonomous agent boundaries and permission sets."
      actions={
        <button className="btn-p" onClick={() => setOpen(true)}>
          <Plus size={16} />
          <span>Create Workspace</span>
        </button>
      }
    >
      {w.loading ? (
        <Loading />
      ) : w.error ? (
        <ErrorState msg={w.error} retry={w.reload} />
      ) : !w.data?.length ? (
        <Empty title="No workspaces found" hint="Create a workspace to isolate agent test scenarios." />
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {w.data.map((x) => {
            const isActive = workspace?.id === x.id;
            return (
              <div
                key={x.id}
                className={`card flex flex-col justify-between space-y-4 transition-all duration-200 ${
                  isActive ? 'ring-2 ring-slate-900 border-slate-900 shadow-md' : 'hover:border-slate-300'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold uppercase tracking-wider text-slate-400">
                      ID: {x.id}
                    </span>
                    {isActive ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-900">
                        <Check size={12} /> ACTIVE
                      </span>
                    ) : (
                      x.demo && <DemoTag />
                    )}
                  </div>

                  <h3 className="mt-3 text-lg font-bold text-slate-900">{x.name}</h3>
                  <p className="mt-1 text-sm text-slate-600 leading-relaxed">{x.description}</p>
                </div>

                <div className="space-y-4 pt-2">
                  <div className="rounded-2xl border border-slate-100 bg-slate-50/70 p-3 text-xs space-y-1 font-mono">
                    <div className="flex items-center justify-between text-slate-500">
                      <span>Sandbox:</span>
                      <span className="font-semibold text-slate-800">{x.sandbox}</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-500">
                      <span>Agent:</span>
                      <span className="font-semibold text-slate-800">{x.agent}</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-500">
                      <span>Scenarios:</span>
                      <span className="font-semibold text-slate-800">{x.scenarios} suites</span>
                    </div>
                  </div>

                  <button
                    className={`w-full ${isActive ? 'btn-g font-bold' : 'btn-p'}`}
                    onClick={() => {
                      setWorkspace(x);
                      toast.success(`Active workspace set to "${x.name}"`);
                    }}
                  >
                    {isActive ? 'Current Active Workspace' : 'Select & Activate'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {open && (
        <Modal title="Create New Workspace" onClose={() => setOpen(false)}>
          <div className="space-y-4 text-sm">
            {['name', 'description', 'sandbox', 'agent'].map((k) => (
              <label key={k} className="block text-xs font-semibold capitalize text-slate-700">
                {k} {(k === 'name' || k === 'agent') && <span className="text-rose-500">*</span>}
                <input
                  className="inp mt-1.5"
                  placeholder={`Enter workspace ${k}…`}
                  value={f[k]}
                  onChange={(e) => setF({ ...f, [k]: e.target.value })}
                />
              </label>
            ))}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
              <button className="btn-g" onClick={() => setOpen(false)}>
                Cancel
              </button>
              <button className="btn-p" disabled={busy} onClick={save}>
                {busy ? 'Saving…' : 'Save Workspace'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </Page>
  );
}
