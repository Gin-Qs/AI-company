import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";

import "./globals.css";

export const metadata: Metadata = {
  title: "Portal de mando",
  description: "La bandeja unica de HITL de la oficina virtual.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      {/* ClerkProvider va DENTRO de <body>, no envolviendo <html>. */}
      <body>
        <ClerkProvider>{children}</ClerkProvider>
      </body>
    </html>
  );
}
