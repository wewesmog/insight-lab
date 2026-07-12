import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { InsightsRollup } from "@/lib/types"
import { cn } from "@/lib/utils"

interface InsightsDashboardProps {
  rollup: InsightsRollup
  engine: string
}

function CountBar({
  label,
  count,
  total,
  tone,
}: {
  label: string
  count: number
  total: number
  tone?: "default" | "success" | "warning" | "destructive"
}) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="capitalize">{label.replace(/_/g, " ")}</span>
        <span className="text-muted-foreground">
          {count} ({pct}%)
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            tone === "success" && "bg-success",
            tone === "warning" && "bg-warning",
            tone === "destructive" && "bg-destructive",
            (!tone || tone === "default") && "bg-primary"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function ThemeList({ title, items }: { title: string; items: { theme: string; count: number }[] }) {
  if (!items.length) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No signals yet.</p>
        </CardContent>
      </Card>
    )
  }

  const max = items[0]?.count ?? 1
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.map((item) => (
          <div key={item.theme} className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="font-medium">{item.theme.replace(/_/g, " ")}</span>
              <span className="text-muted-foreground">{item.count}</span>
            </div>
            <div className="h-1.5 rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${Math.round((item.count / max) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export function InsightsDashboard({ rollup, engine }: InsightsDashboardProps) {
  const analyzed = rollup.analyzed || 1

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{engine} engine</Badge>
        <Badge variant="outline">{rollup.analyzed} analyzed</Badge>
        {rollup.skipped > 0 ? (
          <Badge variant="outline">{rollup.skipped} skipped (low signal)</Badge>
        ) : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Sentiment mix</CardDescription>
            <CardTitle className="text-2xl">{rollup.analyzed}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(rollup.sentiment).map(([key, count]) => (
              <CountBar
                key={key}
                label={key}
                count={count}
                total={analyzed}
                tone={
                  key === "positive"
                    ? "success"
                    : key === "negative"
                      ? "destructive"
                      : key === "mixed"
                        ? "warning"
                        : "default"
                }
              />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Churn risk</CardDescription>
            <CardTitle className="text-2xl">
              {(rollup.churn_risk.high ?? 0) + (rollup.churn_risk.medium ?? 0)}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(rollup.churn_risk).map(([key, count]) => (
              <CountBar
                key={key}
                label={key}
                count={count}
                total={analyzed}
                tone={
                  key === "high" ? "destructive" : key === "medium" ? "warning" : "success"
                }
              />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>NPS class</CardDescription>
            <CardTitle className="text-2xl">{rollup.nps_class.promoter ?? 0} promoters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(rollup.nps_class).map(([key, count]) => (
              <CountBar key={key} label={key} count={count} total={analyzed} />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Emotion</CardDescription>
            <CardTitle className="text-2xl capitalize">
              {Object.entries(rollup.emotion).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(rollup.emotion).map(([key, count]) => (
              <CountBar key={key} label={key} count={count} total={analyzed} />
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <ThemeList title="Top themes" items={rollup.top_themes} />
        <ThemeList title="Top issues" items={rollup.top_issues} />
        <ThemeList title="Top delights" items={rollup.top_delights} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {rollup.mixed_sentiment_count > 0 ? (
          <Card className="border-warning/40">
            <CardHeader>
              <CardDescription>Mixed sentiment</CardDescription>
              <CardTitle className="text-2xl">{rollup.mixed_sentiment_count}</CardTitle>
              <CardDescription>
                Praise and complaints in the same comment — a single star rating would miss this.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {rollup.mixed_sentiment_samples.map((sample) => (
                <div
                  key={sample.verbatim_id}
                  className="rounded-lg border border-warning/30 bg-warning/5 p-3"
                >
                  <div className="mb-2 flex flex-wrap gap-2">
                    <Badge variant="warning">mixed</Badge>
                    {sample.delights.slice(0, 1).map((d) => (
                      <Badge key={d} variant="outline" className="text-success">
                        + {d}
                      </Badge>
                    ))}
                    {sample.issues.slice(0, 2).map((issue) => (
                      <Badge key={issue} variant="outline" className="text-destructive">
                        − {issue}
                      </Badge>
                    ))}
                  </div>
                  <p className="text-sm leading-relaxed">{sample.key_quote ?? sample.text}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        ) : null}

        {rollup.competitor_switch_count > 0 ? (
          <Card className="border-destructive/40">
            <CardHeader>
              <CardDescription>Competitor switch signals</CardDescription>
              <CardTitle className="text-2xl">{rollup.competitor_switch_count}</CardTitle>
              <CardDescription>
                Customers naming Equity, KCB, M-Pesa, Monzo, or actively switching away.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {rollup.competitor_switch_samples.map((sample) => (
                <div
                  key={sample.verbatim_id}
                  className="rounded-lg border border-destructive/30 bg-destructive/5 p-3"
                >
                  <div className="mb-2 flex flex-wrap gap-2">
                    <Badge variant="destructive">competitor risk</Badge>
                    <Badge
                      variant={
                        sample.churn_risk === "high"
                          ? "destructive"
                          : sample.churn_risk === "medium"
                            ? "warning"
                            : "outline"
                      }
                    >
                      churn: {sample.churn_risk}
                    </Badge>
                  </div>
                  <p className="text-sm leading-relaxed">{sample.key_quote ?? sample.text}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        ) : null}
      </div>

      {rollup.high_churn_samples.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">At-risk verbatims</CardTitle>
            <CardDescription>Medium and high churn risk — action these first.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {rollup.high_churn_samples.map((sample) => (
              <div key={sample.verbatim_id} className="rounded-lg border border-border bg-muted/20 p-3">
                <div className="mb-2 flex flex-wrap gap-2">
                  <Badge
                    variant={
                      sample.churn_risk === "high"
                        ? "destructive"
                        : sample.churn_risk === "medium"
                          ? "warning"
                          : "outline"
                    }
                  >
                    churn: {sample.churn_risk}
                  </Badge>
                  {sample.themes.slice(0, 3).map((theme) => (
                    <Badge key={theme} variant="outline">
                      {theme.replace(/_/g, " ")}
                    </Badge>
                  ))}
                </div>
                <p className="text-sm leading-relaxed">{sample.key_quote ?? sample.text}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
