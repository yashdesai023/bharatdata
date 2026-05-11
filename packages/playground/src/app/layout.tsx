import type { Metadata } from "next";
import { Newsreader, Poppins, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const newsreader = Newsreader({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-serif",
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
});

const poppins = Poppins({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
  weight: ["400", "500", "600", "700"],
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
  weight: ["400", "500", "600", "700"],
});

// Define custom font classes
const serifFont = "font-serif";
const sansFont = "font-sans";

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
    <html lang="en" className={`${newsreader.variable} ${poppins.variable} ${ibmPlexMono.variable}`}>
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL@20..48,100..700,0..1,-50..200"
        />
        <style dangerouslySetInnerHTML={{__html: `
          .font-serif { font-family: var(--font-serif), Newsreader, Georgia, serif; }
          .font-sans { font-family: var(--font-sans), Poppins, system-ui, sans-serif; }
        `}} />
      </head>
      <body className="bg-[#fff8f5] text-[#231a13] antialiased font-sans selection:bg-[#8f4e00]/20 selection:text-[#8f4e00]">
        {children}
      </body>
    </html>
  );
}
