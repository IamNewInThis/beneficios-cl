import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Beneficios CL",
  description: "Centraliza los beneficios de tus tarjetas en Chile.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className={inter.variable}>
      <body
        // Extensiones del navegador (ej. ColorZilla añade `cz-shortcut-listen`)
        // mutan el <body> antes de la hidratación; esto evita el falso warning.
        suppressHydrationWarning
        className="min-h-screen bg-black text-white antialiased font-sans selection:bg-cobalt/30"
      >
        {children}
      </body>
    </html>
  );
}
