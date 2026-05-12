import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Nav } from "@/components/Nav";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Support Tickets",
  description: "Support ticket triage and SLA tracking",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0 }}>
        <AuthProvider>
          <Nav />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
