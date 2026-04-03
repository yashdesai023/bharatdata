import type { Metadata } from "next";
import { Newsreader, Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { ClientLayoutWrapper } from "../components/layout/ClientLayoutWrapper";

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-newsreader",
  display: "swap",
  style: ["normal", "italic"],
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "BharatData Playground | Professional Indian Public Data Search",
  description: "An AI-powered interface for querying, analyzing, and auditing Indian government data with source-cited narratives.",
};

export const dynamic = "force-dynamic";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${newsreader.variable} ${inter.variable} ${ibmPlexMono.variable}`}>
       <head>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
      </head>
      <body className="bg-background text-on-surface font-body antialiased selection:bg-primary/10 selection:text-primary">
        <ClientLayoutWrapper>
          {children}
        </ClientLayoutWrapper>
      </body>
    </html>
  );
}
