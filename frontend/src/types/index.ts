export type UserRole = "agent" | "lead";
export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";
export type TicketPriority = "P1" | "P2" | "P3" | "P4";
export type SLAStatus = "on_track" | "at_risk" | "breached";

export interface TicketHistory {
  id: string;
  action: string;
  old_value: string | null;
  new_value: string | null;
  changed_by: string;
  timestamp: string;
}

export interface Ticket {
  id: string;
  title: string;
  description: string;
  channel: string;
  status: TicketStatus;
  priority: TicketPriority;
  category: string;
  assigned_team: string | null;
  assigned_agent: string | null;
  sla_deadline: string | null;
  sla_status: SLAStatus;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  history?: TicketHistory[];
}

export interface SLABreachTicket extends Ticket {
  sla_elapsed_seconds: number;
}

export interface User {
  id: string;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface Metrics {
  tickets_by_status: Record<TicketStatus, number>;
  tickets_by_priority: Record<TicketPriority, number>;
  tickets_by_team: Record<string, number>;
  sla_breaches: number;
  avg_resolution_seconds: number | null;
}

export interface TicketCreateResponse {
  ticket: Ticket;
  routed_to: string;
  final_priority: TicketPriority;
  sla_deadline: string | null;
  rule_matched: string;
}

export interface PaginatedTickets {
  items: Ticket[];
  total: number;
  limit: number;
  offset: number;
}
