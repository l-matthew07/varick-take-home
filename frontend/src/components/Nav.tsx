"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";

export function Nav() {
  const router = useRouter();
  const { user, logout } = useAuth();

  if (!user) {
    return null;
  }

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <nav
      style={{
        alignItems: "center",
        borderBottom: "1px solid #d9dde5",
        display: "flex",
        gap: "24px",
        padding: "14px 24px",
      }}
    >
      <Link href="/dashboard" style={{ fontWeight: 700, marginRight: "12px" }}>
        Support Tickets
      </Link>
      <Link href="/dashboard">Dashboard</Link>
      <Link href="/submit">Submit Ticket</Link>
      {user.role === "lead" ? <Link href="/metrics">Metrics</Link> : null}
      <button
        onClick={handleLogout}
        style={{
          marginLeft: "auto",
          padding: "8px 12px",
        }}
        type="button"
      >
        Logout
      </button>
    </nav>
  );
}
