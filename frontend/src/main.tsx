import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Link, NavLink, Route, Routes, useParams } from "react-router-dom";
import ReactECharts from "echarts-for-react";
import { CBadge } from "@coreui/react";
import { Activity, BookOpen, Brain, CandlestickChart, Database, HeartPulse, Library, LineChart, ShieldCheck } from "lucide-react";
import "@coreui/coreui/dist/css/coreui.min.css";
import "admin-lte/dist/css/adminlte.min.css";
import "./styles.css";

const apiBase = import.meta.env.VITE_API_BASE ?? "";

type Row = Record<string, string | number | boolean>;

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`);
  if (!response.ok) throw new Error(`Request failed: ${path}`);
  return response.json() as Promise<T>;
}

function useApi<T>(path: string): T | null {
  const [data, setData] = React.useState<T | null>(null);
  React.useEffect(() => {
    let active = true;
    getJson<T>(path).then((payload) => active && setData(payload));
    const timer = window.setInterval(() => {
      getJson<T>(path).then((payload) => active && setData(payload));
    }, 30000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [path]);
  return data;
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-wrapper dashboard-shell min-h-screen bg-slate-950 text-slate-100" data-bs-theme="dark">
        <div className="dashboard-frame">
          <Sidebar />
          <main className="dashboard-main min-h-screen">
            <Header />
            <section className="app-content dashboard-content px-5 py-4 lg:px-8">
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/research" element={<Research />} />
                <Route path="/strategies" element={<Strategies />} />
                <Route path="/strategies/:id" element={<StrategyDetail />} />
                <Route path="/portfolio" element={<Portfolio />} />
                <Route path="/paper" element={<Paper />} />
                <Route path="/operations" element={<Operations />} />
                <Route path="/knowledge" element={<Knowledge />} />
              </Routes>
            </section>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

function Sidebar() {
  const links = [
    ["/", "Overview", Activity],
    ["/research", "Research", LineChart],
    ["/strategies", "Strategies", Library],
    ["/portfolio", "Portfolio", ShieldCheck],
    ["/paper", "Paper", CandlestickChart],
    ["/operations", "Operations", HeartPulse],
    ["/knowledge", "Knowledge", Brain]
  ] as const;
  return (
    <aside className="app-sidebar sidebar-dark-primary dashboard-sidebar hidden h-screen border-r border-slate-800 bg-slate-950 px-4 py-5 lg:block">
      <div className="sidebar-brand dashboard-brand mb-7 border-0 p-0">
        <div className="brand-link p-0 text-slate-100">
          <span className="brand-text text-lg font-semibold">QuantForge AI</span>
        </div>
        <div className="text-xs text-slate-400">Production Research Dashboard</div>
      </div>
      <nav className="nav nav-pills nav-sidebar dashboard-nav flex-column space-y-1">
        {links.map(([to, label, Icon]) => (
          <NavLink key={to} to={to} className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}>
            <Icon size={17} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

function Header() {
  return (
    <header className="app-header navbar navbar-expand dashboard-header sticky top-0 z-20 border-b border-slate-800 bg-slate-950/95 px-5 py-3 backdrop-blur lg:px-8">
      <div className="dashboard-header-inner flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-normal">QuantForge AI</h1>
          <p className="text-sm text-slate-400">Production Research Dashboard</p>
        </div>
        <div className="dashboard-status-strip flex flex-wrap gap-2">
          <CBadge color="info">CoreUI</CBadge>
          <span className="badge text-bg-secondary">AdminLTE</span>
          <StatusBadge label="HEALTHY" tone="good" />
          <StatusBadge label="READ ONLY" tone="neutral" />
          <StatusBadge label="LIVE DISABLED" tone="warn" />
        </div>
      </div>
    </header>
  );
}

function Overview() {
  const data = useApi<Row>("/api/dashboard/overview");
  if (!data) return <Loading />;
  return (
    <div className="space-y-5">
      <ReadinessBanner value={String(data.decision_banner)} source={String(data.source)} />
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard title="Platform" value={data.platform_status} tone="good" />
        <KpiCard title="Research" value={data.research_status} tone="good" />
        <KpiCard title="Portfolio" value={data.portfolio_readiness} tone="good" />
        <KpiCard title="Paper Trading" value={data.paper_trading_status} />
        <KpiCard title="Live Trading" value={data.live_trading_status} tone="warn" />
        <KpiCard title="Alerts" value={data.critical_alerts} tone="good" />
      </div>
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
        <KpiCard title="Experiments" value={number(data.experiments)} />
        <KpiCard title="Candidates" value={number(data.candidate_strategies)} />
        <KpiCard title="Optimized" value={number(data.optimized_strategies)} />
        <KpiCard title="Validated Assets" value={number(data.validated_assets)} />
        <KpiCard title="Production Grade" value={number(data.production_strategies)} />
        <KpiCard title="Knowledge Records" value={number(data.knowledge_records)} />
        <KpiCard title="Avg Confidence" value={`${data.average_confidence}%`} />
        <KpiCard title="Avg PF" value={data.average_profit_factor} />
        <KpiCard title="Max Drawdown" value={`${data.max_drawdown}%`} />
        <KpiCard title="Architecture" value={data.architecture_freeze} />
      </div>
    </div>
  );
}

function Research() {
  const progress = useApi<any>("/api/dashboard/research/progress");
  const programs = useApi<Row[]>("/api/dashboard/research/programs");
  const rejections = useApi<Row[]>("/api/dashboard/research/rejections");
  if (!progress || !programs || !rejections) return <Loading />;
  return (
    <Page title="Research Progress">
      <div className="grid gap-4 xl:grid-cols-2">
        <LinePanel title="Experiments completed" data={progress.charts.experiments_over_time} />
        <LinePanel title="Knowledge growth" data={progress.charts.knowledge_growth} />
        <BarPanel title="Profit factor distribution" data={progress.charts.profit_factor_distribution} />
        <BarPanel title="Drawdown distribution" data={progress.charts.drawdown_distribution} />
      </div>
      <DataTable title="Research Programs" rows={programs} />
      <DataTable title="Rejected Strategy Reasons" rows={rejections} />
    </Page>
  );
}

function Strategies() {
  const rows = useApi<Row[]>("/api/strategies");
  const [query, setQuery] = React.useState("");
  if (!rows) return <Loading />;
  const filtered = rows.filter((row) => JSON.stringify(row).toLowerCase().includes(query.toLowerCase()));
  return (
    <Page title="Strategy Library">
      <input className="input" placeholder="Filter by pair, timeframe, regime, grade, PF, drawdown..." value={query} onChange={(event) => setQuery(event.target.value)} />
      <DataTable title="Production-Grade Strategies" rows={filtered.slice(0, 50)} linkKey="strategy_id" />
    </Page>
  );
}

function StrategyDetail() {
  const { id } = useParams();
  const data = useApi<any>(`/api/strategies/${id}`);
  if (!data) return <Loading />;
  return (
    <Page title={data.strategy_name}>
      <div className="grid gap-3 md:grid-cols-4">
        <KpiCard title="Pair" value={data.pair} />
        <KpiCard title="Timeframe" value={data.timeframe} />
        <KpiCard title="Confidence" value={`${data.confidence}%`} />
        <KpiCard title="Grade" value={data.validation_grade} tone="good" />
      </div>
      <JsonPanel title="Strategy Passport" data={data.passport} />
      <JsonPanel title="Decision Trace" data={data.decision_trace} />
      <JsonPanel title="Optimization Report" data={data.optimization_report} />
      <JsonPanel title="Validation Report" data={data.validation_report} />
      <JsonPanel title="Backtest Report" data={data.backtest_report} />
    </Page>
  );
}

function Portfolio() {
  const ready = useApi<Row>("/api/portfolio/readiness");
  const coverage = useApi<any>("/api/portfolio/coverage");
  const risk = useApi<any>("/api/portfolio/risk");
  if (!ready || !coverage || !risk) return <Loading />;
  return (
    <Page title="Portfolio Readiness">
      <ReadinessBanner value={String(ready.portfolio_readiness)} source={String(ready.source)} />
      <div className="grid gap-3 md:grid-cols-4">
        <KpiCard title="Production Strategies" value={ready.production_strategies} />
        <KpiCard title="Selected Portfolio" value={ready.selected_portfolio_strategies} />
        <KpiCard title="Average Correlation" value={ready.average_correlation} />
        <KpiCard title="Expected PF" value={ready.expected_portfolio_pf} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <BarPanel title="Regime Coverage" data={Object.values(coverage.regimes)} labels={Object.keys(coverage.regimes)} />
        <BarPanel title="Pair Exposure" data={Object.values(coverage.pairs)} labels={Object.keys(coverage.pairs)} />
        <LinePanel title="Expected Drawdown" data={risk.expected_drawdown_curve} />
        <LinePanel title="Validation Equity Curve" data={risk.portfolio_equity_curve} />
      </div>
    </Page>
  );
}

function Paper() {
  const summary = useApi<Row>("/api/paper/summary");
  const trades = useApi<Row[]>("/api/paper/trades/open");
  const drift = useApi<any>("/api/paper/drift");
  if (!summary || !trades || !drift) return <Loading />;
  return (
    <Page title="Paper Trading">
      <div className="grid gap-3 md:grid-cols-4">
        <KpiCard title="Paper Balance" value={`$${number(summary.paper_balance)}`} />
        <KpiCard title="Paper Equity" value={`$${number(summary.paper_equity)}`} />
        <KpiCard title="Daily P/L" value={`$${summary.daily_pl}`} />
        <KpiCard title="Promotion" value={summary.promotion_readiness} tone="good" />
      </div>
      <DataTable title="Open Paper Trades" rows={trades} />
      <JsonPanel title="Drift" data={drift} />
    </Page>
  );
}

function Operations() {
  const health = useApi<Row>("/api/ops/health");
  const services = useApi<Row[]>("/api/ops/services");
  const system = useApi<any>("/api/ops/system");
  if (!health || !services || !system) return <Loading />;
  return (
    <Page title="Operations Health">
      <div className="grid gap-3 md:grid-cols-4">
        <KpiCard title="Status" value={health.platform_status} tone="good" />
        <KpiCard title="Services Online" value={health.services_online} />
        <KpiCard title="Warnings" value={health.warnings} tone="good" />
        <KpiCard title="Queue Size" value={health.queue_size} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <LinePanel title="CPU Trend" data={system.cpu} />
        <LinePanel title="RAM Trend" data={system.ram} />
      </div>
      <DataTable title="Service Health" rows={services} />
    </Page>
  );
}

function Knowledge() {
  const summary = useApi<Row>("/api/knowledge/summary");
  const features = useApi<Row[]>("/api/knowledge/features");
  const plugins = useApi<Row[]>("/api/knowledge/plugins");
  const hypotheses = useApi<Row[]>("/api/knowledge/hypotheses");
  if (!summary || !features || !plugins || !hypotheses) return <Loading />;
  return (
    <Page title="Knowledge Base">
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard title="Records" value={number(summary.knowledge_records)} />
        <KpiCard title="Confirmed" value={summary.confirmed_hypotheses} />
        <KpiCard title="Rejected" value={summary.rejected_hypotheses} />
        <KpiCard title="Top Feature" value={summary.top_feature_family} />
        <KpiCard title="Top Template" value={summary.top_strategy_template} />
        <KpiCard title="Top Regime" value={summary.top_regime} />
      </div>
      <DataTable title="Feature Rankings" rows={features} />
      <DataTable title="Plugin Rankings" rows={plugins} />
      <DataTable title="Hypothesis Confidence" rows={hypotheses} />
    </Page>
  );
}

function Page({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="page-shell space-y-5">
      <h2 className="page-title text-lg font-semibold">{title}</h2>
      {children}
    </div>
  );
}

function KpiCard({ title, value, tone = "neutral" }: { title: string; value: React.ReactNode; tone?: "good" | "warn" | "neutral" }) {
  return (
    <div className={`card panel dashboard-card border-l-4 ${tone === "good" ? "border-l-emerald-400" : tone === "warn" ? "border-l-amber-400" : "border-l-sky-400"}`}>
      <div className="card-body p-0">
        <div className="text-xs uppercase text-slate-400">{title}</div>
        <div className="mt-2 break-words text-xl font-semibold">{value}</div>
      </div>
    </div>
  );
}

function StatusBadge({ label, tone }: { label: string; tone: "good" | "warn" | "neutral" }) {
  const bootstrapTone = tone === "good" ? "success" : tone === "warn" ? "warning" : "secondary";
  return <span className={`badge text-bg-${bootstrapTone} status ${tone}`}>{label}</span>;
}

function ReadinessBanner({ value, source }: { value: string; source: string }) {
  return (
    <div className="callout callout-success rounded border border-emerald-500/40 bg-emerald-500/10 p-4">
      <div className="text-sm text-emerald-200">Decision</div>
      <div className="text-2xl font-semibold text-emerald-50">{value}</div>
      <div className="mt-1 text-xs text-emerald-200/80">Source: {source}</div>
    </div>
  );
}

function DataTable({ title, rows, linkKey }: { title: string; rows: Row[]; linkKey?: string }) {
  const columns = rows[0] ? Object.keys(rows[0]).slice(0, 10) : [];
  return (
    <div className="card panel dashboard-card overflow-hidden">
      <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">{title}</div>
      <div className="overflow-auto">
        <table className="table table-dark table-hover dashboard-table w-full min-w-[760px] text-left text-sm">
          <thead className="bg-slate-900 text-xs uppercase text-slate-400">
            <tr>{columns.map((column) => <th key={column} className="px-3 py-2">{column.replace(/_/g, " ")}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index} className="border-t border-slate-800">
                {columns.map((column) => (
                  <td key={column} className="px-3 py-2 text-slate-200">
                    {linkKey === column ? <Link className="text-cyan-300 hover:text-cyan-200" to={`/strategies/${row[column]}`}>{String(row[column])}</Link> : String(row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LinePanel({ title, data }: { title: string; data: number[] }) {
  return (
    <div className="card panel dashboard-card">
      <div className="card-header border-0 bg-transparent p-0 pb-2 font-medium">{title}</div>
      <ReactECharts className="h-64" option={{ backgroundColor: "transparent", xAxis: { type: "category", data: data.map((_, index) => `T${index + 1}`) }, yAxis: { type: "value" }, series: [{ data, type: "line", smooth: true, areaStyle: {} }], textStyle: { color: "#cbd5e1" }, grid: { left: 44, right: 16, top: 20, bottom: 28 } }} />
    </div>
  );
}

function BarPanel({ title, data, labels }: { title: string; data: number[]; labels?: string[] }) {
  return (
    <div className="card panel dashboard-card">
      <div className="card-header border-0 bg-transparent p-0 pb-2 font-medium">{title}</div>
      <ReactECharts className="h-64" option={{ backgroundColor: "transparent", xAxis: { type: "category", data: labels ?? data.map((_, index) => `B${index + 1}`) }, yAxis: { type: "value" }, series: [{ data, type: "bar" }], textStyle: { color: "#cbd5e1" }, grid: { left: 44, right: 16, top: 20, bottom: 42 } }} />
    </div>
  );
}

function JsonPanel({ title, data }: { title: string; data: unknown }) {
  return (
    <div className="card panel dashboard-card">
      <div className="card-header border-0 bg-transparent p-0 pb-2 font-medium">{title}</div>
      <pre className="overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-300">{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}

function Loading() {
  return <div className="panel text-slate-300">Loading dashboard data...</div>;
}

function number(value: unknown) {
  return Number(value).toLocaleString();
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
