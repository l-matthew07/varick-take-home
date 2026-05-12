"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { getTicket, updateTicket } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, priorityBadge, slaIndicator } from "@/lib/ticketFormat";
import type { Ticket, TicketStatus } from "@/types";

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <span style={{ color: "#6b7280", fontSize: "13px" }}>{label}</span>
      <span style={{ fontSize: "15px" }}>{value}</span>
    </div>
  );
}

export default function TicketDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState("");

  const ticketId = params.id;

  const fetchTicket = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await getTicket(ticketId);
      setTicket(response);
    } catch (err) {
      if (err instanceof Error && err.message !== "Unauthorized") {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, router, user]);

  useEffect(() => {
    if (user) {
      void fetchTicket();
    }
  }, [fetchTicket, user]);

  async function runAction(data: { status?: TicketStatus; assigned_agent?: string | null }) {
    setUpdating(true);
    setError("");

    try {
      await updateTicket(ticketId, data);
      await fetchTicket();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setUpdating(false);
    }
  }

  function actionButtons(currentTicket: Ticket) {
    const buttonStyle = {
      border: "1px solid #c9ced8",
      borderRadius: "6px",
      cursor: updating ? "not-allowed" : "pointer",
      padding: "9px 12px",
    };

    if (currentTicket.status === "open") {
      return (
        <>
          <button
            disabled={updating}
            onClick={() => runAction({ status: "in_progress" })}
            style={buttonStyle}
            type="button"
          >
            Start Working
          </button>
          <button
            disabled={updating}
            onClick={() => runAction({ assigned_agent: user?.email ?? null })}
            style={buttonStyle}
            type="button"
          >
            Assign to Me
          </button>
        </>
      );
    }

    if (currentTicket.status === "in_progress") {
      return (
        <button
          disabled={updating}
          onClick={() => runAction({ status: "resolved" })}
          style={buttonStyle}
          type="button"
        >
          Resolve
        </button>
      );
    }

    if (currentTicket.status === "resolved") {
      return (
        <>
          <button
            disabled={updating}
            onClick={() => runAction({ status: "closed" })}
            style={buttonStyle}
            type="button"
          >
            Close
          </button>
          <button
            disabled={updating}
            onClick={() => runAction({ status: "in_progress" })}
            style={buttonStyle}
            type="button"
          >
            Reopen
          </button>
        </>
      );
    }

    return null;
  }

  if (authLoading || loading) {
    return <main style={{ padding: "32px" }}>Loading...</main>;
  }

  if (!ticket) {
    return (
      <main style={{ padding: "32px" }}>
        <Link href="/dashboard">Back to dashboard</Link>
        <p>{error || "Ticket not found"}</p>
      </main>
    );
  }

  return (
    <main style={{ padding: "32px" }}>
      <Link href="/dashboard">Back to dashboard</Link>

      <section
        style={{
          border: "1px solid #d9dde5",
          borderRadius: "8px",
          marginTop: "18px",
          padding: "24px",
        }}
      >
        <div style={{ display: "flex", gap: "12px", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ fontSize: "28px", margin: "0 0 10px" }}>{ticket.title}</h1>
            <p style={{ color: "#374151", margin: 0 }}>{ticket.description}</p>
          </div>
          <div style={{ alignItems: "flex-end", display: "flex", flexDirection: "column", gap: "8px" }}>
            {priorityBadge(ticket.priority)}
            {slaIndicator(ticket.sla_status)}
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gap: "18px",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            marginTop: "24px",
          }}
        >
          <DetailRow label="Status" value={ticket.status} />
          <DetailRow label="Priority" value={priorityBadge(ticket.priority)} />
          <DetailRow label="Category" value={ticket.category} />
          <DetailRow label="Channel" value={ticket.channel} />
          <DetailRow label="Team" value={ticket.assigned_team ?? "Unassigned"} />
          <DetailRow label="Agent" value={ticket.assigned_agent ?? "Unassigned"} />
          <DetailRow label="SLA Deadline" value={formatDate(ticket.sla_deadline)} />
          <DetailRow label="SLA Status" value={slaIndicator(ticket.sla_status)} />
          <DetailRow label="Created" value={formatDate(ticket.created_at)} />
          <DetailRow label="Resolved" value={formatDate(ticket.resolved_at)} />
        </div>

        {ticket.status !== "closed" ? (
          <div style={{ display: "flex", gap: "10px", marginTop: "24px" }}>
            {actionButtons(ticket)}
          </div>
        ) : null}

        {error ? (
          <p style={{ color: "#b42318", margin: "16px 0 0" }}>{error}</p>
        ) : null}
      </section>

      <section style={{ marginTop: "28px" }}>
        <h2 style={{ fontSize: "20px", margin: "0 0 14px" }}>History</h2>
        {ticket.history && ticket.history.length > 0 ? (
          <ol style={{ display: "flex", flexDirection: "column", gap: "12px", paddingLeft: "20px" }}>
            {ticket.history.map((entry) => (
              <li key={entry.id}>
                <div style={{ fontWeight: 600 }}>{entry.action}</div>
                <div style={{ color: "#4b5563", fontSize: "14px" }}>
                  {entry.changed_by} · {formatDate(entry.timestamp)}
                </div>
                {entry.old_value && entry.new_value ? (
                  <div style={{ color: "#4b5563", fontSize: "14px", marginTop: "2px" }}>
                    {entry.old_value} → {entry.new_value}
                  </div>
                ) : null}
              </li>
            ))}
          </ol>
        ) : (
          <p>No history entries</p>
        )}
      </section>
    </main>
  );
}
