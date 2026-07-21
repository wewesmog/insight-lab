"use client"

import { useEffect, useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Download, FileSpreadsheet, Radar } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { downloadAnalysisCsv, exportReportPdf } from "@/lib/api"
import type {
  AnalysisReport,
  DeepDiveInsight,
  SegmentStat,
  ThemeCount,
} from "@/lib/types"
import { cn } from "@/lib/utils"

const REPORT_SECTIONS = [
  { id: "executive", label: "Commentary" },
  { id: "snapshot", label: "Snapshot" },
  { id: "themes", label: "Themes" },
  { id: "deep-dive", label: "Deep dive" },
] as const

type ReportSectionId = (typeof REPORT_SECTIONS)[number]["id"]

const COLORS = {
  promoter: "#1f7a4d",
  passive: "#c4a35a",
  detractor: "#c45c4a",
  positive: "#2f6f5e",
  negative: "#b54a3c",
  neutral: "#8a8f98",
  mixed: "#6b5b95",
  low: "#3d7a5f",
  medium: "#c4a35a",
  high: "#b54a3c",
  bar: "#3d4f63",
}

function pct(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return "—"
  return `${n.toFixed(1)}%`
}

function num(n: number | null | undefined, digits = 1) {
  if (n == null || Number.isNaN(n)) return "—"
  return n.toFixed(digits)
}

function toChartRows(counts: Record<string, number> | undefined) {
  if (!counts) return []
  return Object.entries(counts).map(([name, value]) => ({
    name: name.replaceAll("_", " "),
    value,
  }))
}

function themeRows(items: ThemeCount[], analyzed: number) {
  const denom = Math.max(analyzed, 1)
  return items.slice(0, 10).map((i) => ({
    name: i.theme.replaceAll("_", " "),
    count: i.count,
    shareOfAnalyzed: (100 * i.count) / denom,
  }))
}

function severityClass(severity: DeepDiveInsight["severity"]) {
  if (severity === "urgent") return "border-destructive/40 bg-destructive/5"
  if (severity === "watch") return "border-warning/50 bg-warning/10"
  return "border-border/70 bg-muted/20"
}

function groupSegments(stats: SegmentStat[]) {
  const out: Record<string, SegmentStat[]> = {}
  for (const row of stats) {
    ;(out[row.column] ??= []).push(row)
  }
  return out
}

export function AnalysisReportView({ report }: { report: AnalysisReport }) {
  const { analysis, dataset, rollup } = report
  const summary = rollup?.executive_summary
  const metrics = rollup?.metrics
  const deep = rollup?.deep_dive
  const analyzed = rollup?.analyzed ?? 0

  const npsData = [
    { name: "Promoters", value: metrics?.nps_promoter_pct ?? 0, fill: COLORS.promoter },
    { name: "Passives", value: metrics?.nps_passive_pct ?? 0, fill: COLORS.passive },
    { name: "Detractors", value: metrics?.nps_detractor_pct ?? 0, fill: COLORS.detractor },
  ].filter((d) => d.value > 0)

  const sentimentData = toChartRows(rollup?.sentiment).map((d) => ({
    ...d,
    fill:
      d.name === "positive"
        ? COLORS.positive
        : d.name === "negative"
          ? COLORS.negative
          : d.name === "mixed"
            ? COLORS.mixed
            : COLORS.neutral,
  }))

  const churnData = toChartRows(rollup?.churn_risk).map((d) => ({
    ...d,
    fill:
      d.name === "high" ? COLORS.high : d.name === "medium" ? COLORS.medium : COLORS.low,
  }))

  const segmentsByColumn = groupSegments(deep?.segment_stats ?? [])
  const showSignals =
    (rollup?.competitor_switch_count ?? 0) > 0 || (rollup?.mixed_sentiment_count ?? 0) > 0

  const [activeSection, setActiveSection] = useState<ReportSectionId>("executive")

  useEffect(() => {
    const sectionEls = REPORT_SECTIONS.map((s) => document.getElementById(s.id)).filter(
      (el): el is HTMLElement => Boolean(el)
    )
    if (sectionEls.length === 0) return

    const scrollRoot =
      sectionEls[0].closest("[data-report-scroll]") ??
      sectionEls[0].closest(".overflow-y-auto")

    const visible = new Map<string, number>()

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            visible.set(entry.target.id, entry.intersectionRatio)
          } else {
            visible.delete(entry.target.id)
          }
        }
        let bestId: string | null = null
        let bestRatio = -1
        for (const section of REPORT_SECTIONS) {
          const ratio = visible.get(section.id) ?? -1
          if (ratio > bestRatio) {
            bestRatio = ratio
            bestId = section.id
          }
        }
        if (bestId) setActiveSection(bestId as ReportSectionId)
      },
      {
        root: scrollRoot instanceof Element ? scrollRoot : null,
        rootMargin: "-15% 0px -55% 0px",
        threshold: [0, 0.1, 0.25, 0.5, 0.75],
      }
    )

    for (const el of sectionEls) observer.observe(el)
    return () => observer.disconnect()
  }, [summary, rollup, deep])

  function goToSection(id: ReportSectionId) {
    setActiveSection(id)
    const el = document.getElementById(id)
    if (!el) return

    const root = el.closest("[data-report-scroll]") as HTMLElement | null
    if (root) {
      const rootRect = root.getBoundingClientRect()
      const elRect = el.getBoundingClientRect()
      // Keep section title clear of the sticky tab bar (~3.5rem).
      const offset = 64
      const nextTop = root.scrollTop + (elRect.top - rootRect.top) - offset
      root.scrollTo({ top: Math.max(0, nextTop), behavior: "smooth" })
      return
    }

    el.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  return (
    <div className="report-root mx-auto max-w-5xl space-y-12">
      {/* Sticky section tabs — stay visible while the report scrolls */}
      <div className="sticky top-0 z-20 -mx-1 mb-2 border-b border-border/60 bg-card/95 px-1 py-3 backdrop-blur-md print:static print:border-0 print:bg-transparent print:py-0">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/60 bg-[oklch(0.99_0.004_80)] px-3 py-2.5 shadow-sm print:hidden">
          <nav className="flex flex-wrap items-center gap-1 text-xs" aria-label="Report sections">
            {REPORT_SECTIONS.map((item) => {
              const active = activeSection === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => goToSection(item.id)}
                  aria-current={active ? "true" : undefined}
                  className={cn(
                    "rounded-md px-2.5 py-1.5 font-medium transition",
                    active
                      ? "bg-foreground text-background shadow-sm"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  {item.label}
                </button>
              )
            })}
          </nav>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                void downloadAnalysisCsv(analysis.id, analysis.name)
              }}
            >
              <FileSpreadsheet className="size-4" />
              Download CSV
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() => exportReportPdf(analysis.name)}
            >
              <Download className="size-4" />
              Export PDF
            </Button>
          </div>
        </div>
      </div>

      {/* Cover */}
      <header className="report-hero relative overflow-hidden rounded-2xl border border-border/60 bg-[linear-gradient(145deg,oklch(0.97_0.01_70),oklch(0.99_0.004_85)_45%,oklch(0.96_0.02_40))] px-6 py-8 sm:px-10">
        <div className="pointer-events-none absolute -right-16 -top-20 size-56 rounded-full bg-primary/10 blur-2xl print:hidden" />
        <div className="relative space-y-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Insight Lab · CX intelligence briefing
          </p>
          <h1 className="max-w-3xl font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
            {summary?.title || analysis.name}
          </h1>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <span>{analysis.name}</span>
            <span>·</span>
            <span>{dataset.filename}</span>
            <span>·</span>
            <span>{analysis.total_rows} verbatims</span>
            <span>·</span>
            <span>
              {analysis.finished_at
                ? new Date(analysis.finished_at).toLocaleString()
                : new Date(analysis.created_at).toLocaleString()}
            </span>
          </div>

          {metrics ? (
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <HeroStat
                label="Inferred NPS"
                value={num(metrics.nps_score, 0)}
                sub="From language (promoters − detractors)"
              />
              <HeroStat
                label="High churn"
                value={pct(metrics.high_churn_pct)}
                sub="Share of analyzed verbatims"
              />
              <HeroStat
                label="Analyzed"
                value={`${analyzed}`}
                sub={`${rollup?.skipped ?? 0} skipped · ${deep?.available_columns.length ?? 0} extra cols`}
              />
            </div>
          ) : null}
        </div>
      </header>

      {/* Watch-outs */}
      {showSignals ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {(rollup?.competitor_switch_count ?? 0) > 0 ? (
            <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-destructive">
                Watch · competitor switch
              </p>
              <p className="mt-1 text-sm">
                <span className="font-semibold tabular-nums">
                  {rollup?.competitor_switch_count}
                </span>{" "}
                verbatims signal switching or competitor comparison.
              </p>
            </div>
          ) : null}
          {(rollup?.mixed_sentiment_count ?? 0) > 0 ? (
            <div className="rounded-xl border border-warning/40 bg-warning/10 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-foreground/80">
                Watch · mixed sentiment
              </p>
              <p className="mt-1 text-sm">
                <span className="font-semibold tabular-nums">{rollup?.mixed_sentiment_count}</span>{" "}
                verbatims mix praise and complaint — often early churn risk.
              </p>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* 01 Executive first — what leadership reads */}
      {summary ? (
        <section id="executive" className="scroll-mt-28 space-y-6">
          <SectionHeading eyebrow="01" title="Executive commentary" />
          <div className="max-w-3xl space-y-4 text-[15px] leading-7 text-foreground/90 whitespace-pre-wrap">
            {summary.executive_overview}
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <NarrativeBlock title="Key findings" items={summary.key_findings} accent="findings" />
            <NarrativeBlock title="Priority issues" items={summary.priority_issues} accent="issues" />
            <NarrativeBlock
              title="Strengths to protect"
              items={summary.strengths_to_protect}
              accent="strengths"
            />
            <NarrativeBlock
              title="Recommended actions"
              items={summary.recommended_actions}
              accent="actions"
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
            <div className="rounded-xl border border-border/70 bg-[oklch(0.97_0.01_30)] p-5">
              <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                Risk commentary
              </h3>
              <p className="mt-2 text-[15px] leading-7 whitespace-pre-wrap">
                {summary.risk_commentary}
              </p>
            </div>
            <div className="rounded-xl border border-border/70 bg-card p-5">
              <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                Closing note
              </h3>
              <p className="mt-2 font-serif text-[15px] leading-7 italic text-foreground/85">
                {summary.closing_note}
              </p>
            </div>
          </div>
        </section>
      ) : (
        <p className="text-sm text-muted-foreground">Executive commentary unavailable for this run.</p>
      )}

      {/* 02 Snapshot charts */}
      {rollup ? (
        <section id="snapshot" className="scroll-mt-28 space-y-5">
          <SectionHeading
            eyebrow="02"
            title="Scorecard snapshot"
            subtitle="Deterministic mix from analyzed verbatims"
          />
          <div className="grid gap-5 lg:grid-cols-3">
            <ChartPanel title="NPS mix" subtitle="Promoters / passives / detractors (inferred)">
              <div className="relative h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={npsData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={52}
                      outerRadius={78}
                      paddingAngle={2}
                    >
                      {npsData.map((entry) => (
                        <Cell key={entry.name} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: number) => `${Number(v).toFixed(1)}%`} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">NPS</p>
                  <p className="font-serif text-2xl font-semibold tabular-nums">
                    {num(metrics?.nps_score, 0)}
                  </p>
                </div>
              </div>
              <LegendRows
                items={npsData.map((d) => ({
                  label: d.name,
                  value: `${d.value.toFixed(1)}%`,
                  color: d.fill,
                }))}
              />
            </ChartPanel>

            <ChartPanel title="Sentiment" subtitle="Count of analyzed verbatims">
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={sentimentData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e6e8eb" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                      {sentimentData.map((entry) => (
                        <Cell key={entry.name} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartPanel>

            <ChartPanel title="Churn risk" subtitle="Language-modelled risk bands">
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={churnData} dataKey="value" nameKey="name" outerRadius={78}>
                      {churnData.map((entry) => (
                        <Cell key={entry.name} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <LegendRows
                items={churnData.map((d) => ({
                  label: d.name,
                  value: String(d.value),
                  color: d.fill,
                }))}
              />
            </ChartPanel>
          </div>
        </section>
      ) : null}

      {/* 03 Themes */}
      {rollup ? (
        <section id="themes" className="scroll-mt-28 space-y-5">
          <SectionHeading
            eyebrow="03"
            title="Theme landscape"
            subtitle="% = share of analyzed verbatims that mention the item"
          />
          <div className="space-y-5">
            <RankedThemeBlock
              title="Top themes"
              items={rollup.top_themes}
              analyzed={analyzed}
              color={COLORS.bar}
            />
            <RankedThemeBlock
              title="Top issues"
              items={rollup.top_issues}
              analyzed={analyzed}
              color={COLORS.detractor}
            />
            <RankedThemeBlock
              title="Top delights"
              items={rollup.top_delights}
              analyzed={analyzed}
              color={COLORS.promoter}
            />
          </div>
        </section>
      ) : null}

      {/* 04 Deep dive */}
      <section id="deep-dive" className="scroll-mt-28 space-y-6">
        <SectionHeading
          eyebrow="04"
          title="Contextual deep dive"
          subtitle="Extra CSV columns, segment cuts, and suggested follow-ups"
        />

        {!deep ? (
          <p className="text-sm text-muted-foreground">
            Deep dive was not produced for this run. Re-run the analysis to generate it.
          </p>
        ) : (
          <>
          {deep.narrative ? (
            <p className="max-w-3xl text-[15px] leading-7 text-foreground/90 whitespace-pre-wrap">
              {deep.narrative}
            </p>
          ) : null}

          {deep.available_columns.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {deep.available_columns.map((col) => (
                <Badge key={col} variant="outline">
                  {col}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No extra columns in this CSV — insights below still use core fields.
            </p>
          )}

          {deep.insights.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {deep.insights.map((insight, idx) => (
                <div
                  key={`${insight.headline}-${idx}`}
                  className={cn("rounded-xl border p-4", severityClass(insight.severity))}
                >
                  <div className="flex items-center gap-2">
                    <Radar className="size-4 text-muted-foreground" />
                    <Badge variant="secondary" className="text-[10px] uppercase">
                      {insight.severity}
                    </Badge>
                  </div>
                  <p className="mt-2 font-medium">{insight.headline}</p>
                  <p className="mt-1 text-sm leading-6 text-foreground/85">{insight.detail}</p>
                  {insight.evidence ? (
                    <p className="mt-2 text-xs text-muted-foreground">{insight.evidence}</p>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No deep-dive insights for this dataset.</p>
          )}

          {deep.column_profiles.length > 0 ? (
            <div className="overflow-x-auto rounded-xl border border-border/70">
              <table className="w-full min-w-[36rem] text-left text-sm">
                <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2.5 font-medium">Column</th>
                    <th className="px-3 py-2.5 font-medium">Kind</th>
                    <th className="px-3 py-2.5 font-medium">Coverage</th>
                    <th className="px-3 py-2.5 font-medium">AI reading</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {deep.column_profiles.map((col) => (
                    <tr key={col.name} className="align-top">
                      <td className="px-3 py-3 font-medium">{col.name}</td>
                      <td className="px-3 py-3 capitalize text-muted-foreground">{col.kind}</td>
                      <td className="px-3 py-3 tabular-nums text-muted-foreground">
                        {col.non_null} · {col.unique_count} unique
                      </td>
                      <td className="px-3 py-3 text-[13px] leading-5 text-foreground/85">
                        {col.interpretation || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {Object.entries(segmentsByColumn).map(([column, rows]) => {
            const worstChurn = Math.max(...rows.map((r) => r.high_churn_pct ?? 0), 0)
            return (
              <div key={column} className="space-y-2">
                <h3 className="text-sm font-semibold tracking-wide">
                  Segment cut · <span className="text-primary">{column}</span>
                </h3>
                <div className="overflow-x-auto rounded-xl border border-border/70">
                  <table className="w-full min-w-[40rem] text-left text-sm">
                    <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2.5 font-medium">Value</th>
                        <th className="px-3 py-2.5 font-medium">n</th>
                        <th className="px-3 py-2.5 font-medium">Neg %</th>
                        <th className="px-3 py-2.5 font-medium">High churn %</th>
                        <th className="px-3 py-2.5 font-medium">Promoter %</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/60">
                      {rows.map((row) => {
                        const isWorst =
                          worstChurn > 0 && (row.high_churn_pct ?? 0) === worstChurn
                        return (
                          <tr
                            key={`${row.column}-${row.value}`}
                            className={cn(isWorst && "bg-destructive/5")}
                          >
                            <td className="px-3 py-2.5 font-medium">
                              {row.value}
                              {isWorst ? (
                                <span className="ml-2 text-[10px] font-semibold uppercase text-destructive">
                                  highest churn
                                </span>
                              ) : null}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">{row.count}</td>
                            <td className="px-3 py-2.5 tabular-nums">{pct(row.negative_pct)}</td>
                            <td className="px-3 py-2.5 tabular-nums font-medium">
                              {pct(row.high_churn_pct)}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">{pct(row.promoter_pct)}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          })}

          {/* Suggested analyses: kept in API rollup.deep_dive.suggested_analyses;
              hide from the business report until we can run them in-product. */}
          </>
        )}
      </section>

      <section className="print:hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-dashed border-border/80 bg-muted/20 px-5 py-4">
          <div>
            <p className="text-sm font-medium">Need the row-level detail?</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Download all analyzed verbatims as CSV — not rendered in this briefing.
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              void downloadAnalysisCsv(analysis.id, analysis.name)
            }}
          >
            <FileSpreadsheet className="size-4" />
            Download CSV
          </Button>
        </div>
      </section>

      <footer className="border-t border-border/70 pt-6 text-xs leading-5 text-muted-foreground">
        Prepared by Insight Lab for management review. KPIs and segment tables are computed in
        code. Narrative and column interpretation are LLM-assisted and grounded in those numbers.
      </footer>
    </div>
  )
}

function SectionHeading({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow: string
  title: string
  subtitle?: string
}) {
  return (
    <div className="space-y-1 border-b border-border/60 pb-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        {eyebrow}
      </p>
      <h2 className="font-serif text-2xl font-semibold tracking-tight">{title}</h2>
      {subtitle ? <p className="text-sm text-muted-foreground">{subtitle}</p> : null}
    </div>
  )
}

function HeroStat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="rounded-xl border border-border/50 bg-card/80 px-4 py-3 backdrop-blur">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 font-serif text-3xl font-semibold tabular-nums tracking-tight">{value}</p>
      <p className="text-[11px] text-muted-foreground">{sub}</p>
    </div>
  )
}

function ChartPanel({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-xl border border-border/70 bg-card p-4 shadow-sm">
      <div className="mb-2">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </div>
      {children}
    </div>
  )
}

function LegendRows({
  items,
}: {
  items: { label: string; value: string; color: string }[]
}) {
  return (
    <ul className="mt-1 space-y-1.5">
      {items.map((item) => (
        <li key={item.label} className="flex items-center justify-between gap-3 text-xs">
          <span className="inline-flex items-center gap-2">
            <span className="size-2.5 rounded-sm" style={{ background: item.color }} />
            <span className="capitalize">{item.label}</span>
          </span>
          <span className="tabular-nums text-muted-foreground">{item.value}</span>
        </li>
      ))}
    </ul>
  )
}

function RankedThemeBlock({
  title,
  items,
  analyzed,
  color,
}: {
  title: string
  items: ThemeCount[]
  analyzed: number
  color: string
}) {
  const data = themeRows(items, analyzed)
  const max = Math.max(...data.map((d) => d.count), 1)

  return (
    <div className="rounded-2xl border border-border/70 bg-card p-5 shadow-sm sm:p-6">
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <h3 className="font-serif text-xl font-semibold tracking-tight">{title}</h3>
          <p className="text-xs text-muted-foreground">
            Bars scaled to #1 · % is share of {analyzed || "—"} analyzed verbatims
          </p>
        </div>
        <Badge variant="outline">{data.length || 0} items</Badge>
      </div>
      {data.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">None detected</p>
      ) : (
        <ul className="space-y-3.5">
          {data.map((item, index) => (
            <li
              key={item.name}
              className="grid grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-3"
            >
              <span className="text-xs font-semibold tabular-nums text-muted-foreground">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div className="min-w-0 space-y-1.5">
                <p className="truncate text-sm font-medium capitalize">{item.name}</p>
                <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.max((item.count / max) * 100, 4)}%`,
                      background: color,
                    }}
                  />
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold tabular-nums">{item.count}</p>
                <p className="text-[11px] tabular-nums text-muted-foreground">
                  {item.shareOfAnalyzed.toFixed(0)}%
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function NarrativeBlock({
  title,
  items,
  accent,
}: {
  title: string
  items: string[]
  accent: "findings" | "issues" | "strengths" | "actions"
}) {
  const border =
    accent === "issues"
      ? "border-l-destructive/70"
      : accent === "strengths"
        ? "border-l-success/70"
        : accent === "actions"
          ? "border-l-primary/70"
          : "border-l-foreground/40"

  return (
    <div className={cn("rounded-xl border border-border/70 bg-card p-5 border-l-4", border)}>
      <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        {title}
      </h3>
      <ol className="mt-3 space-y-2.5">
        {items.map((item, index) => (
          <li key={`${title}-${index}`} className="flex gap-3 text-[15px] leading-6">
            <span className="mt-0.5 w-5 shrink-0 text-xs font-semibold tabular-nums text-muted-foreground">
              {String(index + 1).padStart(2, "0")}
            </span>
            <span>{item}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}
