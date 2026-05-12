import type {
  Metrics,
  PaginatedTickets,
  Ticket,
  TicketCreateResponse,
  TicketPriority,
  TicketStatus,
  User,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
const TOKEN_KEY = "token";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: "agent" | "lead";
}

export interface TicketFilters {
  status?: TicketStatus;
  priority?: TicketPriority;
  category?: string;
  assigned_team?: string;
  limit?: number;
  offset?: number;
}

export interface TicketCreateInput {
  title: string;
  description: string;
  channel: string;
  category: string;
  priority: TicketPriority;
}

export interface TicketUpdateInput {
  status?: TicketStatus;
  assigned_agent?: string | null;
  assigned_team?: string | null;
}

export function getToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(TOKEN_KEY);
}

function redirectToLogin(): void {
  if (typeof window !== "undefined") {
    window.location.assign("/login");
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function authFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearToken();
    redirectToLogin();
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    let message = `API request failed with ${response.status}`;
    try {
      const errorBody = await response.json();
      if (typeof errorBody?.detail === "string") {
        message = errorBody.detail;
      }
    } catch {
      // Keep the generic status message when the response is not JSON.
    }
    throw new Error(message);
  }

  return parseResponse<T>(response);
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  return authFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe(): Promise<User> {
  return authFetch<User>("/auth/me");
}

export async function getTickets(filters: TicketFilters = {}): Promise<PaginatedTickets> {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });

  const query = params.toString();
  return authFetch<PaginatedTickets>(`/tickets${query ? `?${query}` : ""}`);
}

export async function getTicket(id: string): Promise<Ticket> {
  return authFetch<Ticket>(`/tickets/${id}`);
}

export async function createTicket(data: TicketCreateInput): Promise<TicketCreateResponse> {
  return authFetch<TicketCreateResponse>("/tickets", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateTicket(id: string, data: TicketUpdateInput): Promise<Ticket> {
  return authFetch<Ticket>(`/tickets/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function getMetrics(): Promise<Metrics> {
  return authFetch<Metrics>("/metrics");
}

export async function getSLABreaches(): Promise<Ticket[]> {
  return authFetch<Ticket[]>("/tickets/sla-breaches");
}
