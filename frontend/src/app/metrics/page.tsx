"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { getMetrics, getSLABreaches } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Metrics, SLABreachTicket, TicketPriority } from "@/types";

function formatDuration(seconds: number | null): string {
  if (seconds === null) {
    return "None";
  }

  const totalMinutes = Math.max(0, Math.round(seconds / 60));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }

  return `${minutes}m`;
}

function SummaryCard({
  label,
  value,
  danger,
}: {
  label: string;
  value: string | number;
  danger?: boolean;
}) {
  return (
    <div
      style={{
        border: "1px solid #d9dde5",
        borderRadius: "8px",
        flex: "1 1 180px",
        padding: "18px",
      }}
    >
      <div style={{ color: "#6b7280", fontSize: "13px", marginBottom: "8px" }}>{label}</div>
      <div style={{ color: danger ? "#dc2626" : "#111827", fontSize: "26px", fontWeight: 700 }}>
        {value}
      </div>
    </div>
  );
}

export default function MetricsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [breaches, setBreaches] = useState<SLABreachTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (authLoading) {
      return;
    }
    if (!user) {
      router.replace("/login");
      return;
    }
    if (user.role !== "lead") {
      router.replace("/dashboard");
    }
  }, [authLoading, router, user]);

  useEffect(() => {
    if (!user || user.role !== "lead") {
      return;
    }

    let active = true;
    setLoading(true);
    setError("");

    Promise.all([getMetrics(), getSLABreaches()])
      .then(([metricsResponse, breachResponse]) => {
        if (active) {
          setMetrics(metricsResponse);
          setBreaches(breachResponse);
        }
      })
      .catch((err) => {
        if (active && err instanceof Error && err.message !== "Unauthorized") {
          setError(err.message);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [user]);

  const teamsByCount = useMemo(
    () =>
      Object.entries(metrics?.tickets_by_team ?? {}).sort((a, b) => b[1] - a[1]),
    [metrics],
  );

  if (authLoading || loading) {
    return <main style={{ padding: "32px" }}>Loading...</main>;
  }

  if (!metrics) {
    return <main style={{ padding: "32px" }}>{error || "Metrics unavailable"}</main>;
  }

  return (
    <main style={{ padding: "32px" }}>
      <h1 style={{ fontSize: "28px", margin: "0 0 20px" }}>Metrics</h1>
      {error ? <p style={{ color: "#b42318" }}>{error}</p> : null}

      <section style={{ display: "flex", flexWrap: "wrap", gap: "14px", marginBottom: "28px" }}>
        <SummaryCard label="Total Open" value={metrics.tickets_by_status.open} />
        <SummaryCard label="Total In Progress" value={metrics.tickets_by_status.in_progress} />
        <SummaryCard
          danger={metrics.sla_breaches > 0}
          label="SLA Breaches"
          value={metrics.sla_breaches}
        />
        <SummaryCard
          label="Avg Resolution Time"
          value={formatDuration(metrics.avg_resolution_seconds)}
        />
      </section>

      <section style={{ display: "grid", gap: "24px", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
        <div>
          <h2 style={{ fontSize: "20px" }}>Tickets by Team</h2>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={{ borderBottom: "1px solid #d9dde5", padding: "10px", textAlign: "left" }}>
                  Team
                </th>
                <th style={{ borderBottom: "1px solid #d9dde5", padding: "10px", textAlign: "left" }}>
                  Count
                </th>
              </tr>
            </thead>
            <tbody>
              {teamsByCount.map(([team, count]) => (
                <tr key={team}>
                  <td style={{ borderBottom: "1px solid #eef0f4", padding: "10px" }}>{team}</td>
                  <td style={{ borderBottom: "1px solid #eef0f4", padding: "10px" }}>{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div>
          <h2 style={{ fontSize: "20px" }}>Tickets by Priority</h2>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={{ borderBottom: "1px solid #d9dde5", padding: "10px", textAlign: "left" }}>
                  Priority
                </th>
                <th style={{ borderBottom: "1px solid #d9dde5", padding: "10px", textAlign: "left" }}>
                  Count
                </th>
              </tr>
            </thead>
            <tbody>
              {(["P1", "P2", "P3", "P4"] as TicketPriority[]).map((priority) => (
                <tr key={priority}>
                  <td style={{ borderBottom: "1px solid #eef0f4", padding: "10px" }}>
                    {priority}
                  </td>
                  <td style={{ borderBottom: "1px solid #eef0f4", padding: "10px" }}>
                    {metrics.tickets_by_priority[priority]}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section style={{ marginTop: "28px" }}>
        <h2 style={{ fontSize: "20px" }}>Breaching Tickets</h2>
        {breaches.length === 0 ? (
          <p>No breaching tickets</p>
        ) : (
          <ul style={{ display: "flex", flexDirection: "column", gap: "10px", paddingLeft: "20px" }}>
            {breaches.map((ticket) => (
              <li key={ticket.id}>
                <strong>{ticket.title}</strong> · {ticket.assigned_team ?? "Unassigned"} ·{" "}
                {formatDuration(ticket.sla_elapsed_seconds)}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
