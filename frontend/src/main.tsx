import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Link, NavLink, Route, Routes, useParams } from "react-router-dom";
import ReactECharts from "echarts-for-react";
import { CBadge } from "@coreui/react";
import { Activity, BookOpen, Brain, CandlestickChart, CircleHelp, Database, HeartPulse, Library, LineChart, ShieldCheck } from "lucide-react";
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
      <div className="app-wrapper dashboard-shell sidebar-expand-lg min-h-screen bg-slate-950 text-slate-100" data-bs-theme="dark">
        <Sidebar />
        <Header />
        <main className="app-main dashboard-main min-h-screen">
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
              <Route path="/help" element={<Help />} />
            </Routes>
          </section>
        </main>
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
    ["/knowledge", "Knowledge", Brain],
    ["/help", "Manual / Help", CircleHelp]
  ] as const;
  return (
    <aside className="app-sidebar sidebar-dark-primary dashboard-sidebar border-r border-slate-800 bg-slate-950" data-bs-theme="dark">
      <div className="sidebar-brand dashboard-brand border-0">
        <div className="brand-link text-slate-100">
          <span className="brand-text text-lg font-semibold">QuantForge AI</span>
        </div>
        <div className="text-xs text-slate-400">Production Research Dashboard</div>
      </div>
      <div className="sidebar-wrapper">
        <nav className="mt-2">
          <ul className="nav nav-pills nav-sidebar dashboard-nav flex-column" role="menu">
            {links.map(([to, label, Icon]) => (
              <li className="nav-item" key={to}>
                <NavLink to={to} className={({ isActive }) => `nav-link ${isActive ? "nav-link-active active" : ""}`}>
                  <Icon className="nav-icon" size={17} />
                  <p>{label}</p>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </div>
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
      <div className="kpi-grid">
        <KpiCard title="Platform" value={data.platform_status} tone="good" />
        <KpiCard title="Research" value={data.research_status} tone="good" />
        <KpiCard title="Portfolio" value={data.portfolio_readiness} tone="good" />
        <KpiCard title="Paper Trading" value={data.paper_trading_status} />
        <KpiCard title="Live Trading" value={data.live_trading_status} tone="warn" />
        <KpiCard title="Alerts" value={data.critical_alerts} tone="good" />
      </div>
      <div className="kpi-grid">
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
      <div className="kpi-grid">
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
      <div className="kpi-grid">
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
      <div className="kpi-grid">
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
      <div className="kpi-grid">
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

const manualSections = [
  {
    title: "Overview",
    purpose: "Executive command screen for deciding whether QuantForge is healthy enough to continue research and paper-trading review.",
    use: [
      "Read the Decision banner first. It summarizes the safest current action.",
      "Check Platform, Research, Portfolio, Paper Trading, Live Trading, and Alerts for a fast status scan.",
      "Use the lower KPI group to compare experiment volume, candidate count, validated assets, confidence, profit factor, and drawdown."
    ],
    details: [
      "The dashboard is read-only. It does not start trades, deploy strategies, or change production state.",
      "LIVE DISABLED means live execution is intentionally blocked from this dashboard."
    ]
  },
  {
    title: "Research",
    purpose: "Tracks experiment progress, knowledge growth, profit-factor distribution, drawdown distribution, active programs, and rejection reasons.",
    use: [
      "Use the experiment and knowledge charts to confirm research velocity.",
      "Use profit-factor and drawdown distributions to judge whether the library is improving or becoming riskier.",
      "Review rejected strategy reasons before adding new templates or calculators."
    ],
    details: [
      "Research programs show current workstreams and progress.",
      "Rejected reasons explain why candidates failed validation so the next experiment can avoid repeated mistakes."
    ]
  },
  {
    title: "Strategy Library",
    purpose: "Lists production-grade or near-production strategy candidates with validation metrics and links to strategy passports.",
    use: [
      "Type in the filter box to search by pair, timeframe, regime, grade, profit factor, drawdown, or any visible field.",
      "Click a strategy ID to open its Strategy Passport page.",
      "Compare confidence, validation grade, profit factor, and drawdown before considering portfolio inclusion."
    ],
    details: [
      "Tables scroll horizontally on smaller screens so columns stay readable.",
      "The page shows a capped list for fast scanning; refine the filter to narrow results."
    ]
  },
  {
    title: "Strategy Passport",
    purpose: "Shows the traceable record for one strategy, including decision trace, optimization, validation, and backtest evidence.",
    use: [
      "Start with Pair, Timeframe, Confidence, and Grade.",
      "Review the Decision Trace to understand why the strategy exists.",
      "Compare Optimization, Validation, and Backtest reports before trusting any single metric."
    ],
    details: [
      "Passport JSON is intentionally raw so audit evidence is not hidden behind summaries.",
      "A strategy should not move toward production unless validation and drawdown evidence both support it."
    ]
  },
  {
    title: "Portfolio",
    purpose: "Shows whether the selected strategy set is balanced enough for paper trading or later certification.",
    use: [
      "Read the Portfolio Readiness banner before looking at individual charts.",
      "Use Regime Coverage to spot overdependence on one market condition.",
      "Use Pair Exposure and Average Correlation to avoid crowded risk.",
      "Use Expected Drawdown and Validation Equity Curve to judge portfolio-level risk."
    ],
    details: [
      "Portfolio readiness is about the combined set, not only the best individual strategy.",
      "Low correlation and broad regime coverage are preferred before promotion."
    ]
  },
  {
    title: "Paper Trading",
    purpose: "Monitors virtual trading performance, open paper trades, drift, and promotion readiness.",
    use: [
      "Compare Paper Balance, Paper Equity, and Daily P/L for current simulation performance.",
      "Review Open Paper Trades to see active exposure.",
      "Use Drift to detect if live-like behavior is moving away from validation expectations."
    ],
    details: [
      "Paper trading is still simulated. Treat it as a gate before any live approval.",
      "Promotion readiness should be supported by stable drift and risk, not only profit."
    ]
  },
  {
    title: "Operations",
    purpose: "Checks service health, queue size, warnings, and system resource trends.",
    use: [
      "Confirm overall platform status and services online.",
      "Watch warnings and queue size for blocked or delayed research jobs.",
      "Use CPU and RAM trends to decide whether the research workload is too heavy."
    ],
    details: [
      "Operations health helps explain slow or missing research output.",
      "A healthy service table is required before trusting fresh dashboard numbers."
    ]
  },
  {
    title: "Knowledge Base",
    purpose: "Summarizes validated findings, rejected hypotheses, feature rankings, plugin rankings, and confidence evidence.",
    use: [
      "Check Records, Confirmed, and Rejected counts to see whether the research memory is growing.",
      "Use Feature Rankings to identify the strongest reusable signals.",
      "Use Plugin Rankings and Hypothesis Confidence before selecting the next experiment direction."
    ],
    details: [
      "The Knowledge Base is the feedback loop for future strategy discovery.",
      "Rejected hypotheses are valuable evidence and should not be ignored."
    ]
  }
];

const workflowSteps = [
  "Start on Overview and confirm the Decision banner is acceptable.",
  "Check Operations to make sure services and resource trends are healthy.",
  "Review Research progress and rejection reasons to understand the current experiment state.",
  "Open Strategy Library, filter candidates, and inspect individual Strategy Passports.",
  "Check Portfolio to confirm strategy diversity, correlation, and drawdown behavior.",
  "Review Paper Trading for drift and simulated execution performance.",
  "Use Knowledge Base findings to choose the next research direction."
];

function Help() {
  return (
    <Page title="Manual / Help">
      <div className="manual-grid">
        <section className="card panel dashboard-card manual-panel">
          <div className="card-header border-0 bg-transparent p-0 pb-2 font-medium">How to use the dashboard</div>
          <ol className="manual-steps">
            {workflowSteps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </section>
        <section className="card panel dashboard-card manual-panel">
          <div className="card-header border-0 bg-transparent p-0 pb-2 font-medium">Safety model</div>
          <div className="manual-copy">
            <p>This dashboard is a read-only control surface for research, validation, portfolio readiness, paper trading, operations, and evidence review.</p>
            <p>It is designed to help decide what to inspect next. It does not place trades, enable live trading, deploy strategies, or mutate research records from the browser.</p>
          </div>
        </section>
      </div>

      <div className="manual-section-grid">
        {manualSections.map((section) => (
          <section className="card panel dashboard-card manual-panel" key={section.title}>
            <div className="flex items-start gap-3">
              <BookOpen className="mt-1 shrink-0 text-cyan-300" size={18} />
              <div>
                <h3 className="manual-title">{section.title}</h3>
                <p className="manual-purpose">{section.purpose}</p>
              </div>
            </div>
            <div className="manual-block">
              <div className="manual-label">How to work with it</div>
              <ul className="manual-list">
                {section.use.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="manual-block">
              <div className="manual-label">Details</div>
              <ul className="manual-list">
                {section.details.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </section>
        ))}
      </div>
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
        <div className="dashboard-card-value mt-2 font-semibold">{value}</div>
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
      <div className="readiness-value text-2xl font-semibold text-emerald-50">{value}</div>
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
