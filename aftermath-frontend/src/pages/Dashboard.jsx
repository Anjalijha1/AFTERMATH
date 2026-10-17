import { Link, useNavigate } from 'react-router-dom';
import {
  Activity,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ShieldCheck,
  TrendingDown,
  ArrowRight,
  ShieldAlert,
  Cpu,
  Layers,
  ArrowDownRight,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { useAsync } from '../hooks/useAsync';
import { getRuns } from '../services/runService';
import { getScenarios } from '../services/scenarioService';
import {
  Stat,
  Loading,
  ErrorState,
  Empty,
  Table,
  StatusBadge,
  DemoTag,
} from '../components/common/ui';
import { CyberRobot, TechGlyph, LockBadge } from '../components/common/CyberGraphics';

export default function Dashboard() {
  const nav = useNavigate();
  const r = useAsync(getRuns);
  const s = useAsync(getScenarios);

  if (r.loading || s.loading) return <Loading />;
  if (r.error || !r.data)
    return <ErrorState msg={r.error ?? 'No data'} retry={r.reload} />;

  const runs = r.data;
  const c = (x) => runs.filter((a) => a.status === x).length;
  const byDay = Object.entries(
    runs.reduce((m, a) => {
      const d = a.started_at.slice(0, 10);
      m[d] = (m[d] ?? 0) + 1;
      return m;
    }, {})
  )
    .sort()
    .map(([d, n]) => ({ d: d.slice(5), n }));

  const pie = [
    { n: 'PASS', v: c('PASS'), c: '#10B981' },
    { n: 'FAIL', v: c('FAIL'), c: '#0B0F17' },
  ];

  // Regression = a scenario whose latest run FAILs while its previous run PASSed
  const reg = (s.data ?? []).filter((sc) => {
    const l = runs
      .filter((x) => x.scenario_id === sc.id)
      .sort((a, b) => b.started_at.localeCompare(a.started_at));
    return l.length > 1 && l[0].status === 'FAIL' && l[1].status === 'PASS';
  }).length;

  return (
    <div className="space-y-8">
      {/* Hero Section (Slide 2 & 4 dark contrast aesthetic with Cyber Robot mascot) */}
      <section className="card-dark relative overflow-hidden p-6 sm:p-8 md:p-12">
        {/* Soft pastel mint-cyan ambient glow in top-right corner */}
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl" />

        {/* Top Header metadata */}
        <div className="flex items-center justify-between font-mono text-xs font-bold uppercase tracking-[0.25em] text-slate-400">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span>AFTERMATH SEC.</span>
          </div>
          <span className="text-emerald-400">2030</span>
        </div>

        {/* Main Hero Grid */}
        <div className="mt-8 grid items-center gap-8 lg:grid-cols-12">
          <div className="space-y-6 lg:col-span-7">
            <div className="font-mono text-[11px] uppercase tracking-widest text-emerald-400/90">
              Pitch Deck Presentation // Autonomous Security
            </div>

            <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl lg:text-6xl leading-[1.08]">
              Cyber <TechGlyph />
              <br />
              Security
            </h1>

            {/* Pill Container */}
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-700 bg-white/10 px-4 py-1.5 text-xs font-semibold tracking-wider text-white">
                Cyber Security
              </span>
              <span className="rounded-full border border-slate-800 bg-white/5 px-4 py-1.5 text-xs font-medium text-slate-300">
                Trusted by 500+ organizations worldwide.
              </span>
            </div>

            <p className="max-w-xl text-sm leading-relaxed text-slate-300 sm:text-[15px]">
              Protecting your digital assets with next-generation threat intelligence, proactive defense systems, and zero-trust frameworks for agentic workflows.
            </p>

            {/* Hero CTAs */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                className="btn bg-white text-slate-950 font-bold hover:bg-slate-100 shadow-sm group"
                onClick={() => nav('/run')}
              >
                <span>Start Test Execution</span>
                <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
              </button>
              <Link
                to="/scenarios"
                className="inline-flex items-center rounded-full border border-slate-700 bg-white/10 px-6 py-2.5 text-sm font-semibold text-white hover:bg-white/20 transition"
              >
                View Scenarios
              </Link>
            </div>
          </div>

          {/* Right Column: Sleek 3D Robot Mascot */}
          <div className="flex justify-center lg:col-span-5 lg:justify-end">
            <CyberRobot className="h-64 w-64 sm:h-72 sm:w-72 lg:h-80 lg:w-80" />
          </div>
        </div>

        {/* Hero Footer Metadata */}
        <div className="mt-10 flex flex-wrap items-center justify-between border-t border-slate-800/80 pt-4 font-mono text-xs text-slate-400">
          <span>www.aftermath.security</span>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span>Deterministic AI Red-Teaming OS</span>
          </div>
        </div>
      </section>

      {/* High-Contrast Feature Cards (Slide 4 layout: Light, Jet Black, Pastel Gradient) */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Card 1: Light Card */}
        <div className="card flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="pill-black">Regulatory Compliance</span>
            <LockBadge />
          </div>
          <div className="my-4">
            <div className="text-2xl font-extrabold text-slate-950 md:text-3xl">
              Deterministic Verification
            </div>
            <p className="mt-2 text-xs leading-relaxed text-slate-500">
              Meeting SOC 2, HIPAA, and ISO 42001 AI governance standards with immutable cryptographic execution logs.
            </p>
          </div>
          <div className="font-mono text-xs font-semibold text-slate-600">
            {runs.length} Total Verified Runs
          </div>
        </div>

        {/* Card 2: Jet Black Card (Slide 4 style) */}
        <div className="card-dark flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-700 bg-white/10 px-3.5 py-1 text-xs font-semibold tracking-wide text-white">
              National Security
            </span>
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-400/20 text-emerald-300">
              <ShieldAlert size={16} />
            </span>
          </div>
          <div className="my-4">
            <div className="text-2xl font-extrabold text-white md:text-3xl">
              Zero-Trust Guardrails
            </div>
            <p className="mt-2 text-xs leading-relaxed text-slate-400">
              Defending critical infrastructure from unauthorized prompt injections, tool escalations, and state mutations.
            </p>
          </div>
          <div className="flex items-center justify-between font-mono text-xs text-slate-400">
            <span>Pass Rate</span>
            <span className="font-bold text-emerald-400">
              {runs.length ? Math.round((c('PASS') / runs.length) * 100) : 0}%
            </span>
          </div>
        </div>

        {/* Card 3: Pastel Mint-Cyan Gradient Card (Slide 4 style) */}
        <div className="card-gradient flex flex-col justify-between sm:col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-black px-3.5 py-1 text-xs font-bold text-white">
              Digital Transformation
            </span>
            <ArrowDownRight className="text-slate-800" size={20} />
          </div>
          <div className="my-4">
            <div className="text-2xl font-extrabold text-slate-950 md:text-3xl">
              Regression Defense
            </div>
            <p className="mt-2 text-xs leading-relaxed text-slate-700">
              Automated continuous evaluation detecting behavioral drift before vulnerable agents are promoted to production.
            </p>
          </div>
          <div className="flex items-center justify-between font-mono text-xs font-bold text-slate-900">
            <span>Active Regressions</span>
            <span className={reg > 0 ? 'text-rose-700' : 'text-emerald-800'}>
              {reg === 0 ? '0 Detected' : `${reg} Detected`}
            </span>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <Stat
          title="Total Runs"
          value={runs.length}
          icon={<Activity size={16} />}
          hint="All executions"
        />
        <Stat
          title="Passed"
          value={c('PASS')}
          icon={<CheckCircle2 size={16} />}
          hint="Backend verdict"
        />
        <Stat
          title="Failed"
          value={c('FAIL')}
          icon={<XCircle size={16} />}
          hint="Backend verdict"
        />
        <Stat
          title="Inconclusive"
          value={c('INCONCLUSIVE')}
          icon={<HelpCircle size={16} />}
          hint="Missing evidence"
        />
        <Stat
          title="Scenarios"
          value={s.data?.length ?? 0}
          icon={<ShieldCheck size={16} />}
          hint="Saved test suites"
        />
        <Stat
          title="Regressions"
          value={reg}
          icon={<TrendingDown size={16} />}
          hint="PASS → FAIL status"
          variant={reg > 0 ? 'default' : 'default'}
        />
      </div>

      {/* Visual Analytics Charts */}
      {!runs.length ? (
        <Empty title="No runs recorded yet" hint="Run a security scenario to populate real-time telemetry." />
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="card lg:col-span-2">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900">Executions per Day</h3>
                <p className="text-xs text-slate-500">Security test activity timeline</p>
              </div>
              <span className="pill-black text-[10px]">DAILY SOC FREQUENCY</span>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={byDay} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="d" stroke="#94A3B8" fontSize={11} tickLine={false} />
                  <YAxis allowDecimals={false} stroke="#94A3B8" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderRadius: '16px',
                      border: '1px solid #E2E8F0',
                      boxShadow: '0 10px 25px -5px rgba(0,0,0,0.05)',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="n" fill="#0B0F17" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card flex flex-col justify-between">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900">Verdict Ratio</h3>
                <p className="text-xs text-slate-500">PASS vs FAIL executions</p>
              </div>
              <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 font-mono text-[10px] font-bold text-emerald-800">
                SOC-2
              </span>
            </div>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pie}
                    dataKey="v"
                    nameKey="n"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                  >
                    {pie.map((p) => (
                      <Cell key={p.n} fill={p.c} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderRadius: '16px',
                      border: '1px solid #E2E8F0',
                      fontSize: '12px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 flex justify-center gap-6 border-t border-slate-100 pt-3 text-xs font-mono">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                <span className="text-slate-600">PASS: {c('PASS')}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-[#0B0F17]" />
                <span className="text-slate-600">FAIL: {c('FAIL')}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recent Executions Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-950">Recent Security Executions</h3>
            <p className="text-xs text-slate-500">Latest deterministic test runs</p>
          </div>
          <Link to="/evidence" className="text-xs font-mono font-semibold text-slate-700 hover:text-black">
            View All Evidence →
          </Link>
        </div>

        <Table head={['Run ID', 'Scenario', 'Agent', 'Authorization', 'Status', 'Date', '']}>
          {runs.slice(0, 8).map((x) => (
            <tr key={x.id} className="hover:bg-slate-50/80 transition-colors">
              <td className="px-5 py-4 font-mono font-medium text-slate-900">
                {x.id} {x.demo && <DemoTag />}
              </td>
              <td className="px-5 py-4 font-medium text-slate-800">{x.scenario_name}</td>
              <td className="px-5 py-4 font-mono text-xs text-slate-600">{x.agent}</td>
              <td className="px-5 py-4">
                <StatusBadge s={x.decision} />
              </td>
              <td className="px-5 py-4">
                <StatusBadge s={x.status} />
              </td>
              <td className="px-5 py-4 text-xs font-mono text-slate-500">
                {new Date(x.started_at).toLocaleDateString()}
              </td>
              <td className="px-5 py-4 text-right">
                <Link
                  className="inline-flex items-center gap-1 font-mono text-xs font-bold text-slate-950 hover:underline"
                  to={`/runs/${x.id}`}
                >
                  Details →
                </Link>
              </td>
            </tr>
          ))}
        </Table>
      </div>
    </div>
  );
}
