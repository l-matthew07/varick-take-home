"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const { user, login, loading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      router.replace("/dashboard");
    }
  }, [loading, router, user]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main
      style={{
        alignItems: "center",
        display: "flex",
        justifyContent: "center",
        minHeight: "calc(100vh - 58px)",
        padding: "24px",
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          border: "1px solid #d9dde5",
          borderRadius: "8px",
          boxShadow: "0 12px 30px rgba(15, 23, 42, 0.08)",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
          maxWidth: "360px",
          padding: "28px",
          width: "100%",
        }}
      >
        <h1 style={{ fontSize: "24px", margin: 0 }}>Sign in</h1>
        <input
          autoComplete="email"
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Email"
          required
          style={{
            border: "1px solid #c9ced8",
            borderRadius: "6px",
            fontSize: "16px",
            padding: "10px 12px",
          }}
          type="email"
          value={email}
        />
        <input
          autoComplete="current-password"
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
          required
          style={{
            border: "1px solid #c9ced8",
            borderRadius: "6px",
            fontSize: "16px",
            padding: "10px 12px",
          }}
          type="password"
          value={password}
        />
        {error ? (
          <p style={{ color: "#b42318", fontSize: "14px", margin: 0 }}>{error}</p>
        ) : null}
        <button
          disabled={submitting}
          style={{
            background: submitting ? "#64748b" : "#1f2937",
            border: 0,
            borderRadius: "6px",
            color: "#ffffff",
            cursor: submitting ? "not-allowed" : "pointer",
            fontSize: "16px",
            fontWeight: 600,
            padding: "11px 12px",
          }}
          type="submit"
        >
          {submitting ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </main>
  );
}
