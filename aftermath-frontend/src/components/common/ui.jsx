import { Loader2, AlertTriangle, Inbox, X, ArrowDownRight } from 'lucide-react';

const badgeClasses = {
  PASS: 'bg-emerald-100 text-emerald-950 border border-emerald-300/70',
  ALLOWED: 'bg-emerald-100 text-emerald-950 border border-emerald-300/70',
  FAIL: 'bg-rose-100 text-rose-950 border border-rose-300/70',
  DENIED: 'bg-slate-900 text-white border border-slate-700',
  ERROR: 'bg-amber-100 text-amber-950 border border-amber-300/70',
  INCONCLUSIVE: 'bg-slate-100 text-slate-700 border border-slate-300',
  PENDING: 'bg-slate-100 text-slate-700 border border-slate-300',
  RUNNING: 'bg-sky-100 text-sky-950 border border-sky-300/70',
};

export const StatusBadge = ({ s }) => {
  const cls = badgeClasses[s ?? ''] ?? 'bg-slate-100 text-slate-700 border border-slate-200';
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-0.5 text-xs font-semibold tracking-wide ${cls}`}>
      {s === 'RUNNING' && <span className="h-1.5 w-1.5 rounded-full bg-sky-500 animate-ping" />}
      {s === 'PASS' && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />}
      {s === 'FAIL' && <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />}
      {s ?? '—'}
    </span>
  );
};

export const DemoTag = () => (
  <span
    className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-800 shadow-sm"
    title="Synthetic data, not a real security result"
  >
    DEMO
  </span>
);

export const Stat = ({ title, value, icon, hint, variant = 'default' }) => {
  if (variant === 'dark') {
    return (
      <div className="card-dark flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-slate-400">
          <span>{title}</span>
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/10 text-emerald-300">
            {icon}
          </span>
        </div>
        <div className="my-3 text-3xl font-extrabold tracking-tight text-white md:text-4xl">
          {value}
        </div>
        <div className="text-xs text-slate-400">{hint}</div>
      </div>
    );
  }

  if (variant === 'gradient') {
    return (
      <div className="card-gradient flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-slate-800">
          <span>{title}</span>
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-black/10 text-slate-900">
            {icon}
          </span>
        </div>
        <div className="my-3 text-3xl font-extrabold tracking-tight text-slate-950 md:text-4xl">
          {value}
        </div>
        <div className="text-xs text-slate-700">{hint}</div>
      </div>
    );
  }

  return (
    <div className="card flex flex-col justify-between">
      <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-slate-500">
        <span>{title}</span>
        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-100 text-slate-800">
          {icon}
        </span>
      </div>
      <div className="my-3 text-3xl font-extrabold tracking-tight text-slate-900 md:text-4xl">
        {value}
      </div>
      <div className="text-xs text-slate-500">{hint}</div>
    </div>
  );
};

export const Loading = () => (
  <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 p-10 text-slate-600">
    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
      <Loader2 className="animate-spin" size={24} />
    </div>
    <span className="text-xs font-mono font-medium uppercase tracking-wider">Loading System Data…</span>
  </div>
);

export const ErrorState = ({ msg, retry }) => (
  <div className="card flex flex-col items-center gap-4 py-10 text-center">
    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-rose-700">
      <AlertTriangle size={24} />
    </div>
    <div>
      <h3 className="font-bold text-slate-900">Encountered an Error</h3>
      <p className="mt-1 text-sm text-slate-600">{msg}</p>
    </div>
    {retry && (
      <button className="btn-p" onClick={retry}>
        Retry Request
      </button>
    )}
  </div>
);

export const Empty = ({ title, hint }) => (
  <div className="card flex flex-col items-center gap-2 py-12 text-center text-slate-500">
    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-700">
      <Inbox size={22} />
    </div>
    <b className="text-base font-bold text-slate-900">{title}</b>
    <span className="max-w-md text-sm text-slate-500">{hint}</span>
  </div>
);

export const Page = ({ title, sub, badge, actions, children }) => (
  <div className="space-y-8">
    <div className="card-dark relative overflow-hidden flex flex-wrap items-end justify-between gap-6">
      {/* Soft ambient glow inside the dark banner */}
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-emerald-500/10 blur-2xl" />

      <div className="space-y-2 relative z-10">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-slate-400">
            AFTERMATH SEC.
          </span>
          <span className="text-slate-600">/</span>
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-emerald-400">
            2030
          </span>
          {badge && <span className="ml-2">{badge}</span>}
        </div>
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-extrabold tracking-tight text-white md:text-4xl">
            {title}
          </h1>
          <ArrowDownRight className="text-emerald-400" size={28} />
        </div>
        {sub && <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">{sub}</p>}
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-3 relative z-10">
          {actions}
        </div>
      )}
    </div>
    {children}
  </div>
);

export function Modal({ title, onClose, children }) {
  return (
    <div
      role="dialog"
      aria-modal
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm"
    >
      <div className="card w-full max-w-xl animate-in fade-in zoom-in-95 duration-200">
        <div className="mb-4 flex items-center justify-between border-b border-slate-200/80 pb-3">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-black" />
            <b className="text-lg font-bold text-slate-900">{title}</b>
          </div>
          <button
            aria-label="Close"
            onClick={onClose}
            className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-800 transition"
          >
            <X size={18} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export const Table = ({ head, children }) => (
  <div className="card overflow-hidden p-0">
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50/80 text-xs font-mono uppercase tracking-wider text-slate-500">
          <tr>
            {head.map((h) => (
              <th key={h} className="px-5 py-3.5">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  </div>
);
