"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { createTicket } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/ticketFormat";
import type { TicketCreateResponse, TicketPriority } from "@/types";

const initialForm = {
  title: "",
  description: "",
  channel: "web_form",
  category: "general",
  priority: "P3" as TicketPriority,
};

export default function SubmitPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState<TicketCreateResponse | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, router, user]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const response = await createTicket(form);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  function updateField(name: keyof typeof initialForm, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  if (authLoading) {
    return <main style={{ padding: "32px" }}>Loading...</main>;
  }

  return (
    <main style={{ padding: "32px" }}>
      <h1 style={{ fontSize: "28px", margin: "0 0 20px" }}>Submit Ticket</h1>

      <form
        onSubmit={handleSubmit}
        style={{
          border: "1px solid #d9dde5",
          borderRadius: "8px",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
          maxWidth: "640px",
          padding: "24px",
        }}
      >
        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          Title
          <input
            onChange={(event) => updateField("title", event.target.value)}
            required
            style={{ padding: "10px 12px" }}
            type="text"
            value={form.title}
          />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          Description
          <textarea
            onChange={(event) => updateField("description", event.target.value)}
            required
            rows={5}
            style={{ padding: "10px 12px", resize: "vertical" }}
            value={form.description}
          />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          Channel
          <select
            onChange={(event) => updateField("channel", event.target.value)}
            style={{ padding: "10px 12px" }}
            value={form.channel}
          >
            <option value="web_form">web_form</option>
            <option value="email">email</option>
            <option value="api">api</option>
          </select>
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          Category
          <select
            onChange={(event) => updateField("category", event.target.value)}
            style={{ padding: "10px 12px" }}
            value={form.category}
          >
            <option value="billing">billing</option>
            <option value="engineering">engineering</option>
            <option value="account_management">account_management</option>
            <option value="security">security</option>
            <option value="general">general</option>
          </select>
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          Priority
          <select
            onChange={(event) => updateField("priority", event.target.value)}
            style={{ padding: "10px 12px" }}
            value={form.priority}
          >
            <option value="P1">P1</option>
            <option value="P2">P2</option>
            <option value="P3">P3</option>
            <option value="P4">P4</option>
          </select>
        </label>

        {error ? <p style={{ color: "#b42318", margin: 0 }}>{error}</p> : null}

        <button
          disabled={submitting}
          style={{
            cursor: submitting ? "not-allowed" : "pointer",
            padding: "11px 12px",
          }}
          type="submit"
        >
          {submitting ? "Submitting..." : "Submit"}
        </button>
      </form>

      {result ? (
        <section
          style={{
            border: "1px solid #d9dde5",
            borderRadius: "8px",
            marginTop: "20px",
            maxWidth: "640px",
            padding: "18px",
          }}
        >
          <p style={{ margin: "0 0 12px" }}>
            Routed to: {result.routed_to}, Priority: {result.final_priority}, SLA Deadline:{" "}
            {formatDate(result.sla_deadline)}, Rule matched: {result.rule_matched}
          </p>
          <Link
            href={`/tickets/${result.ticket.id}`}
            style={{
              color: "#1d4ed8",
              display: "inline-block",
              fontWeight: 600,
              marginBottom: "12px",
            }}
          >
            View created ticket
          </Link>
          <br />
          <button
            onClick={() => {
              setForm(initialForm);
              setResult(null);
              setError("");
            }}
            style={{ padding: "9px 12px" }}
            type="button"
          >
            Submit another
          </button>
        </section>
      ) : null}
    </main>
  );
}
