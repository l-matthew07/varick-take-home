"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/lib/auth";

export default function HomePage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (loading) {
      return;
    }

    router.replace(user ? "/dashboard" : "/login");
  }, [loading, router, user]);

  return null;
}
