import type { Ticket, TicketPriority } from "@/types";

const priorityColors: Record<TicketPriority, string> = {
  P1: "#b42318",
  P2: "#f97316",
  P3: "#854d0e",
  P4: "#374151",
};

const slaColors: Record<Ticket["sla_status"], string> = {
  on_track: "#16a34a",
  at_risk: "#ca8a04",
  breached: "#dc2626",
};

export function formatDate(
  value: string | null,
  options: Intl.DateTimeFormatOptions = { dateStyle: "medium", timeStyle: "short" },
): string {
  if (!value) {
    return "None";
  }

  return new Intl.DateTimeFormat("en-US", options).format(new Date(value));
}

export function priorityBadge(priority: TicketPriority) {
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

export function slaIndicator(status: Ticket["sla_status"]) {
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
