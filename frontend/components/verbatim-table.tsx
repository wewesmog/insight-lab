"use client"

import * as React from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { VerbatimAnalysis } from "@/lib/types"

function sentimentVariant(sentiment?: string | null) {
  if (sentiment === "positive") return "success" as const
  if (sentiment === "negative") return "destructive" as const
  if (sentiment === "mixed") return "warning" as const
  return "outline" as const
}

function churnVariant(risk?: string | null) {
  if (risk === "high") return "destructive" as const
  if (risk === "medium") return "warning" as const
  return "outline" as const
}

function RecordDetail({ record }: { record: VerbatimAnalysis }) {
  if (record.skipped) {
    return (
      <p className="text-sm text-muted-foreground">
        Skipped ({record.skip_reason?.replace(/_/g, " ") ?? "low signal"})
      </p>
    )
  }

  return (
    <div className="grid gap-3 text-sm md:grid-cols-2">
      <div>
        <p className="mb-1 text-xs font-medium text-muted-foreground">Summary</p>
        <p>{record.summary ?? "—"}</p>
      </div>
      <div>
        <p className="mb-1 text-xs font-medium text-muted-foreground">Key quote</p>
        <p className="italic">&ldquo;{record.key_quote ?? record.text}&rdquo;</p>
      </div>
      {record.issues.length > 0 ? (
        <div>
          <p className="mb-1 text-xs font-medium text-muted-foreground">Issues</p>
          <ul className="list-inside list-disc space-y-0.5">
            {record.issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {record.delights.length > 0 ? (
        <div>
          <p className="mb-1 text-xs font-medium text-muted-foreground">Delights</p>
          <ul className="list-inside list-disc space-y-0.5">
            {record.delights.map((delight) => (
              <li key={delight}>{delight}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="md:col-span-2">
        <p className="mb-1 text-xs font-medium text-muted-foreground">Themes</p>
        <div className="flex flex-wrap gap-1">
          {record.themes.map((theme) => (
            <Badge key={theme} variant="outline">
              {theme.replace(/_/g, " ")}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  )
}

export function VerbatimTable({ records }: { records: VerbatimAnalysis[] }) {
  const [openId, setOpenId] = useState<string | null>(null)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Per-verbatim insights</CardTitle>
        <CardDescription>
          Each row is one LangGraph <code className="text-xs">analyze_one</code> output — not a raw
          sentiment score.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8" />
              <TableHead>Verbatim</TableHead>
              <TableHead>Sentiment</TableHead>
              <TableHead>Churn</TableHead>
              <TableHead>NPS</TableHead>
              <TableHead>Themes</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {records.map((record) => {
              const open = openId === record.verbatim_id
              return (
                <React.Fragment key={record.verbatim_id}>
                  <TableRow
                    className="cursor-pointer"
                    onClick={() =>
                      setOpenId(open ? null : record.verbatim_id)
                    }
                  >
                    <TableCell>
                      {open ? (
                        <ChevronDown className="size-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="size-4 text-muted-foreground" />
                      )}
                    </TableCell>
                    <TableCell className="max-w-md">
                      <p className="line-clamp-2 text-sm">{record.text}</p>
                      {record.star_rating != null ? (
                        <p className="mt-1 text-xs text-muted-foreground">
                          ★ {record.star_rating}
                        </p>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      {record.skipped ? (
                        <Badge variant="outline">skipped</Badge>
                      ) : (
                        <Badge variant={sentimentVariant(record.sentiment)}>
                          {record.sentiment}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {!record.skipped ? (
                        <Badge variant={churnVariant(record.churn_risk)}>
                          {record.churn_risk}
                        </Badge>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="capitalize">{record.nps_class ?? "—"}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {record.themes.slice(0, 2).map((theme) => (
                          <Badge key={theme} variant="outline" className="text-[10px]">
                            {theme.replace(/_/g, " ")}
                          </Badge>
                        ))}
                        {record.themes.length > 2 ? (
                          <span className="text-xs text-muted-foreground">
                            +{record.themes.length - 2}
                          </span>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                  {open ? (
                    <TableRow key={`${record.verbatim_id}-detail`}>
                      <TableCell colSpan={6} className="bg-muted/20">
                        <RecordDetail record={record} />
                      </TableCell>
                    </TableRow>
                  ) : null}
                </React.Fragment>
              )
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
