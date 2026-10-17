import { useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderKanban,
  ShieldCheck,
  Play,
  RotateCcw,
  Search,
  Network,
  Settings,
  Menu,
  PanelLeft,
  Bell,
  User,
  Shield,
  Sparkles,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

const nav = [
  ['/', 'Dashboard', LayoutDashboard],
  ['/workspaces', 'Workspaces', FolderKanban],
  ['/scenarios', 'Scenarios', ShieldCheck],
  ['/run', 'Run Tests', Play],
  ['/regression', 'Regression Lab', RotateCcw],
  ['/evidence', 'Evidence Explorer', Search],
  ['/graph', 'Consequence Graph', Network],
  ['/settings', 'Settings', Settings],
];

export default function AppLayout() {
  const [open, setOpen] = useState(false);
  const [mini, setMini] = useState(false);
  const { workspace } = useApp();
  const loc = useLocation();
  const crumbs = loc.pathname.split('/').filter(Boolean);

  return (
    <div className="flex min-h-screen bg-ink">
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-slate-950/70 backdrop-blur-sm lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Clean Light Sidebar extending full height */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-screen flex-col border-r border-slate-200/90 bg-white/95 p-4 text-slate-800 backdrop-blur-md transition-all duration-300 lg:sticky lg:top-0 lg:h-screen lg:shrink-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0 ${mini ? 'lg:w-20' : 'w-64'}`}
      >
        {/* Brand Header */}
        <div className="mb-6 flex items-center justify-between px-2 pt-2 pb-1">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500 shadow-[0_0_12px_#10b981]" />
            </span>
            {!mini && (
              <div>
                <div className="font-mono text-sm font-extrabold tracking-[0.2em] text-slate-950">
                  AFTERMATH CO.
                </div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-slate-400">
                  DEFENSE OS · 2030
                </div>
              </div>
            )}
          </div>
          {!mini && (
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[9px] font-mono font-medium text-slate-500">
              v2.4
            </span>
          )}
        </div>

        {/* Navigation list */}
        <nav className="flex-1 space-y-1.5 overflow-y-auto pr-1">
          {nav.map(([to, label, Icon]) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-full px-4 py-2.5 text-sm transition-all duration-200 ${
                  isActive
                    ? 'bg-black font-semibold text-white shadow-sm'
                    : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-950'
                }`
              }
            >
              <Icon size={18} className="shrink-0" />
              {!mini && <span className="truncate">{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Sidebar Footer */}
        <div className="space-y-3 border-t border-slate-200/80 pt-4 text-xs">
          <button
            className="hidden items-center gap-2 text-slate-500 hover:text-slate-900 transition lg:flex"
            onClick={() => setMini(!mini)}
          >
            <PanelLeft size={16} />
            {!mini && <span className="font-mono text-[11px] uppercase tracking-wider">Collapse Sidebar</span>}
          </button>

          {!mini && (
            <div className="rounded-2xl border border-slate-200/80 bg-slate-50/80 p-3">
              <div className="font-mono text-[10px] uppercase tracking-widest text-slate-400">
                Active Workspace
              </div>
              <div className="mt-1 truncate font-semibold text-slate-900">
                {workspace?.name ?? 'Default Sandbox'}
              </div>
            </div>
          )}

          <div className="flex items-center gap-2.5 px-1 py-1">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-slate-800">
              <User size={15} />
            </span>
            {!mini && (
              <div className="truncate">
                <div className="font-medium text-slate-900">Security Lead</div>
                <div className="font-mono text-[10px] text-slate-400">Autonomous Defense</div>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <div className="min-w-0 flex-1 flex flex-col">
        {/* Top Header Bar */}
        <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-slate-200/80 bg-white/80 px-6 backdrop-blur-md">
          <button
            className="rounded-full p-1 text-slate-600 hover:bg-slate-100 lg:hidden"
            aria-label="Open menu"
            onClick={() => setOpen(true)}
          >
            <Menu size={22} />
          </button>

          {/* Breadcrumbs */}
          <div className="flex items-center gap-2 font-mono text-xs text-slate-500">
            <span className="font-bold tracking-wider text-slate-900">AFTERMATH</span>
            {crumbs.map((c) => (
              <span key={c} className="flex items-center gap-2">
                <span className="text-slate-300">/</span>
                <span className="font-semibold capitalize text-slate-800">{c}</span>
              </span>
            ))}
          </div>

          {/* Top Right Badges */}
          <div className="ml-auto flex items-center gap-3">
            {workspace && (
              <span className="hidden rounded-full border border-slate-200 bg-white px-3 py-1 font-mono text-xs text-slate-600 shadow-sm sm:inline-block">
                {workspace.name}
              </span>
            )}
            <span className="inline-flex items-center gap-1.5 rounded-full bg-black px-3 py-1 text-[11px] font-mono font-bold tracking-wider text-white shadow-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              SANDBOX 2030
            </span>
            <span className="hidden rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-[11px] font-bold text-amber-800 sm:inline-block">
              SAMPLE DATA
            </span>
            <div className="relative">
              <button
                aria-label="Notifications"
                className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 transition shadow-sm"
              >
                <Bell size={16} />
              </button>
              <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-emerald-500" />
            </div>
          </div>
        </header>

        {/* Page Content Body */}
        <main className="mx-auto w-full max-w-7xl flex-1 p-6 md:p-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
