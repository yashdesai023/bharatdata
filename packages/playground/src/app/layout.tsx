import type { Metadata } from "next";
import { Newsreader, Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Header } from "../components/layout/Header";
import { Footer } from "../components/layout/Footer";

const newsreader = Newsreader({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-serif",
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
});

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "BharatData | Clean Indian Public Data",
  description: "The official gateway to queryable, high-fidelity Indian government datasets. Open data for a modern India.",
  viewport: "width=device-width, initial-scale=1",
};

// Force dynamic is no longer required as a 'fix' but kept for real-time data needs if any.
export const dynamic = "force-dynamic";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${newsreader.variable} ${inter.variable} ${ibmPlexMono.variable}`}>
      <head>
        <link 
          rel="stylesheet" 
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" 
        />
      </head>
      <body className="bg-background text-on-surface antialiased font-sans selection:bg-primary/20 selection:text-primary">
        <div className="flex flex-col min-h-screen">
          <main className="flex-grow">
            <div className="max-w-[1440px] mx-auto">
              {children}
            </div>
          </main>
          <Footer />
        </div>
      </body>
    </html>
  );
}
