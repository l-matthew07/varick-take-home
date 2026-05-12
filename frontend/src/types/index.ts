export type UserRole = "agent" | "lead";

export interface User {
  id: number;
  email: string;
  role: UserRole;
}

export interface Ticket {
  id: number;
  title: string;
  description: string;
  channel: string;
  category: string;
  priority: "P1" | "P2" | "P3" | "P4";
  status: "open" | "in_progress" | "resolved" | "closed";
  assignedTeam?: string;
  assignedAgent?: string;
  createdAt: string;
  slaDeadline: string;
  slaStatus: "on_track" | "at_risk" | "breached";
}

export interface Metrics {
  openCount: number;
  inProgressCount: number;
  slaBreachCount: number;
  averageResolutionTime: number | null;
}

export interface RoutingResult {
  team: string;
  finalPriority: Ticket["priority"];
  slaDeadline: string;
  matchedRule: string;
}
