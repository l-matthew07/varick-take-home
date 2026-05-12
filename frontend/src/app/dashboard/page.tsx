"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getTickets } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, priorityBadge, slaIndicator } from "@/lib/ticketFormat";
import type { Ticket, TicketPriority, TicketStatus } from "@/types";

type StatusFilter = "all" | TicketStatus;
type PriorityFilter = "all" | TicketPriority;

const PAGE_SIZE = 20;
const SUPPORT_TEAMS = ["Account Management", "Billing", "Engineering", "Security"];

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [status, setStatus] = useState<StatusFilter>("all");
  const [priority, setPriority] = useState<PriorityFilter>("all");
  const [team, setTeam] = useState("all");
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
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
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    })
      .then((response) => {
        if (active) {
          setTickets(response.items);
          setTotal(response.total);
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
  }, [page, priority, status, team, user]);

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
            onChange={(event) => { setStatus(event.target.value as StatusFilter); setPage(0); }}
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
            onChange={(event) => { setPriority(event.target.value as PriorityFilter); setPage(0); }}
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
            onChange={(event) => { setTeam(event.target.value); setPage(0); }}
            style={{ padding: "8px 10px", minWidth: "180px" }}
            value={team}
          >
            <option value="all">all</option>
            {SUPPORT_TEAMS.map((teamName) => (
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
                    {formatDate(ticket.created_at, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
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

      {total > PAGE_SIZE && (
        <div style={{ alignItems: "center", display: "flex", gap: "12px", marginTop: "16px" }}>
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            style={{ padding: "6px 12px" }}
            type="button"
          >
            Previous
          </button>
          <span style={{ fontSize: "14px" }}>
            {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
          </span>
          <button
            disabled={(page + 1) * PAGE_SIZE >= total}
            onClick={() => setPage((p) => p + 1)}
            style={{ padding: "6px 12px" }}
            type="button"
          >
            Next
          </button>
        </div>
      )}
    </main>
  );
}
