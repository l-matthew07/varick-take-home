"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { getTickets } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Ticket, TicketPriority, TicketStatus } from "@/types";

type StatusFilter = "all" | TicketStatus;
type PriorityFilter = "all" | TicketPriority;

const priorityColors: Record<TicketPriority, string> = {
  P1: "#b42318",
  P2: "#c4320a",
  P3: "#854d0e",
  P4: "#374151",
};

const slaColors: Record<Ticket["sla_status"], string> = {
  on_track: "#16a34a",
  at_risk: "#ea580c",
  breached: "#dc2626",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function priorityBadge(priority: TicketPriority) {
  return (
    <span
      style={{
        background: priorityColors[priority],
        borderRadius: "9999px",
        color: "#ffffff",
        display: "inline-block",
        fontSize: "12px",
        fontWeight: 600,
        padding: "2px 8px",
      }}
    >
      {priority}
    </span>
  );
}

function slaIndicator(status: Ticket["sla_status"]) {
  return (
    <span style={{ alignItems: "center", display: "inline-flex", gap: "8px" }}>
      <span
        style={{
          background: slaColors[status],
          borderRadius: "9999px",
          display: "inline-block",
          height: "12px",
          width: "12px",
        }}
      />
      {status.replace("_", " ")}
    </span>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [status, setStatus] = useState<StatusFilter>("all");
  const [priority, setPriority] = useState<PriorityFilter>("all");
  const [team, setTeam] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, router, user]);

  useEffect(() => {
    if (!user) {
      return;
    }

    let active = true;
    setLoading(true);

    getTickets({
      status: status === "all" ? undefined : status,
      priority: priority === "all" ? undefined : priority,
      assigned_team: team === "all" ? undefined : team,
    })
      .then((response) => {
        if (active) {
          setTickets(response.items);
        }
      })
      .catch((error) => {
        if (error instanceof Error && error.message !== "Unauthorized") {
          console.error(error);
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
  }, [priority, status, team, user]);

  const teams = useMemo(
    () =>
      Array.from(
        new Set(tickets.map((ticket) => ticket.assigned_team).filter(Boolean) as string[]),
      ).sort(),
    [tickets],
  );

  if (authLoading || (!user && loading)) {
    return <main style={{ padding: "32px" }}>Loading...</main>;
  }

  return (
    <main style={{ padding: "32px" }}>
      <h1 style={{ fontSize: "28px", margin: "0 0 20px" }}>Dashboard</h1>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "12px",
          marginBottom: "18px",
        }}
      >
        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          Status
          <select
            onChange={(event) => setStatus(event.target.value as StatusFilter)}
            style={{ padding: "8px 10px" }}
            value={status}
          >
            <option value="all">all</option>
            <option value="open">open</option>
            <option value="in_progress">in_progress</option>
            <option value="resolved">resolved</option>
            <option value="closed">closed</option>
          </select>
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          Priority
          <select
            onChange={(event) => setPriority(event.target.value as PriorityFilter)}
            style={{ padding: "8px 10px" }}
            value={priority}
          >
            <option value="all">all</option>
            <option value="P1">P1</option>
            <option value="P2">P2</option>
            <option value="P3">P3</option>
            <option value="P4">P4</option>
          </select>
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          Team
          <select
            onChange={(event) => setTeam(event.target.value)}
            style={{ padding: "8px 10px", minWidth: "180px" }}
            value={team}
          >
            <option value="all">all</option>
            {teams.map((teamName) => (
              <option key={teamName} value={teamName}>
                {teamName}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading ? (
        <p>Loading...</p>
      ) : tickets.length === 0 ? (
        <p>No tickets found</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              borderCollapse: "collapse",
              minWidth: "900px",
              width: "100%",
            }}
          >
            <thead>
              <tr>
                {["Title", "Priority", "Category", "Team", "Status", "Created", "SLA Status"].map(
                  (heading) => (
                    <th
                      key={heading}
                      style={{
                        borderBottom: "1px solid #d9dde5",
                        color: "#4b5563",
                        fontSize: "13px",
                        padding: "10px 12px",
                        textAlign: "left",
                      }}
                    >
                      {heading}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {tickets.map((ticket) => (
                <tr
                  key={ticket.id}
                  onClick={() => router.push(`/tickets/${ticket.id}`)}
                  style={{ cursor: "pointer" }}
                >
                  <td style={{ borderBottom: "1px solid #eef0f4", padding: "12px" }}>
                    {ticket.title}
                  </td>
                  <td style={{ borderBottom: "1px solid #eef0f4", padding: "12px" }}>
                    {priorityBadge(ticket.priority)}
                  </td>
                  <td style={{ borderBottom: "1px solid #eef0f4", padding: "12px" }}>
                    {ticket.category}
                  </td>
                  <td style={{ borderBottom: "1px solid #eef0f4", padding: "12px" }}>
                    {ticket.assigned_team ?? "Unassigned"}
                  </td>
                  <td style={{ borderBottom: "1px solid #eef0f4", padding: "12px" }}>
                    {ticket.status}
                  </td>
                  <td style={{ borderBottom: "1px solid #eef0f4", padding: "12px" }}>
                    {formatDate(ticket.created_at)}
                  </td>
                  <td style={{ borderBottom: "1px solid #eef0f4", padding: "12px" }}>
                    {slaIndicator(ticket.sla_status)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
