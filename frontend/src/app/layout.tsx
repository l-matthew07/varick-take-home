import type { ReactNode } from "react";

import { AuthProvider } from "@/lib/auth";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider value={{ user: null }}>{children}</AuthProvider>
      </body>
    </html>
  );
}
