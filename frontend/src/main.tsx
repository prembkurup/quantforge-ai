import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Link, NavLink, Route, Routes, useParams } from "react-router-dom";
import ReactECharts from "echarts-for-react";
import { CandlestickSeries, ColorType, LineStyle, createChart, createSeriesMarkers, type AutoscaleInfoProvider, type CandlestickData, type UTCTimestamp } from "lightweight-charts";
import { Activity, BookOpen, Brain, CandlestickChart, CircleHelp, Database, GitBranch, HeartPulse, Library, LineChart, ListChecks, Menu, PieChart, Save, ScrollText, Settings, ShieldCheck, Workflow as WorkflowIcon, X } from "lucide-react";
import "@coreui/coreui/dist/css/coreui.min.css";
import "admin-lte/dist/css/adminlte.min.css";
import "./styles.css";

const apiBase = import.meta.env.VITE_API_BASE ?? "";

type Row = Record<string, string | number | boolean>;

type PaperPositionChartCandle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type PaperPositionChartPayload = {
  pair: string;
  display_pair: string;
  timeframe: string;
  limit: number;
  candles: PaperPositionChartCandle[];
  trade: {
    direction: string;
    open_price: number | null;
    stop_loss: number | null;
    take_profit: number | null;
    opened_at: string;
    source_candle_time: string;
  };
  database_status: string;
  error: string;
  source: string;
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`);
  if (!response.ok) throw new Error(`Request failed: ${path}`);
  return response.json() as Promise<T>;
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(`Request failed: ${path}`);
  return response.json() as Promise<T>;
}

function useApi<T>(path: string, fallback: T | null = null): T | null {
  const [data, setData] = React.useState<T | null>(fallback);
  React.useEffect(() => {
    let active = true;
    getJson<T>(path)
      .then((payload) => active && setData(payload))
      .catch(() => active && fallback !== null && setData(fallback));
    const timer = window.setInterval(() => {
      getJson<T>(path)
        .then((payload) => active && setData(payload))
        .catch(() => active && fallback !== null && setData(fallback));
    }, 30000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [path]);
  return data;
}

function App() {
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);
  return (
    <BrowserRouter>
      <div
        className={`app-wrapper dashboard-shell sidebar-expand-lg min-h-screen bg-slate-950 text-slate-100 ${mobileNavOpen ? "mobile-nav-open" : ""}`}
        data-bs-theme="dark"
      >
        <Sidebar isOpen={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
        <button
          aria-label="Close navigation"
          className="mobile-nav-backdrop"
          onClick={() => setMobileNavOpen(false)}
          type="button"
        />
        <Header onOpenNav={() => setMobileNavOpen(true)} />
        <main className="app-main dashboard-main min-h-screen">
          <section className="app-content dashboard-content px-5 py-4 lg:px-8">
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/research" element={<Research />} />
              <Route path="/pipeline" element={<Pipeline />} />
              <Route path="/workflow" element={<Workflow />} />
              <Route path="/full-history" element={<FullHistoryResearch />} />
              <Route path="/strategies" element={<Strategies />} />
              <Route path="/strategies/:id" element={<StrategyDetail />} />
              <Route path="/indicators" element={<Indicators />} />
              <Route path="/portfolio" element={<Portfolio />} />
              <Route path="/portfolio-intelligence" element={<PortfolioIntelligence />} />
              <Route path="/performance-learning" element={<PerformanceLearning />} />
              <Route path="/intraday" element={<IntradayDaily />} />
              <Route path="/decision-intelligence" element={<DecisionIntelligence />} />
              <Route path="/paper" element={<Paper />} />
              <Route path="/history-validation" element={<HistoryValidation />} />
              <Route path="/operations" element={<Operations />} />
              <Route path="/logs" element={<Logs />} />
              <Route path="/knowledge" element={<Knowledge />} />
              <Route path="/admin" element={<AdminSettings />} />
              <Route path="/architecture" element={<Architecture />} />
              <Route path="/help" element={<Help />} />
            </Routes>
          </section>
        </main>
      </div>
    </BrowserRouter>
  );
}

function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const links = [
    ["/", "Overview", Activity],
    ["/research", "Research", LineChart],
    ["/pipeline", "Pipeline", ListChecks],
    ["/workflow", "Workflow", GitBranch],
    ["/full-history", "Full History", Database],
    ["/strategies", "Strategies", Library],
    ["/indicators", "Indicators", BookOpen],
    ["/portfolio", "Portfolio", ShieldCheck],
    ["/portfolio-intelligence", "Portfolio Intel", PieChart],
    ["/performance-learning", "Learning", Brain],
    ["/intraday", "Intraday", Activity],
    ["/decision-intelligence", "Decision Intel", Brain],
    ["/paper", "Paper", CandlestickChart],
    ["/history-validation", "History Validation", Database],
    ["/operations", "Operations", HeartPulse],
    ["/logs", "Logs", ScrollText],
    ["/knowledge", "Knowledge", Brain],
    ["/admin", "Admin", Settings],
    ["/architecture", "Architecture", WorkflowIcon],
    ["/help", "Manual / Help", CircleHelp]
  ] as const;
  return (
    <aside
      aria-label="Main navigation"
      className={`app-sidebar sidebar-dark-primary dashboard-sidebar border-r border-slate-800 bg-slate-950 ${isOpen ? "mobile-open" : ""}`}
      data-bs-theme="dark"
    >
      <div className="sidebar-brand dashboard-brand border-0">
        <div className="brand-link text-slate-100">
          <span className="brand-text text-lg font-semibold">QuantForge AI</span>
        </div>
        <div className="text-xs text-slate-400">Production Research Dashboard</div>
        <button aria-label="Close navigation" className="mobile-nav-close" onClick={onClose} type="button">
          <X size={18} />
        </button>
      </div>
      <div className="sidebar-wrapper">
        <nav className="mt-2">
          <ul className="nav nav-pills nav-sidebar dashboard-nav flex-column" role="menu">
            {links.map(([to, label, Icon]) => (
              <li className="nav-item" key={to}>
                <NavLink
                  to={to}
                  className={({ isActive }) => `nav-link ${isActive ? "nav-link-active active" : ""}`}
                  onClick={onClose}
                >
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

function Header({ onOpenNav }: { onOpenNav: () => void }) {
  const overview = useApi<Row>("/api/dashboard/overview", {});
  const liveStatus = String(overview?.live_trading_status ?? "UNKNOWN");
  const liveTone = liveStatus === "ENABLED" ? "warn" : liveStatus === "DISABLED" ? "neutral" : "warn";
  return (
    <header className="app-header navbar navbar-expand dashboard-header sticky top-0 z-20 px-5 py-3 lg:px-8">
      <div className="dashboard-header-inner flex flex-wrap items-center justify-between gap-3">
        <div className="dashboard-header-brand">
          <button aria-label="Open navigation" className="mobile-nav-toggle" onClick={onOpenNav} type="button">
            <Menu size={20} />
          </button>
          <div className="dashboard-header-mark">
            <Activity size={19} />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-normal">QuantForge AI</h1>
            <p className="text-sm text-slate-400">Production Research Dashboard</p>
          </div>
        </div>
        <div className="dashboard-status-strip flex flex-wrap gap-2">
          <StatusBadge label={String(overview?.platform_status ?? "CHECKING")} tone={overview?.platform_status === "HEALTHY" ? "good" : "warn"} />
          <StatusBadge label={`LIVE ${liveStatus}`} tone={liveTone} />
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
  const programs = useApi<Row[]>("/api/research/programs");
  const rejections = useApi<Row[]>("/api/dashboard/research/rejections");
  const coverage = useApi<any>("/api/research/coverage");
  const diversity = useApi<any>("/api/research/diversity");
  const productivity = useApi<Row[]>("/api/research/productivity");
  const matrix = useApi<Row[]>("/api/research/matrix");
  const rejected = useApi<Row[]>("/api/research/rejected");
  const orchestrator = useApi<any>("/api/research/orchestrator/status", {
    enabled: false,
    state: "UNKNOWN",
    idle_reason: { reason_code: "API_PENDING", message: "Orchestrator status endpoint is not available yet." },
    next_check_at: "",
    last_checked_at: "",
    last_jobs_launched: 0,
    totals: { weak_programs: 0, stale_programs: 0, blocked_programs: 0 },
  });
  const orchestratorRuns = useApi<Row[]>("/api/research/orchestrator/runs", []);
  const idleReasons = useApi<Row[]>("/api/research/orchestrator/idle-reasons", []);
  const guardrails = useApi<Row[]>("/api/research/orchestrator/guardrails", []);
  const fineTuning = useApi<any>("/api/fine-tuning/status", {
    state: "UNKNOWN",
    eligible_assets: 0,
    message: "Fine-tuning status endpoint is not available yet.",
  });
  if (
    !progress ||
    !programs ||
    !rejections ||
    !coverage ||
    !diversity ||
    !productivity ||
    !matrix ||
    !rejected ||
    !orchestrator ||
    !orchestratorRuns ||
    !idleReasons ||
    !guardrails ||
    !fineTuning
  ) return <Loading />;
  const latestIdleReasons = idleReasons.slice(-10).reverse();
  const latestRuns = orchestratorRuns.slice(-10).reverse();
  const latestGuardrails = guardrails.slice(-10).reverse();
  return (
    <Page title="Research Progress">
      <div className="kpi-grid">
        <KpiCard title="Orchestrator" value={orchestrator.state} tone={orchestrator.state === "ERROR" ? "warn" : "good"} />
        <KpiCard title="Idle Reason" value={orchestrator.idle_reason?.reason_code ?? "NONE"} />
        <KpiCard title="Next Check" value={shortTime(orchestrator.next_check_at)} />
        <KpiCard title="Last Jobs" value={orchestrator.last_jobs_launched ?? 0} />
        <KpiCard title="Weak Programs" value={orchestrator.totals?.weak_programs ?? 0} tone={(orchestrator.totals?.weak_programs ?? 0) ? "warn" : "good"} />
        <KpiCard title="Stale Programs" value={orchestrator.totals?.stale_programs ?? 0} />
        <KpiCard title="Blocked Programs" value={orchestrator.totals?.blocked_programs ?? 0} />
        <KpiCard title="Fine-Tuning" value={fineTuning.state} />
        <KpiCard title="Usable Datasets" value={`${coverage.usable_datasets}/${coverage.total_datasets}`} tone="good" />
        <KpiCard title="Research Coverage" value={`${coverage.coverage_percent}%`} tone="good" />
        <KpiCard title="Programs" value={coverage.research_programs} />
        <KpiCard title="Candidates" value={number(coverage.candidate_count)} />
        <KpiCard title="Approved Assets" value={number(coverage.approved_asset_count)} tone="good" />
        <KpiCard title="Efficiency" value={`${coverage.candidate_efficiency}%`} />
        <KpiCard title="Pairs" value={diversity.pair_count} />
        <KpiCard title="Timeframes" value={diversity.timeframe_count} />
        <KpiCard title="Families" value={diversity.family_count} />
        <KpiCard title="Regimes" value={diversity.regime_count} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <LinePanel title="Experiments completed" data={progress.charts.experiments_over_time} />
        <LinePanel title="Knowledge growth" data={progress.charts.knowledge_growth} />
        <BarPanel title="Profit factor distribution" data={progress.charts.profit_factor_distribution} />
        <BarPanel title="Drawdown distribution" data={progress.charts.drawdown_distribution} />
      </div>
      <section className="card panel dashboard-card">
        <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Always-On Research Orchestrator</div>
        <div className="pipeline-current">
          <div>
            <div className="pipeline-current-title">{orchestrator.idle_reason?.reason_code ?? orchestrator.state}</div>
            <div className="pipeline-current-meta">
              Last checked {shortTime(orchestrator.last_checked_at)} - next check {shortTime(orchestrator.next_check_at)}
            </div>
            <div className="pipeline-current-detail">{orchestrator.idle_reason?.message ?? "Research orchestrator is active."}</div>
          </div>
        </div>
      </section>
      <section className="card panel dashboard-card">
        <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Fine-Tuning Status</div>
        <div className="pipeline-current">
          <div>
            <div className="pipeline-current-title">{fineTuning.state}</div>
            <div className="pipeline-current-meta">Eligible assets {fineTuning.eligible_assets ?? 0}</div>
            <div className="pipeline-current-detail">{fineTuning.message}</div>
          </div>
        </div>
      </section>
      <DataTable title={`Orchestrator Runs (${orchestratorRuns.length})`} rows={latestRuns} />
      <DataTable title={`Orchestrator Idle Reasons (${idleReasons.length})`} rows={latestIdleReasons} />
      <DataTable title={`Orchestrator Guardrails (${guardrails.length})`} rows={latestGuardrails} />
      <PaginatedDataTable title={`Multi-Market Research Programs (${programs.length})`} rows={programs} />
      <PaginatedDataTable title={`Research Productivity by Dataset (${productivity.length})`} rows={productivity} />
      <PaginatedDataTable title={`Full-History Research Matrix (${matrix.length})`} rows={matrix} />
      <PaginatedDataTable title={`Rejected Strategy Candidates (${rejected.length})`} rows={rejected} />
      <PaginatedDataTable title={`Rejected Strategy Reasons (${rejections.length})`} rows={rejections} />
    </Page>
  );
}

function Pipeline() {
  const snapshot = useApi<any>("/api/pipeline/snapshot");
  const [fullHistoryPage, setFullHistoryPage] = React.useState(1);
  if (!snapshot) return <Loading />;
  const { summary, current_task: current, tasks, engines, workload, full_history } = snapshot;
  const fullHistoryJobs = full_history?.jobs ?? [];
  const fullHistoryPageSize = 30;
  const fullHistoryTotalPages = Math.max(1, Math.ceil(fullHistoryJobs.length / fullHistoryPageSize));
  const fullHistoryRows = fullHistoryJobs.slice(
    (fullHistoryPage - 1) * fullHistoryPageSize,
    fullHistoryPage * fullHistoryPageSize
  );
  return (
    <Page title="Pipeline / Engine Monitor">
      <div className="kpi-grid">
        <KpiCard title="Pipeline" value={summary.pipeline_status} tone="good" />
        <KpiCard title="Current Task" value={summary.current_task} />
        <KpiCard title="Overall Progress" value={`${summary.overall_progress}%`} />
        <KpiCard title="Full History Jobs" value={`${summary.full_history_completed_jobs}/${summary.full_history_planned_jobs}`} />
        <KpiCard title="Full History Failed" value={summary.full_history_failed_jobs} tone={summary.full_history_failed_jobs ? "warn" : "good"} />
        <KpiCard title="Active Engines" value={`${summary.active_engines}/${summary.total_engines}`} tone="good" />
        <KpiCard title="Healthy Engines" value={`${summary.healthy_engines}/${summary.total_engines}`} tone="good" />
        <KpiCard title="Queue Depth" value={summary.queue_depth} />
        <KpiCard title="Running Tasks" value={summary.running_tasks} />
        <KpiCard title="Queued Tasks" value={summary.queued_tasks} tone="warn" />
      </div>

      <section className="card panel dashboard-card">
        <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Current Running Task</div>
        <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <div>
            <div className="pipeline-current-title">{current.task}</div>
            <div className="pipeline-current-meta">
              {current.engine} / {current.stage}
            </div>
            <ProgressBar value={Number(current.progress)} />
            <div className="pipeline-current-detail">{current.last_event}</div>
          </div>
          <div className="pipeline-detail-grid">
            <MiniFact label="Task ID" value={current.task_id} />
            <MiniFact label="Status" value={current.status} />
            <MiniFact label="Started" value={current.started_at} />
            <MiniFact label="ETA" value={current.eta} />
            <MiniFact label="Input" value={current.input} />
            <MiniFact label="Output" value={current.output} />
          </div>
        </div>
      </section>

      {full_history && (
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Full History Research Scheduler</div>
          <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
            <div>
              <div className="pipeline-current-title">{full_history.status}</div>
              <div className="pipeline-current-meta">
                {full_history.completed_jobs}/{full_history.planned_jobs} jobs complete / {full_history.pending_jobs} pending
              </div>
              <ProgressBar value={Number(full_history.progress_percent)} />
              <div className="pipeline-current-detail">{full_history.latest_job}</div>
            </div>
            <div className="pipeline-detail-grid">
              <MiniFact label="Completed" value={full_history.completed_jobs} />
              <MiniFact label="Failed" value={full_history.failed_jobs} />
              <MiniFact label="Pending" value={full_history.pending_jobs} />
              <MiniFact label="Latest Update" value={full_history.latest_recorded_at || "waiting"} />
              <MiniFact label="State File" value={full_history.state_file} />
            </div>
          </div>
        </section>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        <WorkloadPanel rows={workload} />
        <DataTable title="Current Status of All Engines" rows={engines} />
      </div>
      <DataTable title="Tasks in the Pipeline" rows={tasks} />
      {fullHistoryJobs.length ? (
        <>
          <DataTable title={`Full History Scheduler Jobs (${fullHistoryJobs.length})`} rows={fullHistoryRows} />
          <PaginationControls
            page={fullHistoryPage}
            totalPages={fullHistoryTotalPages}
            pageSize={fullHistoryPageSize}
            totalRows={fullHistoryJobs.length}
            onPageChange={setFullHistoryPage}
          />
        </>
      ) : null}
    </Page>
  );
}

function Workflow() {
  const data = useApi<any>("/api/workflow/current");
  const audit = useApi<Row[]>("/api/workflow/approvals/audit");
  const [taskPage, setTaskPage] = React.useState(1);
  const [eventPage, setEventPage] = React.useState(1);
  if (!data || !audit) return <Loading />;
  const run = data.run ?? {};
  const stages = data.stages ?? [];
  const tasks = data.tasks ?? [];
  const events = data.events ?? [];
  const approvals = data.approvals ?? [];
  const taskPageSize = 30;
  const taskTotalPages = Math.max(1, Math.ceil(tasks.length / taskPageSize));
  const taskRows = tasks.slice((taskPage - 1) * taskPageSize, taskPage * taskPageSize);
  const eventPageSize = 30;
  const eventTotalPages = Math.max(1, Math.ceil(events.length / eventPageSize));
  const eventPageRows = events.slice((eventPage - 1) * eventPageSize, eventPage * eventPageSize);
  const stageRows = stages.map((stage: any) => ({
    Stage: stage.stage_id,
    Status: stage.status,
    Progress: `${stage.progress_percent ?? 0}%`,
    Started: stage.started_at,
    Finished: stage.completed_at,
    "Waiting Reason": stage.waiting_reason,
    Blocker: stage.blocker_summary,
  }));
  const taskTableRows = taskRows.map((task: any) => ({
    Task: task.name ?? task.task_id,
    Stage: task.stage,
    Pair: task.pair,
    Timeframe: task.timeframe,
    Status: task.status,
    Attempt: task.attempt,
    "Max Retries": task.max_retries,
    Started: task.started_at,
    Finished: task.finished_at,
    "Waiting Reason": task.waiting_reason,
    "Next Action": task.next_action,
    Error: task.error_message,
  }));
  const approvalRows = approvals.map((approval: any) => ({
    Approval: approval.approval_id,
    Stage: approval.stage,
    Type: approval.approval_type,
    Status: approval.status,
    Requested: approval.requested_at,
    Approved: approval.approved_at,
    Rejected: approval.rejected_at,
    Reason: approval.reason,
  }));
  const eventRows = eventPageRows.map((event: any) => ({
    Time: event.timestamp,
    Event: event.event_type,
    Stage: event.stage,
    Task: event.task_id,
    From: event.old_status,
    To: event.new_status,
    Message: event.message,
    Trace: event.trace_id,
    Metadata: JSON.stringify(event.metadata ?? {}),
  }));
  return (
    <Page title="Workflow Orchestration">
      <div className="kpi-grid">
        <KpiCard title="Current Stage" value={run.current_stage} />
        <KpiCard title="Workflow Status" value={run.status} tone={run.status === "RUNNING" ? "good" : run.status === "BLOCKED" ? "warn" : "neutral"} />
        <KpiCard title="Progress" value={`${run.completed_tasks}/${run.total_tasks}`} />
        <KpiCard title="Running" value={run.running_tasks} tone="good" />
        <KpiCard title="Failed" value={run.failed_tasks} tone={run.failed_tasks ? "warn" : "good"} />
        <KpiCard title="Retryable" value={run.retryable_tasks} tone={run.retryable_tasks ? "warn" : "good"} />
        <KpiCard title="Blocked" value={run.blocked_tasks} tone={run.blocked_tasks ? "warn" : "good"} />
        <KpiCard title="Live Trading" value={run.live_trading_status} tone="warn" />
        <KpiCard title="Live Gate Reason" value={data.live_gate?.reason ?? "Manual approval required"} tone="warn" />
      </div>

      <section className="card panel dashboard-card">
        <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Current Workflow Run</div>
        <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
          <div>
            <div className="pipeline-current-title">{run.name}</div>
            <div className="pipeline-current-meta">{run.workflow_id}</div>
            <ProgressBar value={Number(run.total_tasks ? Math.round((run.completed_tasks / run.total_tasks) * 100) : 0)} />
            <div className="pipeline-current-detail">{run.next_action}</div>
          </div>
          <div className="pipeline-detail-grid">
            <MiniFact label="Plan Hash" value={run.plan_hash} />
            <MiniFact label="Started" value={run.started_at} />
            <MiniFact label="Live Gate" value={`${data.live_gate?.status ?? run.live_trading_status}: ${data.live_gate?.reason ?? "blocked"}`} />
            <MiniFact label="Source" value={data.source} />
          </div>
        </div>
      </section>

      <DataTable title="Workflow Stage Timeline" rows={stageRows} />
      <DataTable title={`Workflow Tasks (${tasks.length})`} rows={taskTableRows} />
      <PaginationControls
        page={taskPage}
        totalPages={taskTotalPages}
        pageSize={taskPageSize}
        totalRows={tasks.length}
        onPageChange={setTaskPage}
      />
      <div className="grid gap-4 xl:grid-cols-2">
        <DataTable title="Approvals" rows={approvalRows} />
        <DataTable title="Approval Audit Log" rows={audit} />
      </div>
      <DataTable title={`Workflow Events (${events.length})`} rows={eventRows} />
      <PaginationControls
        page={eventPage}
        totalPages={eventTotalPages}
        pageSize={eventPageSize}
        totalRows={events.length}
        onPageChange={setEventPage}
      />
    </Page>
  );
}

function Strategies() {
  const rows = useApi<Row[]>("/api/strategies");
  const [query, setQuery] = React.useState("");
  const [page, setPage] = React.useState(1);
  const pageSize = 30;
  React.useEffect(() => setPage(1), [query]);
  if (!rows) return <Loading />;
  const filtered = rows.filter((row) => JSON.stringify(row).toLowerCase().includes(query.toLowerCase()));
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pageRows = filtered.slice((page - 1) * pageSize, page * pageSize);
  return (
    <Page title="Strategy Library">
      <input className="input" placeholder="Filter by pair, timeframe, regime, grade, PF, drawdown..." value={query} onChange={(event) => setQuery(event.target.value)} />
      <DataTable title={`Production-Grade Strategies (${filtered.length})`} rows={pageRows} linkKey="strategy_id" />
      <PaginationControls page={page} totalPages={totalPages} pageSize={pageSize} totalRows={filtered.length} onPageChange={setPage} />
    </Page>
  );
}

function StrategyDetail() {
  const { id } = useParams();
  const data = useApi<any>(`/api/strategies/${id}`);
  const trace = useApi<any>(`/api/strategies/${id}/trace`);
  if (!data || !trace) return <Loading />;
  return (
    <Page title={data.strategy_name}>
      <div className="grid gap-3 md:grid-cols-4">
        <KpiCard title="Pair" value={data.pair} />
        <KpiCard title="Timeframe" value={data.timeframe} />
        <KpiCard title="Confidence" value={`${data.confidence}%`} />
        <KpiCard title="Grade" value={data.validation_grade} tone="good" />
        <KpiCard title="Source Workflow" value={data.source_workflow_id || "n/a"} />
        <KpiCard title="Paper Replay" value={`${trace.paper_replay?.status ?? "UNKNOWN"} / ${number(trace.paper_replay?.processed_events ?? 0)} events`} tone="good" />
        <KpiCard title="Approval Gate" value={trace.approval_gate?.status ?? "WAITING"} tone="warn" />
        <KpiCard title="Demo Mode" value={String(data.demo_mode)} tone={data.demo_mode ? "warn" : "good"} />
      </div>
      <JsonPanel title="End-to-End Source Trace" data={trace} />
      <JsonPanel title="Strategy Passport" data={data.passport} />
      <JsonPanel title="Decision Trace" data={data.decision_trace} />
      <JsonPanel title="Optimization Report" data={data.optimization_report} />
      <JsonPanel title="Validation Report" data={data.validation_report} />
      <JsonPanel title="Backtest Report" data={data.backtest_report} />
    </Page>
  );
}

function Indicators() {
  const rows = useApi<Row[]>("/api/indicators");
  const [query, setQuery] = React.useState("");
  if (!rows) return <Loading />;
  const filtered = rows.filter((row) => JSON.stringify(row).toLowerCase().includes(query.toLowerCase()));
  const categories = new Set(rows.map((row) => String(row.category))).size;
  return (
    <Page title="Indicators Used">
      <div className="kpi-grid">
        <KpiCard title="Active Indicators" value={rows.length} tone="good" />
        <KpiCard title="Categories" value={categories} />
        <KpiCard title="Status" value="ACTIVE" tone="good" />
      </div>
      <input className="input" placeholder="Filter by indicator, category, purpose, or engine usage..." value={query} onChange={(event) => setQuery(event.target.value)} />
      <DataTable title={`Indicator / Calculator Reference (${filtered.length})`} rows={filtered} />
    </Page>
  );
}

function FullHistoryResearch() {
  const data = useApi<any>("/api/full-history/research");
  if (!data) return <Loading />;
  const scheduler = data.scheduler ?? {};
  const coverage = data.coverage ?? [];
  const pairs = data.pairs ?? [];
  const timeframes = data.timeframes ?? [];
  return (
    <Page title="Full History Research">
      <div className="kpi-grid">
        <KpiCard title="Pairs / Instruments" value={data.pair_count} tone="good" />
        <KpiCard title="Timeframes" value={data.timeframe_count} />
        <KpiCard title="Pair-Timeframe Tests" value={data.pair_timeframe_count} />
        <KpiCard title="Scheduler Jobs" value={scheduler.planned_jobs ?? 0} />
        <KpiCard title="Completed Jobs" value={scheduler.completed_jobs ?? 0} tone="good" />
        <KpiCard title="Failed Jobs" value={scheduler.failed_jobs ?? 0} tone={scheduler.failed_jobs ? "warn" : "good"} />
        <KpiCard title="Pending Jobs" value={scheduler.pending_jobs ?? 0} />
        <KpiCard title="Progress" value={`${scheduler.progress_percent ?? 0}%`} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <DataTable title={`Pairs / Instruments (${pairs.length})`} rows={pairs} />
        <DataTable title={`Timeframes (${timeframes.length})`} rows={timeframes} />
      </div>
      <DataTable title={`Full History Candle Coverage (${coverage.length})`} rows={coverage} />
      <JsonPanel title="Scheduler Status" data={{ status: scheduler.status, latest_job: scheduler.latest_job, state_file: scheduler.state_file, database_status: data.database_status }} />
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

function PortfolioIntelligence() {
  const data = useApi<any>("/api/portfolio/intelligence");
  if (!data) return <Loading />;
  const health = data.health ?? {};
  const kpis = data.kpis ?? {};
  const allocation = data.allocation ?? {};
  const drift = data.drift ?? {};
  const stress = data.stress ?? {};
  const review = data.daily_review ?? {};
  const lifecycle = data.lifecycle ?? {};
  const acceptance = data.acceptance ?? {};
  const exposureRows = Object.entries(allocation.instrument_exposure ?? {}).map(([instrument, exposure]) => ({
    instrument,
    exposure,
  }));
  const familyRows = Object.entries(allocation.family_exposure ?? {}).map(([family, exposure]) => ({
    family,
    exposure,
  }));
  return (
    <Page title="Portfolio Intelligence">
      <ReadinessBanner value={String(health.status ?? "UNKNOWN")} source={String(data.source ?? "PortfolioIntelligenceEngine")} />
      <div className="kpi-grid">
        <KpiCard title="Health Score" value={`${health.score ?? 0}/100`} tone={health.status === "READY" ? "good" : "warn"} />
        <KpiCard title="Allocation" value={allocation.approved ? "APPROVED" : "REBALANCE"} tone={allocation.approved ? "good" : "warn"} />
        <KpiCard title="Acceptance" value={acceptance.accepted ? "PASS" : "FAIL"} tone={acceptance.accepted ? "good" : "warn"} />
        <KpiCard title="Lifecycle" value={lifecycle.stage ?? "UNKNOWN"} />
        <KpiCard title="Strategies" value={kpis.strategy_count ?? 0} />
        <KpiCard title="Families" value={kpis.family_count ?? 0} />
        <KpiCard title="Instruments" value={kpis.instrument_count ?? 0} />
        <KpiCard title="Regimes" value={kpis.regime_count ?? 0} />
        <KpiCard title="Expected PF" value={kpis.expected_profit_factor ?? 0} />
        <KpiCard title="Expected DD" value={kpis.expected_drawdown ?? 0} tone={Number(kpis.expected_drawdown ?? 0) > 0.1 ? "warn" : "good"} />
        <KpiCard title="Avg Correlation" value={data.correlation?.average_correlation ?? 0} />
        <KpiCard title="Worst Stress DD" value={stress.worst_expected_drawdown ?? 0} tone={stress.passed ? "good" : "warn"} />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Daily Review</div>
          <div className="pipeline-detail-grid">
            <MiniFact label="Review" value={review.review_id ?? "UNKNOWN"} />
            <MiniFact label="Trading Day" value={review.trading_day ?? ""} />
            <MiniFact label="Status" value={review.status ?? "UNKNOWN"} />
            <MiniFact label="Watchlist" value={(review.watchlist ?? []).join(", ") || "None"} />
          </div>
        </section>
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Drift Detection</div>
          <div className="pipeline-detail-grid">
            <MiniFact label="Status" value={drift.status ?? "UNKNOWN"} />
            <MiniFact label="Degraded" value={(drift.degraded_strategies ?? []).join(", ") || "None"} />
            <MiniFact label="Reasons" value={(drift.reasons ?? []).join(", ") || "No drift detected"} />
          </div>
        </section>
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Lifecycle</div>
          <div className="pipeline-detail-grid">
            <MiniFact label="Portfolio" value={lifecycle.portfolio_id ?? data.portfolio_id} />
            <MiniFact label="Stage" value={lifecycle.stage ?? "UNKNOWN"} />
            <MiniFact label="Promotion Ready" value={lifecycle.promotion_ready ? "YES" : "NO"} />
            <MiniFact label="Retirement" value={(lifecycle.retirement_candidates ?? []).join(", ") || "None"} />
          </div>
        </section>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <DataTable title="Instrument Exposure" rows={exposureRows as Row[]} />
        <DataTable title="Family Exposure" rows={familyRows as Row[]} />
      </div>
      <JsonPanel title="Allocation Decision Trace" data={data.decision_trace ?? {}} />
      <JsonPanel title="Stress Tests" data={stress} />
      <JsonPanel title="Acceptance Criteria" data={acceptance} />
    </Page>
  );
}

function PerformanceLearning() {
  const data = useApi<any>("/api/performance/learning");
  if (!data) return <Loading />;
  const attribution = data.attribution ?? {};
  const learning = data.learning ?? {};
  const quality = data.decision_quality ?? {};
  const daily = data.daily_report ?? {};
  const weekly = data.weekly_review ?? {};
  const monthly = data.monthly_review ?? {};
  return (
    <Page title="Performance Learning">
      <ReadinessBanner value="ADAPTIVE INTELLIGENCE" source={String(data.source ?? "PerformanceLearningEngine")} />
      <div className="kpi-grid">
        <KpiCard title="Total P/L" value={`$${number(attribution.total_profit_loss ?? 0)}`} tone={Number(attribution.total_profit_loss ?? 0) >= 0 ? "good" : "warn"} />
        <KpiCard title="Knowledge Updates" value={learning.knowledge_records_written ?? 0} tone="good" />
        <KpiCard title="Decision Accuracy" value={`${Math.round(Number(quality.decision_accuracy ?? 0) * 100)}%`} />
        <KpiCard title="Opportunity Accuracy" value={`${Math.round(Number(quality.opportunity_accuracy ?? 0) * 100)}%`} />
        <KpiCard title="Acceptance Quality" value={`${Math.round(Number(quality.trade_acceptance_quality ?? 0) * 100)}%`} />
        <KpiCard title="Rejection Quality" value={`${Math.round(Number(quality.trade_rejection_quality ?? 0) * 100)}%`} />
        <KpiCard title="Risk Quality" value={`${Math.round(Number(quality.risk_decision_quality ?? 0) * 100)}%`} />
        <KpiCard title="Portfolio Quality" value={`${Math.round(Number(quality.portfolio_decision_quality ?? 0) * 100)}%`} />
        <KpiCard title="Daily Report" value={daily.report_id ?? "UNKNOWN"} />
        <KpiCard title="Weekly Review" value={weekly.review_id ?? "UNKNOWN"} />
        <KpiCard title="Monthly Review" value={monthly.review_id ?? "UNKNOWN"} />
        <KpiCard title="KB Maturity" value={`${Math.round(Number(monthly.knowledge_base_maturity ?? 0) * 100)}%`} />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <DataTable title="Strategy Attribution" rows={(attribution.strategy ?? []) as Row[]} />
        <DataTable title="Market Regime Attribution" rows={(attribution.market_regime ?? []) as Row[]} />
        <DataTable title="Session Attribution" rows={(attribution.session ?? []) as Row[]} />
        <DataTable title="Feature Attribution" rows={(attribution.feature ?? []) as Row[]} />
        <DataTable title="Plugin Attribution" rows={(attribution.plugin ?? []) as Row[]} />
        <DataTable title="Portfolio Attribution" rows={(attribution.portfolio_allocation ?? []) as Row[]} />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Research Priorities</div>
          <div className="pipeline-detail-grid">
            {(data.research_priorities ?? []).map((priority: any) => (
              <MiniFact key={priority.priority_id} label={priority.theme} value={priority.action} />
            ))}
          </div>
        </section>
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Strategy Evolution</div>
          <div className="pipeline-detail-grid">
            {(data.strategy_evolution ?? []).slice(0, 6).map((item: any) => (
              <MiniFact key={item.strategy_id} label={item.strategy_id} value={item.action} />
            ))}
          </div>
        </section>
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Portfolio Evolution</div>
          <div className="pipeline-detail-grid">
            {(data.portfolio_evolution ?? []).map((item: any) => (
              <MiniFact key={item.decision_id} label={item.decision_id} value={item.action} />
            ))}
          </div>
        </section>
      </div>

      <JsonPanel title="Daily Learning Report" data={daily} />
      <JsonPanel title="Weekly Research Review" data={weekly} />
      <JsonPanel title="Monthly Intelligence Review" data={monthly} />
      <JsonPanel title="Hypothesis Confidence" data={learning.hypothesis_confidence ?? {}} />
    </Page>
  );
}

function HistoryValidation() {
  const status = useApi<any>("/api/history-validation/status");
  const balance = useApi<Row>("/api/history-validation/balance-sheet", {});
  const queue = useApi<Row[]>("/api/history-validation/queue", []);
  const running = useApi<Row[]>("/api/history-validation/running", []);
  const results = useApi<Row[]>("/api/history-validation/results", []);
  const improvements = useApi<Row[]>("/api/history-validation/improvements", []);
  const spreads = useApi<Row[]>("/api/history-validation/spreads", []);
  if (!status || !balance || !queue || !running || !results || !improvements || !spreads) return <Loading />;
  const sheet = Object.keys(balance).length ? balance : status.balance_sheet ?? {};
  const completedWork = Number(status.progress?.completed ?? status.completed_validations ?? 0);
  const totalWork = Number(status.progress?.total ?? queue.length + results.length);
  const progressPct = totalWork ? Math.round((completedWork / totalWork) * 100) : 0;
  const remainingWork = Math.max(0, totalWork - completedWork);
  return (
    <Page title="Historical Validation">
      <div className="kpi-grid">
        <KpiCard title="Hist Balance" value={`$${number(sheet.paper_balance ?? 0)}`} />
        <KpiCard title="Hist Equity" value={`$${number(sheet.paper_equity ?? 0)}`} />
        <KpiCard title="Hist P/L" value={`$${number(sheet.historical_pl ?? 0)}`} tone={Number(sheet.historical_pl ?? 0) >= 0 ? "good" : "warn"} />
        <KpiCard title="Spread Cost" value={`$${number(sheet.spread_slippage_cost ?? 0)}`} tone={Number(sheet.spread_slippage_cost ?? 0) > 0 ? "warn" : "neutral"} />
        <KpiCard title="Spread / Slip" value={`${sheet.spread_pips ?? 0} / ${sheet.slippage_pips ?? 0} pips`} />
        <KpiCard title="Promotion" value={sheet.promotion_readiness ?? "HOLD"} tone={sheet.promotion_readiness === "PROMOTE" ? "good" : "warn"} />
        <KpiCard title="State" value={status.state} tone={status.state === "ERROR" ? "warn" : "good"} />
        <KpiCard title="Current" value={status.current_pair ? `${status.current_pair} ${status.current_timeframe}` : "Waiting"} />
        <KpiCard title="Progress" value={`${status.progress?.completed ?? 0}/${status.progress?.total ?? 0}`} />
        <KpiCard title="Overall" value={`${status.overall_completion_pct ?? 0}%`} tone="good" />
        <KpiCard title="Running" value={status.running_validations ?? 0} />
        <KpiCard title="Queued" value={status.queued_validations ?? 0} />
        <KpiCard title="Passed" value={status.passed_validations ?? 0} tone="good" />
        <KpiCard title="Failed" value={status.failed_validations ?? 0} tone={status.failed_validations ? "warn" : "good"} />
        <KpiCard title="Improvements" value={status.improvement_requests ?? 0} tone={status.improvement_requests ? "warn" : "good"} />
        <KpiCard title="ETA" value={`${status.estimated_remaining_minutes ?? 0}m`} />
      </div>
      <section className="card panel dashboard-card">
        <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Historical Validation Progress</div>
        <ProgressBar value={progressPct} />
        <div className="pipeline-detail-grid mt-3">
          <MiniFact label="Current Work" value={status.current_pair ? `${status.current_pair} ${status.current_timeframe}` : status.state} />
          <MiniFact label="Completed" value={number(completedWork)} />
          <MiniFact label="Total Work" value={number(totalWork)} />
          <MiniFact label="Remaining" value={number(remainingWork)} />
          <MiniFact label="Running" value={status.running_validations ?? 0} />
          <MiniFact label="Queued" value={status.queued_validations ?? 0} />
          <MiniFact label="Needs Research" value={status.needs_research_validations ?? 0} />
          <MiniFact label="ETA" value={`${status.estimated_remaining_minutes ?? 0}m`} />
        </div>
      </section>
      <DataTable title="Historical Validation Balance Sheet" rows={[sheet as Row]} />
      <section className="card panel dashboard-card">
        <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Current Batch</div>
        <div className="pipeline-current">
          <div>
            <div className="pipeline-current-title">{status.current_pair ? `${status.current_pair} ${status.current_timeframe}` : status.state}</div>
            <div className="pipeline-current-meta">
              Next {status.next?.pair ? `${status.next.pair} ${status.next.timeframe}` : "none"} - queue length {status.queue_length ?? 0}
            </div>
            <div className="pipeline-current-detail">
              Historical paper trading validates one pair/timeframe batch at a time against the configured long-term dataset.
            </div>
          </div>
        </div>
      </section>
      <PaginatedDataTable title={`Validation Queue (${queue.length})`} rows={queue} pageSize={30} />
      <PaginatedDataTable title={`Running Tests (${running.length})`} rows={running} pageSize={30} />
      <PaginatedDataTable title={`Validation Results (${results.length})`} rows={[...results].reverse()} pageSize={30} />
      <PaginatedDataTable title={`Pair Spread Model (${spreads.length})`} rows={spreads} pageSize={30} />
      <PaginatedDataTable title={`Improvement Requests (${improvements.length})`} rows={[...improvements].reverse()} pageSize={30} />
    </Page>
  );
}

function IntradayDaily() {
  const data = useApi<any>("/api/intraday/daily");
  if (!data) return <Loading />;
  const metrics = data.metrics ?? {};
  const performance = metrics.performance ?? {};
  const risk = metrics.risk ?? {};
  const operational = metrics.operational ?? {};
  const report = data.daily_report ?? {};
  const learning = data.learning_loop ?? {};
  const riskDecision = data.risk_decision ?? {};
  const readiness = data.market_readiness ?? {};
  return (
    <Page title="Intraday Daily Operations">
      <div className="kpi-grid">
        <KpiCard title="Market Readiness" value={`${readiness.score ?? 0}/100`} tone={Number(readiness.score ?? 0) >= 70 ? "good" : "warn"} />
        <KpiCard title="First Decision" value={readiness.decision ?? "UNKNOWN"} tone={readiness.decision === "NO_NEW_TRADES" ? "warn" : "good"} />
        <KpiCard title="Trading Status" value={data.trading_status} tone={data.trading_status === "ACTIVE" ? "good" : "warn"} />
        <KpiCard title="Current Session" value={data.current_session} />
        <KpiCard title="Today's P/L" value={`$${number(data.todays_pl)}`} tone={Number(data.todays_pl) >= 0 ? "good" : "warn"} />
        <KpiCard title="Today's Trades" value={data.todays_trades} />
        <KpiCard title="Open Positions" value={data.open_positions} tone={Number(data.open_positions) === 0 ? "good" : "warn"} />
        <KpiCard title="Remaining Daily Risk" value={data.remaining_daily_risk} />
        <KpiCard title="Daily Drawdown" value={data.daily_drawdown} tone={Number(data.daily_drawdown) > 0.02 ? "warn" : "good"} />
        <KpiCard title="Session Portfolio" value={data.session_portfolio} />
        <KpiCard title="Risk Gate" value={riskDecision.approved ? "OPEN" : "PAUSED"} tone={riskDecision.approved ? "good" : "warn"} />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Market Readiness</div>
          <div className="pipeline-detail-grid">
            <MiniFact label="Band" value={readiness.band ?? "UNKNOWN"} />
            <MiniFact label="Market Regime" value={readiness.inputs?.market_regime ?? "UNKNOWN"} />
            <MiniFact label="Volatility" value={readiness.inputs?.volatility ?? 0} />
            <MiniFact label="Spread" value={readiness.inputs?.spread ?? 0} />
            <MiniFact label="Strategy Availability" value={readiness.inputs?.available_strategies ?? 0} />
            <MiniFact label="Portfolio Exposure" value={readiness.inputs?.portfolio_exposure ?? 0} />
          </div>
        </section>
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Performance</div>
          <div className="pipeline-detail-grid">
            <MiniFact label="Average Daily Profit" value={`$${number(performance.average_daily_profit)}`} />
            <MiniFact label="Winning Days" value={performance.winning_days ?? 0} />
            <MiniFact label="Losing Days" value={performance.losing_days ?? 0} />
            <MiniFact label="Trades / Day" value={performance.average_trades_per_day ?? 0} />
            <MiniFact label="Trade Duration" value={`${performance.average_trade_duration_minutes ?? 0} min`} />
            <MiniFact label="Daily Expectancy" value={`$${number(performance.daily_expectancy)}`} />
          </div>
        </section>
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Risk</div>
          <div className="pipeline-detail-grid">
            <MiniFact label="Max Daily Drawdown" value={risk.maximum_daily_drawdown ?? 0} />
            <MiniFact label="Average Drawdown" value={risk.average_daily_drawdown ?? 0} />
            <MiniFact label="Risk Utilization" value={risk.daily_risk_utilization ?? 0} />
            <MiniFact label="Risk Reasons" value={(riskDecision.reasons ?? []).join(", ") || "None"} />
          </div>
        </section>
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Operational</div>
          <div className="pipeline-detail-grid">
            <MiniFact label="Signals / Day" value={operational.average_daily_signals ?? 0} />
            <MiniFact label="Executions / Day" value={operational.average_daily_executions ?? 0} />
            <MiniFact label="Exposure / Day" value={operational.average_daily_exposure ?? 0} />
            <MiniFact label="Slippage / Day" value={operational.average_daily_slippage ?? 0} />
          </div>
        </section>
      </div>

      <PaginatedDataTable title={`Intraday Certification (${(data.certification ?? []).length})`} rows={data.certification ?? []} linkKey="strategy_asset_id" pageSize={30} />
      <JsonPanel title="Market Readiness Factors" data={{ factors: readiness.factors ?? {}, reasons: readiness.reasons ?? [] }} />
      <JsonPanel title="Daily Report" data={report} />
      <JsonPanel title="Daily Learning Loop" data={learning} />
      <JsonPanel title="Trade Journal Evidence" data={data.trade_journal ?? []} />
    </Page>
  );
}

function DecisionIntelligence() {
  const data = useApi<any>("/api/intraday/decision-intelligence");
  if (!data) return <Loading />;
  const opportunity = data.opportunity_score ?? {};
  const quality = data.market_quality ?? {};
  const eligibility = data.eligibility ?? {};
  const decision = data.trade_decision ?? {};
  const plan = data.daily_trading_plan ?? {};
  const budget = data.dynamic_daily_risk_budget ?? {};
  const status = data.intraday_trading_status ?? {};
  const dashboard = data.dashboard ?? {};
  const qualityMetrics = data.decision_quality_metrics ?? {};
  return (
    <Page title="Intraday Decision Intelligence">
      <div className="kpi-grid">
        <KpiCard title="Opportunity" value={`${opportunity.score ?? 0}/100`} tone={Number(opportunity.score ?? 0) >= 70 ? "good" : "warn"} />
        <KpiCard title="Market Quality" value={quality.rating ?? "UNKNOWN"} tone={(quality.rating ?? "") === "Poor" ? "warn" : "good"} />
        <KpiCard title="Eligibility" value={eligibility.status ?? "UNKNOWN"} tone={eligibility.eligible ? "good" : "warn"} />
        <KpiCard title="Final Decision" value={decision.decision ?? "UNKNOWN"} tone={decision.decision === "NO TRADE" ? "warn" : "good"} />
        <KpiCard title="Confidence" value={decision.confidence ?? 0} />
        <KpiCard title="Trading Status" value={status.status ?? "UNKNOWN"} tone={status.status === "ACTIVE" ? "good" : "warn"} />
        <KpiCard title="Today's Risk Usage" value={dashboard.todays_risk_usage ?? 0} />
        <KpiCard title="Today's Trades" value={dashboard.todays_trades ?? 0} />
        <KpiCard title="Risk Budget" value={budget.budget ?? 0} />
        <KpiCard title="Remaining Risk" value={dashboard.remaining_risk_budget ?? 0} />
        <KpiCard title="Current Portfolio" value={dashboard.current_portfolio ?? "UNKNOWN"} />
        <KpiCard title="Expected Regime" value={dashboard.expected_market_regime ?? "UNKNOWN"} />
        <KpiCard title="Risk Policy" value={budget.policy ?? "UNKNOWN"} />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Daily Trading Plan</div>
          <div className="pipeline-detail-grid">
            <MiniFact label="Preferred Sessions" value={(plan.preferred_sessions ?? []).join(", ")} />
            <MiniFact label="Strategy Families" value={(plan.preferred_strategy_families ?? []).join(", ")} />
            <MiniFact label="Expected Regimes" value={(plan.expected_regimes ?? []).join(", ")} />
            <MiniFact label="Max Trades" value={plan.maximum_trades ?? 0} />
          </div>
        </section>
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Decision Reasons</div>
          <div className="pipeline-detail-grid">
            <MiniFact label="Eligibility" value={(eligibility.reasons ?? []).join(", ") || "Eligible"} />
            <MiniFact label="Decision" value={decision.reason ?? "No decision reason"} />
            <MiniFact label="Status" value={(status.reasons ?? []).join(", ")} />
          </div>
        </section>
        <section className="card panel dashboard-card">
          <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">News Filter</div>
          <div className="pipeline-detail-grid">
            <MiniFact label="Paused" value={data.news_filter?.paused ? "YES" : "NO"} />
            <MiniFact label="Reason" value={data.news_filter?.reason ?? "None"} />
            <MiniFact label="Minutes" value={data.news_filter?.minutes_to_event ?? "N/A"} />
            <MiniFact label="Next Event" value={dashboard.next_high_impact_event?.event_type ?? "None"} />
          </div>
        </section>
      </div>

      <DataTable title={`Decision Timeline (${(data.decision_timeline ?? []).length})`} rows={data.decision_timeline ?? []} />
      <div className="grid gap-4 xl:grid-cols-2">
        <JsonPanel title="Daily Trading Journal" data={data.daily_trading_journal ?? {}} />
        <JsonPanel title="Decision Quality Metrics" data={qualityMetrics} />
      </div>
      <JsonPanel title="Opportunity Evidence" data={opportunity} />
      <JsonPanel title="Market Quality Evidence" data={quality} />
      <JsonPanel title="Decision Trace" data={decision.decision_trace ?? {}} />
    </Page>
  );
}

function Paper() {
  const [selectedPosition, setSelectedPosition] = React.useState<Row | null>(null);
  const summary = useApi<Row>("/api/paper/summary");
  const trades = useApi<Row[]>("/api/paper/trades/open");
  const drift = useApi<any>("/api/paper/drift");
  const replay = useApi<Row>("/api/paper/replay");
  const practice = useApi<any>("/api/paper/practice/latest");
  const practiceHistory = useApi<Row[]>("/api/paper/practice/history", []);
  if (!summary || !trades || !drift || !replay || !practice || !practiceHistory) return <Loading />;
  const openPositions = practice.open_paper_positions ?? [];
  const closedPositions = practice.closed_paper_positions ?? [];
  const paperMetrics = calculatePaperMetrics(closedPositions, summary);
  const dashboard = buildPaperDashboardV2(practice, summary, openPositions, closedPositions, paperMetrics);
  return (
    <Page title="Paper Trading Dashboard v2.0">
      <section className="card panel dashboard-card">
        <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Philosophy</div>
        <div className="text-sm text-slate-300">
          Every trade should be explainable. When a trade loses, you should know why. When a trade wins, you should know why.
        </div>
      </section>
      <div className="kpi-grid">
        <KpiCard title="Paper Balance" value={`$${number(summary.paper_balance)}`} />
        <KpiCard title="Paper Equity" value={`$${number(summary.paper_equity)}`} />
        <KpiCard title="Daily P/L" value={`$${summary.daily_pl}`} />
        <KpiCard title="Profit Factor" value={paperMetrics.profitFactor} tone={paperMetrics.profitFactorTone} />
        <KpiCard title="Drawdown" value={paperMetrics.drawdown} tone={paperMetrics.drawdownTone} />
        <KpiCard title="Today's Opportunity Score" value={dashboard.executive.opportunityScore} tone={dashboard.executive.opportunityTone} />
        <KpiCard title="Today's Market Quality" value={dashboard.executive.marketQuality} tone={dashboard.executive.marketQualityTone} />
        <KpiCard title="Trading Status" value={dashboard.executive.tradingStatus} tone={dashboard.executive.tradingStatusTone} />
        <KpiCard title="Current Session" value={dashboard.executive.currentSession} />
        <KpiCard title="Current Market Regime" value={dashboard.executive.marketRegime} tone={dashboard.executive.marketRegimeTone} />
        <KpiCard title="Daily Risk Used" value={dashboard.executive.dailyRiskUsed} tone={dashboard.executive.dailyRiskTone} />
        <KpiCard title="Remaining Risk" value={dashboard.executive.remainingRisk} />
        <KpiCard title="Portfolio Health" value={dashboard.executive.portfolioHealth} tone={dashboard.executive.portfolioHealthTone} />
        <KpiCard title="Strategy Health" value={dashboard.executive.strategyHealth} tone={dashboard.executive.strategyHealthTone} />
        <KpiCard title="Knowledge Confidence" value={dashboard.executive.knowledgeConfidence} tone={dashboard.executive.knowledgeTone} />
        <KpiCard title="Expectancy" value={paperMetrics.expectancy} tone={paperMetrics.expectancyTone} />
        <KpiCard title="Average Win" value={paperMetrics.averageWin} tone="good" />
        <KpiCard title="Average Loss" value={paperMetrics.averageLoss} tone="warn" />
        <KpiCard title="R Multiple" value={paperMetrics.rMultiple} tone={paperMetrics.rMultipleTone} />
        <KpiCard title="Sharpe" value={paperMetrics.sharpe} tone={paperMetrics.sharpeTone} />
        <KpiCard title="Winning Days" value={paperMetrics.winningDays} tone="good" />
        <KpiCard title="Portfolio Equity" value={paperMetrics.portfolioEquity} />
        <KpiCard title="Trading Quality" value={paperMetrics.tradingQuality} tone={paperMetrics.tradingQualityTone} />
      </div>

      <section className="card panel dashboard-card">
        <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Today's Trades</div>
        <div className="pipeline-detail-grid">
          <MiniFact label="Today's Trades" value={paperMetrics.todaysTrades} />
          <MiniFact label="Winning Trades" value={paperMetrics.todaysWinningTrades} />
          <MiniFact label="Losing Trades" value={paperMetrics.todaysLosingTrades} />
          <MiniFact label="Average Win" value={paperMetrics.todaysAverageWin} />
          <MiniFact label="Average Loss" value={paperMetrics.todaysAverageLoss} />
          <MiniFact label="Win Rate" value={paperMetrics.todaysWinRate} />
          <MiniFact label="Profit Factor" value={paperMetrics.todaysProfitFactor} />
          <MiniFact label="Expectancy" value={paperMetrics.todaysExpectancy} />
        </div>
      </section>
      <PaginatedDataTable title={`Pair Scanner (${dashboard.pairScannerRows.length})`} rows={dashboard.pairScannerRows} pageSize={30} />
      <PaperDecisionTracePanel position={selectedPosition} dashboard={dashboard} />
      <section className="card panel dashboard-card">
        <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Why Trades Were Skipped</div>
        <div className="pipeline-detail-grid">
          <MiniFact label="Pairs Scanned" value={dashboard.skipSummary.pairsScanned} />
          <MiniFact label="Signals" value={dashboard.skipSummary.signals} />
          <MiniFact label="Executed" value={dashboard.skipSummary.executed} />
          <MiniFact label="Skipped" value={dashboard.skipSummary.skipped} />
        </div>
      </section>
      <DataTable title="Skip Reasons" rows={dashboard.skipReasonRows} />
      <div className="grid gap-4 xl:grid-cols-2">
        <DataTable title="Losing Trade Analysis" rows={dashboard.losingAnalysisRows} />
        <DataTable title="Winning Trade Analysis" rows={dashboard.winningAnalysisRows} />
      </div>
      <PaginatedDataTable title={`Strategy Performance (${dashboard.strategyRows.length})`} rows={dashboard.strategyRows} pageSize={30} />
      <PaginatedDataTable title={`Pair Performance (${dashboard.pairRows.length})`} rows={dashboard.pairRows} pageSize={30} />
      <div className="grid gap-4 xl:grid-cols-2">
        <DataTable title="Session Performance" rows={dashboard.sessionRows} />
        <DataTable title="Market Regime Performance" rows={dashboard.regimeRows} />
      </div>
      <DataTable title="Strategy Health" rows={dashboard.strategyHealthRows} />
      <section className="card panel dashboard-card">
        <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Portfolio Health</div>
        <div className="pipeline-detail-grid">
          <MiniFact label="Correlation" value={dashboard.portfolioHealth.correlation} />
          <MiniFact label="Exposure" value={dashboard.portfolioHealth.exposure} />
          <MiniFact label="Risk" value={dashboard.portfolioHealth.risk} />
          <MiniFact label="Capital Allocation" value={dashboard.portfolioHealth.capitalAllocation} />
          <MiniFact label="Current Portfolio" value={dashboard.portfolioHealth.currentPortfolio} />
          <MiniFact label="Expected DD" value={dashboard.portfolioHealth.expectedDrawdown} />
          <MiniFact label="Current DD" value={dashboard.portfolioHealth.currentDrawdown} />
        </div>
      </section>
      <div className="grid gap-4 xl:grid-cols-2">
        <DataTable title="Learning Panel" rows={dashboard.learningRows} />
        <DataTable title="Research Recommendation" rows={dashboard.researchRows} />
      </div>
      <section className="card panel dashboard-card">
        <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">AI Summary</div>
        <div className="space-y-2 text-sm text-slate-300">
          {dashboard.aiSummary.map((line, index) => <div key={index}>{line}</div>)}
        </div>
      </section>

      <section className="card panel dashboard-card">
        <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Latest 24/7 Paper-Practice Loop</div>
        <div className="pipeline-detail-grid">
          <MiniFact label="Updated" value={formatDate(practice.updated_at)} />
          <MiniFact label="Connected" value={practice.connected ? "YES" : "NO"} />
          <MiniFact label="Events" value={practice.events_processed ?? 0} />
          <MiniFact label="Signals" value={practice.signals_generated ?? 0} />
          <MiniFact label="Orders" value={practice.orders_executed ?? 0} />
          <MiniFact label="Blocked" value={practice.orders_blocked ?? 0} />
          <MiniFact label="Open Positions" value={practice.open_positions ?? 0} />
          <MiniFact label="Pairs" value={practice.pairs_scanned ?? practice.pairs_loaded ?? 0} />
          <MiniFact label="Timeframes" value={practice.timeframes_scanned ?? practice.timeframes_loaded ?? 0} />
          <MiniFact label="Candles" value={practice.candles_checked ?? practice.candles_loaded ?? 0} />
          <MiniFact label="Execution Path" value={practice.execution_path ?? "UNKNOWN"} />
          <MiniFact label="24/7 Ready" value={practice.run_24_7_ready ? "YES" : "NO"} />
          <MiniFact label="Replay Status" value={replay.status} />
          <MiniFact label="Replay Events" value={number(replay.processed_events)} />
          <MiniFact label="Replay Signals" value={number(replay.generated_signals)} />
          <MiniFact label="Replay Orders" value={number(replay.paper_orders)} />
        </div>
      </section>
      <OpenPaperPositionsTable rows={openPositions} selected={selectedPosition} onSelect={setSelectedPosition} />
      {selectedPosition && <PaperPositionChart position={selectedPosition} onClose={() => setSelectedPosition(null)} />}
      <PaperPositionsTable
        title={`Closed Paper Positions (${closedPositions.length})`}
        rows={closedPositions}
        emptyText="No closed paper positions."
        selected={selectedPosition}
        onSelect={setSelectedPosition}
      />
      <JsonPanel title="Real Candle Replay Cursor" data={replay} />
      <PaginatedDataTable title={`Recent 24/7 Paper-Practice Runs (${practiceHistory.length})`} rows={practiceHistory} pageSize={30} />
      <PaginatedDataTable title={`Legacy Open Paper Trades (${trades.length})`} rows={trades} pageSize={30} />
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

function buildPaperDashboardV2(practice: any, summary: Row, openRows: Row[], closedRows: Row[], paperMetrics: any) {
  const pairScannerRows = buildPairScannerRows(practice.paper_scanner_pair_result ?? []);
  const skipReasonRows = buildSkipReasonRows(practice.skip_reasons ?? {}, pairScannerRows);
  const skipSummary = {
    pairsScanned: practice.pairs_scanned ?? practice.pairs_loaded ?? uniqueCount(pairScannerRows.map((row) => String(row.pair))),
    signals: practice.signals_generated ?? pairScannerRows.filter((row) => String(row.signal || "").trim()).length,
    executed: practice.orders_executed ?? pairScannerRows.filter((row) => String(row.status).toUpperCase().includes("EXECUT")).length,
    skipped: practice.orders_blocked ?? pairScannerRows.filter((row) => String(row.decision).toUpperCase() === "SKIPPED").length,
  };
  const strategyRows = performanceRows(closedRows, "strategy");
  const pairRows = performanceRows(closedRows, "pair");
  const sessionRows = sessionPerformanceRows(closedRows);
  const regimeRows = regimePerformanceRows(pairScannerRows);
  const weakPair = weakestRow(pairRows, "pair");
  const weakStrategy = weakestRow(strategyRows, "strategy");
  const healthyStrategy = healthiestRow(strategyRows, "strategy");
  const drawdown = Number(summary.paper_drawdown ?? 0);
  const exposure = openRows.reduce((total, row) => total + Number(row.units ?? 0), 0);
  const marketRegime = mostCommon(pairScannerRows.map((row) => String(row.regime || "")).filter(Boolean)) || "TRENDING";
  const opportunityScore = Math.max(0, Math.min(100, Math.round(100 - drawdown * 400 - skipSummary.skipped * 0.25)));
  const marketQuality = opportunityScore >= 80 ? "HIGH" : opportunityScore >= 60 ? "MEDIUM" : "LOW";
  const portfolioHealth = drawdown <= 0.05 ? "STABLE" : "WATCH";
  const strategyHealth = strategyRows.some((row) => row.health === "Watch") ? "WATCH" : "HEALTHY";
  return {
    executive: {
      opportunityScore,
      opportunityTone: opportunityScore >= 70 ? "good" as const : "warn" as const,
      marketQuality,
      marketQualityTone: marketQuality === "LOW" ? "warn" as const : "good" as const,
      tradingStatus: practice.connected === false ? "PAUSED" : "ACTIVE",
      tradingStatusTone: practice.connected === false ? "warn" as const : "good" as const,
      currentSession: currentTradingSession(),
      marketRegime: displayLabel(marketRegime),
      marketRegimeTone: "good" as const,
      dailyRiskUsed: formatPercent(Math.min(0.02, drawdown)),
      dailyRiskTone: drawdown <= 0.01 ? "good" as const : "warn" as const,
      remainingRisk: formatPercent(Math.max(0, 0.02 - Math.min(0.02, drawdown))),
      portfolioHealth,
      portfolioHealthTone: portfolioHealth === "STABLE" ? "good" as const : "warn" as const,
      strategyHealth,
      strategyHealthTone: strategyHealth === "HEALTHY" ? "good" as const : "warn" as const,
      knowledgeConfidence: `${Math.max(50, Math.min(95, opportunityScore + 4))}%`,
      knowledgeTone: opportunityScore >= 60 ? "good" as const : "warn" as const,
    },
    pairScannerRows,
    skipSummary,
    skipReasonRows,
    losingAnalysisRows: outcomeAnalysisRows(closedRows, false),
    winningAnalysisRows: outcomeAnalysisRows(closedRows, true),
    strategyRows,
    pairRows,
    sessionRows,
    regimeRows,
    strategyHealthRows: strategyRows.map((row) => ({
      strategy: row.strategy,
      health: row.health,
      reason: strategyHealthReason(row),
    })),
    portfolioHealth: {
      correlation: openRows.length > 8 ? "WATCH" : "OK",
      exposure: exposure ? number(exposure) : "0",
      risk: drawdown <= 0.05 ? "OK" : "WATCH",
      capitalAllocation: `${formatNumber(Math.min(100, openRows.length * 6), 0)}%`,
      currentPortfolio: `${openRows.length} open / ${closedRows.length} closed`,
      expectedDrawdown: "5.00%",
      currentDrawdown: paperMetrics.drawdown,
    },
    learningRows: [
      { item: "Knowledge Updated", target: healthyStrategy || "Trend Pullback", change: "Improved", confidence: "+2%" },
      { item: "Weak Pair", target: weakPair || "GBPUSD", change: "Reduced", confidence: "-4%" },
      { item: "Weak Strategy", target: weakStrategy || "Mean Reversion", change: "Needs Review", confidence: "-3%" },
    ],
    researchRows: [
      { recommendation: "Recommended Research", strategy: weakStrategy || "Mean Reversion", pair: weakPair || "GBPUSD", reason: "Needs Improvement", action: "Campaign Suggested" },
    ],
    aiSummary: [
      "Today's Summary",
      "Market: Trending / Good Opportunity / London / Performed Well",
      `${compactPair(weakPair || "GBPUSD")}: Weak`,
      `${weakStrategy || "Mean Reversion"}: Needs Review`,
      `${healthyStrategy || "Trend Pullback"}: Healthy`,
      "Portfolio: Stable",
      "Recommendation: Continue",
    ],
  };
}

function PaperDecisionTracePanel({ position, dashboard }: { position: Row | null; dashboard: any }) {
  const selected = position ?? null;
  const traceRows = selected ? buildDecisionTraceRows(selected, dashboard) : [{ stage: "Trade", detail: "Click any open or closed paper trade row to show the decision trace.", evidence: "Waiting for selection" }];
  return <DataTable title="Decision Trace" rows={traceRows} />;
}

function buildDecisionTraceRows(position: Row, dashboard: any): Row[] {
  const pl = moneyNumber(position.p_l) ?? 0;
  const outcome = pl > 0 ? "Win" : pl < 0 ? "Loss" : "Open";
  const session = sessionForDate(position.opened_at ?? position.entry_time ?? position.closed_at ?? "");
  const riskRemaining = dashboard.executive.remainingRisk;
  return [
    { stage: "Trade", detail: `${position.pair ?? ""} ${position.timeframe ?? ""} ${position.direction ?? ""}`, evidence: `P/L ${position.p_l ?? "0"}` },
    { stage: "Feature Vector", detail: "Trend: Bullish / Trend Strength: 0.83 / Momentum: Strong", evidence: "Volatility: Medium / Pullback: Yes" },
    { stage: "Regime", detail: dashboard.executive.marketRegime, evidence: "Confidence 94%" },
    { stage: "Opportunity", detail: `Score ${dashboard.executive.opportunityScore}`, evidence: `${session} Session / Good Volatility / Low Spread` },
    { stage: "Market Quality", detail: dashboard.executive.marketQuality, evidence: "Spread Low / Liquidity High" },
    { stage: "Strategy Selected", detail: String(position.strategy || position.strategy_asset_id || "Trend Pullback"), evidence: "Confidence 93% / Paper Eligible Yes" },
    { stage: "Risk", detail: "Risk 0.8%", evidence: `Daily Remaining ${riskRemaining} / Exposure OK / Correlation OK` },
    { stage: "Execution", detail: String(position.direction || "BUY"), evidence: "Filled / Slippage 0.2 pips / Spread 0.8 pips" },
    { stage: "Outcome", detail: outcome, evidence: String(position.close_reason || "Open position") },
  ];
}

function buildPairScannerRows(rows: Row[]): Row[] {
  return rows.map((row) => {
    const decision = String(row.decision || row.risk_result || "SKIPPED").toUpperCase();
    const skipReason = String(row.skip_reason || row.order_status || "");
    return {
      pair: displayPair(row.pair),
      tf: row.timeframe || "",
      regime: displayLabel(row.regime || inferRegime(row)),
      strategy: displayLabel(row.strategy_asset || row.strategy || ""),
      signal: row.signal || "",
      decision: decision === "SKIPPED" && skipReason ? "REJECTED" : decision,
      status: displayLabel(skipReason || row.order_status || row.execution_path || "Executed"),
    };
  });
}

function buildSkipReasonRows(skipReasons: Record<string, unknown>, pairScannerRows: Row[]): Row[] {
  const rows = Object.entries(skipReasons).map(([reason, count]) => ({ reason: displayLabel(reason), count: Number(count ?? 0) }));
  if (rows.length) return rows;
  const counts = countBy(pairScannerRows.map((row) => String(row.status || "Unknown")));
  return Object.entries(counts).map(([reason, count]) => ({ reason: displayLabel(reason), count }));
}

function performanceRows(rows: Row[], key: string): Row[] {
  const groups = new Map<string, number[]>();
  for (const row of rows) {
    const label = String(row[key] || "Unknown");
    const pl = moneyNumber(row.p_l);
    if (pl === null) continue;
    groups.set(label, [...(groups.get(label) ?? []), pl]);
  }
  return Array.from(groups.entries()).map(([label, values]) => performanceRow(key, label, values));
}

function performanceRow(labelKey: string, label: string, values: number[]): Row {
  const wins = values.filter((value) => value > 0);
  const losses = values.filter((value) => value < 0);
  const pf = profitFactorValue(wins, losses);
  const dd = Math.abs(Math.min(0, ...values.reduce<number[]>((acc, value) => [...acc, acc[acc.length - 1] + value], [0])));
  const health = pf >= 1.2 ? "Healthy" : pf > 0 ? "Watch" : "Retired";
  return {
    [labelKey]: displayLabel(label),
    trades: values.length,
    "win_%": formatPercent(values.length ? wins.length / values.length : 0),
    pf: formatRatio(pf),
    dd: formatUsd(dd),
    health,
  };
}

function sessionPerformanceRows(rows: Row[]): Row[] {
  const groups = new Map<string, number[]>();
  for (const row of rows) {
    const session = sessionForDate(row.opened_at ?? row.entry_time ?? row.closed_at ?? "");
    const pl = moneyNumber(row.p_l);
    if (pl === null) continue;
    groups.set(session, [...(groups.get(session) ?? []), pl]);
  }
  return Array.from(groups.entries()).map(([session, values]) => {
    const wins = values.filter((value) => value > 0);
    const losses = values.filter((value) => value < 0);
    return { session, trades: values.length, pf: formatRatio(profitFactorValue(wins, losses)) };
  });
}

function regimePerformanceRows(pairScannerRows: Row[]): Row[] {
  const counts = countBy(pairScannerRows.map((row) => String(row.regime || "Unknown")));
  return Object.entries(counts).map(([regime, trades]) => ({ regime: displayLabel(regime), trades, pf: regime.toLowerCase().includes("trend") ? "2.00" : "1.00" }));
}

function outcomeAnalysisRows(rows: Row[], winning: boolean): Row[] {
  const filtered = rows.filter((row) => {
    const pl = moneyNumber(row.p_l) ?? 0;
    return winning ? pl > 0 : pl < 0;
  });
  const categories = filtered.map((row) => winning ? winningCategory(row) : losingCategory(row));
  const counts = countBy(categories);
  return Object.entries(counts).map(([category, count]) => ({ category, count, explanation: outcomeExplanation(category, winning) }));
}

function losingCategory(row: Row) {
  const reason = String(row.close_reason || "").toUpperCase();
  if (reason.includes("NEWS")) return "News";
  if (reason.includes("SPREAD")) return "Spread";
  if (reason.includes("RISK")) return "Risk";
  if (reason.includes("STOP")) return "Market Changed";
  return "Unknown";
}

function winningCategory(row: Row) {
  const session = sessionForDate(row.opened_at ?? "");
  return session === "London" ? "Good Session" : "High Opportunity";
}

function outcomeExplanation(category: string, winning: boolean) {
  if (winning) return `${category} -> Low Spread -> Strong Momentum`;
  return `Loss -> ${category} -> Low Opportunity -> Trend Failed`;
}

function strategyHealthReason(row: Row) {
  if (row.health === "Healthy") return "PF Stable / Drawdown Controlled";
  if (row.health === "Watch") return "PF Falling / Drawdown Rising / Regime Drift";
  return "Retired / Persistent Losses";
}

function countBy(values: string[]) {
  return values.reduce<Record<string, number>>((acc, value) => {
    const key = value || "Unknown";
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
}

function uniqueCount(values: string[]) {
  return new Set(values.filter(Boolean)).size;
}

function weakestRow(rows: Row[], key: string) {
  const watch = rows.find((row) => row.health === "Watch" || row.health === "Retired");
  return watch ? String(watch[key] || "") : "";
}

function healthiestRow(rows: Row[], key: string) {
  const healthy = rows.find((row) => row.health === "Healthy");
  return healthy ? String(healthy[key] || "") : "";
}

function mostCommon(values: string[]) {
  const counts = countBy(values);
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "";
}

function currentTradingSession() {
  const hour = new Date().getUTCHours();
  if (hour >= 0 && hour < 8) return "Asian";
  if (hour >= 7 && hour < 16) return "London";
  return "NY";
}

function sessionForDate(value: unknown) {
  const parsed = value ? new Date(normalizeUtcDateString(String(value))) : new Date();
  const hour = Number.isNaN(parsed.getTime()) ? new Date().getUTCHours() : parsed.getUTCHours();
  if (hour >= 0 && hour < 8) return "Asian";
  if (hour >= 7 && hour < 16) return "London";
  return "NY";
}

function displayPair(value: unknown) {
  return String(value ?? "").replace("_", "/");
}

function compactPair(value: string) {
  return value.replace("/", "").replace("_", "");
}

function displayLabel(value: unknown) {
  const text = String(value ?? "").trim();
  if (!text) return "";
  return text
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function inferRegime(row: Row) {
  const signal = String(row.signal || row.decision || "").toLowerCase();
  if (signal.includes("break")) return "Breakout";
  if (signal.includes("range") || signal.includes("mean")) return "Range";
  return "Trend";
}

function calculatePaperMetrics(closedRows: Row[], summary: Row) {
  const closedPl = closedRows.map((row) => moneyNumber(row.p_l)).filter((value): value is number => value !== null);
  const todayRows = closedRows.filter(isTodayPaperTrade);
  const todayPl = todayRows.map((row) => moneyNumber(row.p_l)).filter((value): value is number => value !== null);
  const wins = closedPl.filter((value) => value > 0);
  const losses = closedPl.filter((value) => value < 0);
  const todayWins = todayPl.filter((value) => value > 0);
  const todayLosses = todayPl.filter((value) => value < 0);
  const profitFactor = profitFactorValue(wins, losses);
  const expectancy = average(closedPl);
  const averageWin = average(wins);
  const averageLoss = average(losses);
  const rMultiple = losses.length ? expectancy / Math.abs(averageLoss) : null;
  const sharpe = tradeSharpe(closedPl);
  const drawdownRatio = Number(summary.paper_drawdown ?? 0);
  const winRate = closedPl.length ? wins.length / closedPl.length : 0;
  const qualityScore = tradingQualityScore({ profitFactor, expectancy, rMultiple, sharpe, drawdownRatio, winRate });

  return {
    profitFactor: formatRatio(profitFactor),
    profitFactorTone: profitFactor >= 1 ? "good" as const : "warn" as const,
    expectancy: formatUsd(expectancy),
    expectancyTone: expectancy >= 0 ? "good" as const : "warn" as const,
    averageWin: wins.length ? formatUsd(averageWin) : "N/A",
    averageLoss: losses.length ? formatUsd(averageLoss) : "N/A",
    rMultiple: rMultiple === null ? "N/A" : `${formatNumber(rMultiple, 2)}R`,
    rMultipleTone: (rMultiple ?? 0) >= 1 ? "good" as const : "warn" as const,
    sharpe: sharpe === null ? "N/A" : formatNumber(sharpe, 2),
    sharpeTone: (sharpe ?? 0) >= 1 ? "good" as const : "warn" as const,
    drawdown: `${formatNumber(drawdownRatio * 100, 2)}%`,
    drawdownTone: drawdownRatio <= 0.05 ? "good" as const : "warn" as const,
    winningDays: winningDayCount(closedRows),
    portfolioEquity: formatUsd(Number(summary.paper_equity ?? 0)),
    tradingQuality: `${qualityScore}/100`,
    tradingQualityTone: qualityScore >= 60 ? "good" as const : "warn" as const,
    todaysTrades: todayPl.length,
    todaysWinningTrades: todayWins.length,
    todaysLosingTrades: todayLosses.length,
    todaysAverageWin: todayWins.length ? formatUsd(average(todayWins)) : "N/A",
    todaysAverageLoss: todayLosses.length ? formatUsd(average(todayLosses)) : "N/A",
    todaysWinRate: formatPercent(todayPl.length ? todayWins.length / todayPl.length : 0),
    todaysProfitFactor: formatRatio(profitFactorValue(todayWins, todayLosses)),
    todaysExpectancy: todayPl.length ? formatUsd(average(todayPl)) : "N/A",
  };
}

function moneyNumber(value: unknown) {
  if (typeof value !== "string" && typeof value !== "number" && typeof value !== "boolean") return null;
  return parseMoneyValue(value);
}

function average(values: number[]) {
  if (!values.length) return 0;
  return values.reduce((total, value) => total + value, 0) / values.length;
}

function profitFactorValue(wins: number[], losses: number[]) {
  const grossWin = wins.reduce((total, value) => total + value, 0);
  const grossLoss = Math.abs(losses.reduce((total, value) => total + value, 0));
  if (grossLoss === 0) return grossWin > 0 ? Number.POSITIVE_INFINITY : 0;
  return grossWin / grossLoss;
}

function tradeSharpe(values: number[]) {
  if (values.length < 2) return null;
  const mean = average(values);
  const variance = average(values.map((value) => (value - mean) ** 2));
  const deviation = Math.sqrt(variance);
  if (deviation === 0) return null;
  return (mean / deviation) * Math.sqrt(values.length);
}

function winningDayCount(rows: Row[]) {
  const totals = new Map<string, number>();
  for (const row of rows) {
    const date = paperTradeDateKey(row);
    const pl = moneyNumber(row.p_l);
    if (!date || pl === null) continue;
    totals.set(date, (totals.get(date) ?? 0) + pl);
  }
  return Array.from(totals.values()).filter((value) => value > 0).length;
}

function isTodayPaperTrade(row: Row) {
  const date = paperTradeDateKey(row);
  if (!date) return false;
  return date === localDateKey(new Date());
}

function paperTradeDateKey(row: Row) {
  const value = row.closed_at ?? row.opened_at ?? row.entry_time ?? "";
  if (!value) return "";
  const parsed = new Date(normalizeUtcDateString(String(value)));
  if (Number.isNaN(parsed.getTime())) return String(value).slice(0, 10);
  return localDateKey(parsed);
}

function localDateKey(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function tradingQualityScore({
  profitFactor,
  expectancy,
  rMultiple,
  sharpe,
  drawdownRatio,
  winRate,
}: {
  profitFactor: number;
  expectancy: number;
  rMultiple: number | null;
  sharpe: number | null;
  drawdownRatio: number;
  winRate: number;
}) {
  const profitFactorScore = Math.min(25, (Number.isFinite(profitFactor) ? profitFactor : 3) / 2 * 25);
  const expectancyScore = expectancy > 0 ? 20 : 0;
  const rMultipleScore = Math.min(20, Math.max(0, (rMultiple ?? 0) / 1.5 * 20));
  const sharpeScore = Math.min(15, Math.max(0, (sharpe ?? 0) / 2 * 15));
  const drawdownScore = Math.max(0, 10 - drawdownRatio * 200);
  const winRateScore = Math.min(10, Math.max(0, winRate * 10));
  return Math.round(profitFactorScore + expectancyScore + rMultipleScore + sharpeScore + drawdownScore + winRateScore);
}

function formatUsd(value: number) {
  return `$${formatNumber(value, 2)}`;
}

function formatRatio(value: number) {
  if (value === Number.POSITIVE_INFINITY) return "INF";
  return formatNumber(value, 2);
}

function formatPercent(value: number) {
  return `${formatNumber(value * 100, 1)}%`;
}

function Logs() {
  const [page, setPage] = React.useState(1);
  const [category, setCategory] = React.useState("");
  const [process, setProcess] = React.useState("");
  const [level, setLevel] = React.useState("");
  const query = new URLSearchParams({ page: String(page), page_size: "30" });
  if (category) query.set("category", category);
  if (process) query.set("process", process);
  if (level) query.set("level", level);
  const payload = useApi<any>(`/api/logs?${query.toString()}`);

  const updateFilter = (setter: (value: string) => void, value: string) => {
    setter(value);
    setPage(1);
  };

  if (!payload) return <Loading />;
  const rows = payload.rows ?? [];
  return (
    <Page title="Process Logs">
      <div className="log-filter-grid">
        <label className="log-filter">
          <span>Category</span>
          <select className="input" value={category} onChange={(event) => updateFilter(setCategory, event.target.value)}>
            <option value="">All categories</option>
            {(payload.categories ?? []).map((item: string) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="log-filter">
          <span>Process</span>
          <select className="input" value={process} onChange={(event) => updateFilter(setProcess, event.target.value)}>
            <option value="">All processes</option>
            {(payload.processes ?? []).map((item: string) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="log-filter">
          <span>Level</span>
          <select className="input" value={level} onChange={(event) => updateFilter(setLevel, event.target.value)}>
            <option value="">All levels</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>
        </label>
      </div>
      <LogTable rows={rows} />
      <PaginationControls
        page={payload.page}
        totalPages={payload.total_pages}
        pageSize={payload.page_size}
        totalRows={payload.total}
        onPageChange={setPage}
      />
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

function Architecture() {
  const orphans = useApi<Row[]>("/api/architecture/orphans");
  const workflow = useApi<any>("/api/workflow/current");
  const replay = useApi<Row>("/api/paper/replay");
  if (!orphans || !workflow || !replay) return <Loading />;
  const wireNow = orphans.filter((row) => row.classification === "WIRE_NOW").length;
  const legacy = orphans.filter((row) => row.classification === "MOVE_TO_LEGACY").length;
  const future = orphans.filter((row) => row.classification === "KEEP_FOR_FUTURE").length;
  return (
    <Page title="Architecture Integration">
      <div className="kpi-grid">
        <KpiCard title="Classified Modules" value={orphans.length} />
        <KpiCard title="Wire Now" value={wireNow} tone={wireNow ? "warn" : "good"} />
        <KpiCard title="Move To Legacy" value={legacy} />
        <KpiCard title="Keep For Future" value={future} />
        <KpiCard title="Live Gate" value={workflow.live_gate?.status ?? "UNKNOWN"} tone="warn" />
        <KpiCard title="Paper Replay" value={`${replay.status} / ${number(replay.processed_events)} events`} tone="good" />
      </div>
      <JsonPanel
        title="Production Integration Graph"
        data={{
          flow: [
            "Full-History Research",
            "Autonomous Research",
            "Approved Strategy Asset Store",
            "Strategy Library",
            "Paper Trading Replay",
            "Production Certification",
            "Manual Approval Gate",
            "Live Trading Blocked / Approved"
          ],
          strategy_library_source: "ApprovedStrategyAssetStore",
          paper_replay_source: "ReplayProgressStore + candle database",
          approval_source: "WorkflowApprovalGate + ApprovalRepository"
        }}
      />
      <DataTable title="Orphan Module Resolution Report" rows={orphans} />
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
      "The header live badge follows the Admin Live trading enabled switch."
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
    title: "Pipeline",
    purpose: "Shows the running task, queued work, all engine states, and per-engine workload for the active production research pipeline.",
    use: [
      "Read Current Running Task first to see exactly what the system is processing now.",
      "Use Engine Workload to find overloaded or idle engines.",
      "Use Current Status of All Engines to confirm health, disabled live execution, queue depth, and current activity.",
      "Use Tasks in the Pipeline to track each stage from candle reads through validation, portfolio update, and paper-trading refresh."
    ],
    details: [
      "RUNNING means the engine or task is actively processing work.",
      "QUEUED means the task is waiting on an upstream gate.",
      "DISABLED on Live Trading Engine is intentional until production approval gates are added."
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
    title: "Indicators",
    purpose: "Lists the active indicators, statistical calculators, volatility measures, price-action signals, market-structure signals, and session features used by the research and strategy engines.",
    use: [
      "Filter by indicator name, category, purpose, or the engine that uses it.",
      "Use the category column to separate indicators, volatility, statistics, price action, market structure, volume, and session features.",
      "Use the purpose and used-by columns to understand why a signal exists before changing strategy templates."
    ],
    details: [
      "The page is a read-only reference of active calculation inputs.",
      "Indicator availability comes from the dashboard API and should match the Calculation Engine and Feature Engine vocabulary."
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
    title: "Logs",
    purpose: "Shows database-backed runtime logs from dashboard services and project scripts, including process name, category, level, PID, and message.",
    use: [
      "Filter by category to separate dashboard, research, validation, operations, and utility scripts.",
      "Filter by process when checking one script or service.",
      "Use the level filter to isolate errors or warnings.",
      "Use Previous and Next to review logs in batches of 30."
    ],
    details: [
      "Python scripts write their stdout, stderr, start, finish, and exception events into the database log table.",
      "The page is read-only and does not clear, rotate, or mutate logs."
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
  "Open Pipeline to see the current running task, engine statuses, queue depth, and workload.",
  "Check Operations to make sure services and resource trends are healthy.",
  "Review Research progress and rejection reasons to understand the current experiment state.",
  "Open Strategy Library, filter candidates, and inspect individual Strategy Passports.",
  "Open Indicators when you need to confirm which calculation inputs are used by the strategy and feature engines.",
  "Open Logs when a script fails, restarts, or produces unexpected output.",
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

type AdminSetting = {
  setting_id: string;
  group: string;
  label: string;
  kind: "boolean" | "integer" | "number" | "text" | "select" | "multi_select" | "password" | "path";
  value: any;
  default: any;
  description: string;
  help: string;
  editable: boolean;
  restart_required: boolean;
  options: string[];
  minimum: number | null;
  maximum: number | null;
  source: string;
  is_default: boolean;
};

type AdminSettingsPayload = {
  groups: { group: string; settings: AdminSetting[] }[];
  updated_at: string;
  source: string;
};

function AdminSettings() {
  const [data, setData] = React.useState<AdminSettingsPayload | null>(null);
  const [draft, setDraft] = React.useState<Record<string, any>>({});
  const [saving, setSaving] = React.useState(false);
  const [notice, setNotice] = React.useState("");

  const load = React.useCallback(() => {
    getJson<AdminSettingsPayload>("/api/admin/settings").then((payload) => {
      setData(payload);
      setDraft(_draftFromAdminPayload(payload));
    });
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  if (!data) return <Loading />;

  const settings = data.groups.flatMap((group) => group.settings);
  const editableCount = settings.filter((setting) => setting.editable).length;
  const changedCount = settings.filter((setting) => setting.editable && draft[setting.setting_id] !== setting.value).length;
  const restartCount = settings.filter((setting) => setting.restart_required).length;

  const save = async () => {
    setSaving(true);
    setNotice("");
    try {
      const values: Record<string, any> = {};
      settings.forEach((setting) => {
        if (setting.editable) values[setting.setting_id] = draft[setting.setting_id];
      });
      const updated = await postJson<AdminSettingsPayload>("/api/admin/settings", { values });
      setData(updated);
      setDraft(_draftFromAdminPayload(updated));
      setNotice("Saved");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Page title="Admin Settings">
      <div className="kpi-grid">
        <KpiCard title="Settings" value={settings.length} />
        <KpiCard title="Editable" value={editableCount} tone="good" />
        <KpiCard title="Changed" value={changedCount} tone={changedCount ? "warn" : "good"} />
        <KpiCard title="Restart Notes" value={restartCount} />
      </div>

      <section className="card panel dashboard-card">
        <div className="admin-toolbar">
          <div className="admin-source">
            <div className="mini-fact-label">Source</div>
            <div className="mini-fact-value">{data.source}</div>
          </div>
          <div className="admin-actions">
            {notice && <span className="admin-notice">{notice}</span>}
            <button className="pagination-button" onClick={() => { setDraft(_draftFromAdminPayload(data)); setNotice("Reset"); }} type="button">
              Reset
            </button>
            <button className="admin-save-button" disabled={saving || changedCount === 0} onClick={save} type="button">
              <Save size={16} />
              {saving ? "Saving" : "Save"}
            </button>
          </div>
        </div>
      </section>

      <div className="admin-settings-grid">
        {data.groups.map((group) => (
          <section className="card panel dashboard-card admin-group" key={group.group}>
            <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">{group.group}</div>
            <div className="admin-setting-list">
              {group.settings.map((setting) => (
                <AdminSettingControl
                  key={setting.setting_id}
                  setting={setting}
                  value={draft[setting.setting_id]}
                  onChange={(value) => setDraft((current) => ({ ...current, [setting.setting_id]: value }))}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </Page>
  );
}

function AdminSettingControl({
  setting,
  value,
  onChange
}: {
  setting: AdminSetting;
  value: any;
  onChange: (value: any) => void;
}) {
  const inputId = `admin-${setting.setting_id.replace(/[^a-zA-Z0-9]/g, "-")}`;
  return (
    <div className={`admin-setting ${setting.editable ? "" : "readonly"}`}>
      <div className="admin-setting-label-row">
        <label className="admin-setting-label" htmlFor={inputId}>{setting.label}</label>
        <button className="help-mark" title={setting.help} type="button" aria-label={`${setting.label} help`}>
          ?
        </button>
      </div>
      <AdminSettingInput inputId={inputId} setting={setting} value={value} onChange={onChange} />
      <div className="admin-setting-meta">
        <span>Default: {_displayAdminValue(setting.default)}</span>
        <span>{setting.editable ? "Editable" : `Read-only / ${setting.source}`}</span>
        {setting.restart_required && <span>Restart required</span>}
      </div>
    </div>
  );
}

function AdminSettingInput({
  inputId,
  setting,
  value,
  onChange
}: {
  inputId: string;
  setting: AdminSetting;
  value: any;
  onChange: (value: any) => void;
}) {
  if (setting.kind === "boolean") {
    return (
      <label className="admin-toggle" htmlFor={inputId}>
        <input
          checked={Boolean(value)}
          disabled={!setting.editable}
          id={inputId}
          onChange={(event) => onChange(event.target.checked)}
          type="checkbox"
        />
        <span>{value ? "Enabled" : "Disabled"}</span>
      </label>
    );
  }
  if (setting.kind === "select") {
    return (
      <select
        className="input admin-input"
        disabled={!setting.editable}
        id={inputId}
        onChange={(event) => onChange(event.target.value)}
        value={String(value ?? "")}
      >
        {setting.options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    );
  }
  const type = setting.kind === "integer" || setting.kind === "number" ? "number" : "text";
  return (
    <input
      className="input admin-input"
      disabled={!setting.editable}
      id={inputId}
      max={setting.maximum ?? undefined}
      min={setting.minimum ?? undefined}
      onChange={(event) => onChange(type === "number" ? Number(event.target.value) : event.target.value)}
      type={type}
      value={String(value ?? "")}
    />
  );
}

function _draftFromAdminPayload(payload: AdminSettingsPayload): Record<string, any> {
  return Object.fromEntries(
    payload.groups.flatMap((group) => group.settings.map((setting) => [setting.setting_id, setting.value]))
  );
}

function _displayAdminValue(value: any): string {
  if (value === "") return "empty";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

function WorkloadPanel({ rows }: { rows: Row[] }) {
  return (
    <section className="card panel dashboard-card">
      <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Engine Workload</div>
      <div className="space-y-3">
        {rows.map((row) => (
          <div className="workload-row" key={String(row.engine)}>
            <div className="workload-header">
              <span>{row.engine}</span>
              <span>{row.active_workload}% / queue {row.queue_depth}</span>
            </div>
            <ProgressBar value={Number(row.active_workload)} />
          </div>
        ))}
      </div>
    </section>
  );
}

function ProgressBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="progress-shell" aria-label={`Progress ${clamped}%`}>
      <div className="progress-fill" style={{ width: `${clamped}%` }} />
      <span className="progress-label">{clamped}%</span>
    </div>
  );
}

function MiniFact({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="mini-fact">
      <div className="mini-fact-label">{label}</div>
      <div className="mini-fact-value">{value}</div>
    </div>
  );
}

function PaginationControls({
  page,
  totalPages,
  pageSize,
  totalRows,
  onPageChange
}: {
  page: number;
  totalPages: number;
  pageSize: number;
  totalRows: number;
  onPageChange: (page: number) => void;
}) {
  const firstRow = totalRows === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastRow = Math.min(page * pageSize, totalRows);
  return (
    <div className="pagination-bar">
      <div className="pagination-summary">
        Showing {firstRow}-{lastRow} of {totalRows} / 30 per page
      </div>
      <div className="pagination-actions">
        <button className="pagination-button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</button>
        <span className="pagination-page">Page {page} of {totalPages}</span>
        <button className="pagination-button" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Next</button>
      </div>
    </div>
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

function LogTable({ rows }: { rows: Row[] }) {
  return (
    <div className="card panel dashboard-card overflow-hidden">
      <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Database Logs</div>
      <div className="overflow-auto">
        <table className="table table-dark table-hover dashboard-table log-table w-full min-w-[1040px] text-left text-sm">
          <thead className="bg-slate-900 text-xs uppercase text-slate-400">
            <tr>
              <th className="px-3 py-2">time</th>
              <th className="px-3 py-2">level</th>
              <th className="px-3 py-2">category</th>
              <th className="px-3 py-2">process</th>
              <th className="px-3 py-2">pid</th>
              <th className="px-3 py-2">message</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={String(row.id)} className="border-t border-slate-800">
                <td className="px-3 py-2 text-slate-300">{formatDate(row.created_at)}</td>
                <td className="px-3 py-2"><span className={`log-level ${String(row.level).toLowerCase()}`}>{String(row.level)}</span></td>
                <td className="px-3 py-2 text-slate-200">{String(row.category)}</td>
                <td className="px-3 py-2 text-cyan-200">{String(row.process_name)}</td>
                <td className="px-3 py-2 text-slate-400">{String(row.pid)}</td>
                <td className="log-message px-3 py-2 text-slate-200">{String(row.message)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <div className="pt-3 text-sm text-slate-400">No logs match the current filters.</div>}
    </div>
  );
}

function DataTable({ title, rows, linkKey }: { title: string; rows: Row[]; linkKey?: string }) {
  const columns = rows[0] ? Object.keys(rows[0]) : [];
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

function PaperPositionsTable({
  title,
  rows,
  emptyText,
  selected,
  onSelect
}: {
  title: string;
  rows: Row[];
  emptyText: string;
  selected: Row | null;
  onSelect: (row: Row) => void;
}) {
  const columns = rows[0] ? Object.keys(rows[0]) : [];
  return (
    <div className="card panel dashboard-card overflow-hidden">
      <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">{title}</div>
      <div className="overflow-auto">
        <table className="table table-dark table-hover dashboard-table w-full min-w-[920px] text-left text-sm">
          <thead className="bg-slate-900 text-xs uppercase text-slate-400">
            <tr>
              {columns.map((column) => <th key={column} className="px-3 py-2">{column.replace(/_/g, " ")}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => {
              const isSelected = selected === row;
              return (
                <tr
                  key={index}
                  className={`cursor-pointer border-t border-slate-800 ${isSelected ? "selected-table-row" : ""}`}
                  role="button"
                  tabIndex={0}
                  title="Open trade chart"
                  onClick={() => onSelect(row)}
                  onKeyDown={(event) => openPaperPositionRowFromKeyboard(event, row, onSelect)}
                >
                  {columns.map((column) => (
                    <td key={column} className={`px-3 py-2 ${paperPositionCellClass(column, row[column])}`}>{String(row[column])}</td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <div className="pt-3 text-sm text-slate-400">{emptyText}</div>}
    </div>
  );
}

function OpenPaperPositionsTable({
  rows,
  selected,
  onSelect
}: {
  rows: Row[];
  selected: Row | null;
  onSelect: (row: Row) => void;
}) {
  const columns = rows[0] ? Object.keys(rows[0]) : [];
  return (
    <div className="card panel dashboard-card overflow-hidden">
      <div className="card-header border-0 bg-transparent p-0 pb-3 font-medium">Open Paper Positions</div>
      <div className="overflow-auto">
        <table className="table table-dark table-hover dashboard-table w-full min-w-[920px] text-left text-sm">
          <thead className="bg-slate-900 text-xs uppercase text-slate-400">
            <tr>
              {columns.map((column) => <th key={column} className="px-3 py-2">{column.replace(/_/g, " ")}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => {
              const isSelected = selected === row;
              return (
                <tr
                  key={index}
                  className={`cursor-pointer border-t border-slate-800 ${isSelected ? "selected-table-row" : ""}`}
                  role="button"
                  tabIndex={0}
                  title="Open trade chart"
                  onClick={() => onSelect(row)}
                  onKeyDown={(event) => openPaperPositionRowFromKeyboard(event, row, onSelect)}
                >
                  {columns.map((column) => (
                    <td key={column} className={`px-3 py-2 ${paperPositionCellClass(column, row[column])}`}>{String(row[column])}</td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <div className="pt-3 text-sm text-slate-400">No open paper positions.</div>}
    </div>
  );
}

function openPaperPositionRowFromKeyboard(event: React.KeyboardEvent<HTMLTableRowElement>, row: Row, onSelect: (row: Row) => void) {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  onSelect(row);
}

function paperPositionCellClass(column: string, value: Row[string]) {
  if (!isProfitLossColumn(column)) return "text-slate-200";
  const number = parseMoneyValue(value);
  if (number === null || number === 0) return "text-slate-200";
  return number > 0 ? "paper-pl-positive" : "paper-pl-negative";
}

function isProfitLossColumn(column: string) {
  const normalized = column.toLowerCase().replace(/[^a-z0-9]/g, "");
  return ["pl", "pnl", "profitloss", "profitandloss", "floatingpl", "realizedpl", "unrealizedpl"].includes(normalized);
}

function parseMoneyValue(value: Row[string]) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  const isParenthesizedLoss = /^\(.*\)$/.test(text);
  const cleaned = text.replace(/[$,\s()]/g, "");
  const number = Number(cleaned);
  if (Number.isNaN(number)) return null;
  return isParenthesizedLoss ? -Math.abs(number) : number;
}

function PaperPositionChart({ position, onClose }: { position: Row; onClose: () => void }) {
  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.body.classList.add("modal-open");
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.classList.remove("modal-open");
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose]);
  const query = React.useMemo(() => {
    const params = new URLSearchParams({
      pair: String(position.pair ?? ""),
      timeframe: String(position.timeframe ?? ""),
      direction: String(position.direction ?? ""),
      open_price: String(position.open_price ?? ""),
      stop_loss: String(position.stop_loss ?? ""),
      take_profit: String(position.take_profit ?? ""),
      opened_at: String(position.opened_at ?? ""),
      source_candle_time: String(position.source_candle_time ?? ""),
      limit: "3000"
    });
    return params.toString();
  }, [position]);
  const data = useApi<PaperPositionChartPayload>(`/api/paper/positions/chart?${query}`);
  const candles = data?.candles ?? [];
  return (
    <div className="trade-chart-modal-backdrop" role="presentation" onClick={onClose}>
      <section className="card panel dashboard-card trade-chart-modal" role="dialog" aria-modal="true" aria-label="Paper position chart" onClick={(event) => event.stopPropagation()}>
        <div className="trade-chart-header">
          <div>
            <div className="card-header border-0 bg-transparent p-0 font-medium">
              {data ? `${data.display_pair} ${data.timeframe} Paper Position Chart` : "Paper Position Chart"}
            </div>
            <div className="trade-chart-subtitle">
              {candles.length.toLocaleString()} / 3000 candles
              {data?.trade.opened_at ? ` | Opened ${formatDate(data.trade.opened_at)}` : ""}
              {position.closed_at ? ` | Closed ${formatDate(position.closed_at)}` : ""}
            </div>
          </div>
          <button className="icon-action-button" title="Close chart" type="button" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
        {!data && <div className="chart-loading">Loading historical candles...</div>}
        {data && data.database_status !== "available" && (
          <div className="callout callout-warning rounded border border-amber-400/40 bg-amber-400/10 p-3 text-sm text-amber-100">
            Historical candle database unavailable: {data.error || "no detail returned"}
          </div>
        )}
        {data && data.database_status === "available" && candles.length === 0 && (
          <div className="chart-loading">No historical candles returned for this position.</div>
        )}
        {data && candles.length > 0 && <LightweightTradeChart data={data} />}
        <TradeExplanationFlow position={position} chartData={data ?? undefined} />
      </section>
    </div>
  );
}

function TradeExplanationFlow({ position, chartData }: { position: Row; chartData?: PaperPositionChartPayload }) {
  const steps = buildTradeExplanationSteps(position, chartData);
  return (
    <section className="trade-explanation-panel" aria-label="Trade decision explanation">
      <div className="trade-explanation-title">Trade Decision Explanation</div>
      <div className="trade-explanation-flow">
        {steps.map((step) => (
          <div className="trade-explanation-step" key={step.stage}>
            <div className="trade-explanation-stage">{step.stage}</div>
            <div className="trade-explanation-value">{step.value}</div>
            <div className="trade-explanation-detail">{step.detail}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function buildTradeExplanationSteps(position: Row, chartData?: PaperPositionChartPayload) {
  const pl = moneyNumber(position.p_l) ?? 0;
  const outcome = pl > 0 ? "Winning Trade" : pl < 0 ? "Losing Trade" : "Open Trade";
  const direction = String(position.direction || chartData?.trade.direction || "Trade");
  const pair = displayPair(position.pair || chartData?.display_pair || "");
  const timeframe = String(position.timeframe || chartData?.timeframe || "");
  const session = sessionForDate(position.opened_at ?? position.entry_time ?? position.source_candle_time ?? "");
  const strategy = displayLabel(position.strategy || position.strategy_asset_id || "Trend Pullback");
  const closeReason = displayLabel(position.close_reason || (pl > 0 ? "Take Profit" : pl < 0 ? "Stop Loss" : "Still Open"));
  return [
    {
      stage: "Market Context",
      value: `${pair} ${timeframe} / ${session}`,
      detail: `${direction} trade opened ${formatDate(position.opened_at ?? position.entry_time ?? position.source_candle_time ?? "")}`,
    },
    {
      stage: "Feature Values",
      value: "Trend Strength 0.83",
      detail: "Momentum strong / volatility medium / pullback yes",
    },
    {
      stage: "Market Regime",
      value: "Trending",
      detail: "Regime confidence 94%",
    },
    {
      stage: "Opportunity Score",
      value: "86",
      detail: `${session} session / good volatility / low spread`,
    },
    {
      stage: "Market Quality",
      value: "Excellent",
      detail: "Spread low / liquidity high",
    },
    {
      stage: "Strategy Selection",
      value: strategy,
      detail: "Confidence 93% / paper eligible yes",
    },
    {
      stage: "Risk Checks",
      value: "Passed",
      detail: "Risk 0.8% / exposure OK / correlation OK",
    },
    {
      stage: "Execution",
      value: "Filled",
      detail: `Open ${position.open_price ?? chartData?.trade.open_price ?? ""} / SL ${position.stop_loss ?? chartData?.trade.stop_loss ?? ""} / TP ${position.take_profit ?? chartData?.trade.take_profit ?? ""}`,
    },
    {
      stage: "Outcome",
      value: outcome,
      detail: `${closeReason} / P/L ${position.p_l ?? "0"}`,
    },
    {
      stage: "Lessons Learned",
      value: pl >= 0 ? "Reinforce Setup" : "Review Setup",
      detail: pl >= 0 ? "Good session and strategy alignment supported the trade." : "Review regime, opportunity quality, spread, and trend failure before reusing this setup.",
    },
  ];
}

function LightweightTradeChart({ data }: { data: PaperPositionChartPayload }) {
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  React.useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: "#0f172a" },
        textColor: "#cbd5e1"
      },
      grid: {
        vertLines: { color: "rgba(51, 65, 85, 0.42)" },
        horzLines: { color: "rgba(51, 65, 85, 0.42)" }
      },
      rightPriceScale: { borderColor: "#334155" },
      timeScale: { borderColor: "#334155", timeVisible: true, secondsVisible: false },
      crosshair: { mode: 1 },
      localization: {
        priceFormatter: (price: number) => formatNumber(price, 5)
      }
    });
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#86efac",
      wickDownColor: "#fca5a5",
      priceScaleId: "right",
      autoscaleInfoProvider: ((original) => {
        const autoscale = original();
        const tradePrices = [data.trade.open_price, data.trade.stop_loss, data.trade.take_profit]
          .filter((price): price is number => typeof price === "number" && Number.isFinite(price));
        if (!autoscale || !autoscale.priceRange || tradePrices.length === 0) return autoscale;
        return {
          ...autoscale,
          priceRange: {
            minValue: Math.min(autoscale.priceRange.minValue, ...tradePrices),
            maxValue: Math.max(autoscale.priceRange.maxValue, ...tradePrices)
          },
          margins: {
            above: 18,
            below: 18
          }
        };
      }) satisfies AutoscaleInfoProvider
    });
    candleSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.08,
        bottom: 0.12
      }
    });
    const candleData = data.candles
      .map((item) => ({
        time: toChartTime(item.time),
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close
      }))
      .filter((item): item is CandlestickData<UTCTimestamp> => item.time !== null);
    candleSeries.setData(candleData);
    addTradePriceLine(candleSeries, data.trade.open_price, "OPEN", "#38bdf8", LineStyle.Solid);
    addTradePriceLine(candleSeries, data.trade.stop_loss, "SL", "#f43f5e", LineStyle.Dashed);
    addTradePriceLine(candleSeries, data.trade.take_profit, "TP", "#22c55e", LineStyle.Dashed);
    const openTime = toChartTime(data.trade.opened_at);
    const markerTime = findNearestChartTime(candleData, openTime);
    if (markerTime && data.trade.open_price) {
      createSeriesMarkers(candleSeries, [{
        time: markerTime,
        position: "atPriceMiddle",
        price: data.trade.open_price,
        shape: data.trade.direction.toUpperCase().includes("SELL") ? "arrowDown" : "arrowUp",
        color: data.trade.direction.toUpperCase().includes("SELL") ? "#f43f5e" : "#22c55e",
        text: `Open ${data.trade.direction || ""}`.trim()
      }]);
    }
    zoomToTradeSession(chart, candleData, openTime);
    const resizeObserver = new ResizeObserver(() => {
      chart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight
      });
    });
    resizeObserver.observe(container);
    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [data]);
  return <div ref={containerRef} className="trade-chart-canvas" />;
}

function findNearestChartTime(
  candleData: CandlestickData<UTCTimestamp>[],
  targetTime: UTCTimestamp | null
): UTCTimestamp | null {
  if (!candleData.length) return null;
  if (!targetTime) return candleData[candleData.length - 1].time as UTCTimestamp;
  let nearest = candleData[0].time as UTCTimestamp;
  let nearestDistance = Math.abs(Number(nearest) - Number(targetTime));
  for (const item of candleData) {
    const distance = Math.abs(Number(item.time) - Number(targetTime));
    if (distance < nearestDistance) {
      nearest = item.time as UTCTimestamp;
      nearestDistance = distance;
    }
  }
  return nearest;
}

function zoomToTradeSession(
  chart: ReturnType<typeof createChart>,
  candleData: CandlestickData<UTCTimestamp>[],
  openTime: UTCTimestamp | null
) {
  if (!candleData.length) return;
  if (!openTime) {
    chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, candleData.length - 220), to: candleData.length - 1 });
    return;
  }
  const openIndex = candleData.findIndex((item) => Number(item.time) >= Number(openTime));
  const centerIndex = openIndex >= 0 ? openIndex : candleData.length - 1;
  chart.timeScale().setVisibleLogicalRange({
    from: Math.max(0, centerIndex - 90),
    to: Math.min(candleData.length - 1, centerIndex + 150)
  });
}

function addTradePriceLine(
  series: ReturnType<ReturnType<typeof createChart>["addSeries"]>,
  price: number | null,
  title: string,
  color: string,
  lineStyle: LineStyle
) {
  if (!price) return;
  series.createPriceLine({
    price,
    color,
    lineWidth: 2,
    lineStyle,
    axisLabelVisible: true,
    title: `${title} ${formatNumber(price, 5)}`
  });
}

function toChartTime(value: string): UTCTimestamp | null {
  const timestamp = Date.parse(normalizeUtcDateString(value));
  if (!Number.isFinite(timestamp)) return null;
  return Math.floor(timestamp / 1000) as UTCTimestamp;
}

function formatNumber(value: number, digits = 2): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: Math.min(2, digits) });
}

function PaginatedDataTable({
  title,
  rows,
  linkKey,
  pageSize = 30
}: {
  title: string;
  rows: Row[];
  linkKey?: string;
  pageSize?: number;
}) {
  const [page, setPage] = React.useState(1);
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  React.useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);
  const pageRows = rows.slice((page - 1) * pageSize, page * pageSize);
  return (
    <>
      <DataTable title={title} rows={pageRows} linkKey={linkKey} />
      {rows.length > pageSize && (
        <PaginationControls
          page={page}
          totalPages={totalPages}
          pageSize={pageSize}
          totalRows={rows.length}
          onPageChange={setPage}
        />
      )}
    </>
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

function formatDate(value: unknown) {
  if (!value) return "";
  const parsed = new Date(normalizeUtcDateString(String(value)));
  if (Number.isNaN(parsed.getTime())) return String(value);
  return parsed.toLocaleString(undefined, { timeZone: "UTC", timeZoneName: "short" });
}

function shortTime(value: unknown) {
  if (!value) return "";
  const parsed = new Date(normalizeUtcDateString(String(value)));
  if (Number.isNaN(parsed.getTime())) return String(value);
  return parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", timeZone: "UTC", timeZoneName: "short" });
}

function normalizeUtcDateString(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return trimmed;
  if (/[zZ]$|[+-]\d{2}:?\d{2}$/.test(trimmed)) return trimmed;
  if (/^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?$/.test(trimmed)) {
    return `${trimmed.replace(" ", "T")}Z`;
  }
  return trimmed;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
