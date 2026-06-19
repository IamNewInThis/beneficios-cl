import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Nav } from "./componentes/nav";
import { Footer } from "./componentes/footer";

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
        suppressHydrationWarning
        className="flex min-h-screen flex-col bg-black text-white antialiased font-sans selection:bg-cobalt/30"
      >
        <Nav />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
