"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth";

export function Nav() {
  const { user } = useAuth();

  return (
    <nav>
      <Link href="/dashboard">Dashboard</Link>
      <Link href="/submit">Submit</Link>
      {user?.role === "lead" ? <Link href="/metrics">Metrics</Link> : null}
    </nav>
  );
}
