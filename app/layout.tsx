import "./globals.css";
import { Navigation } from "@/components/navigation";
import { Footer } from "@/components/footer";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "Reykjavik 2026 - Chess Tournament Statistics",
  description: "Game statistics and analysis for the Reykjavik 2026 chess tournament.",
  keywords: [
    "reykjavik",
    "chess",
    "tournament",
    "statistics",
    "2026",
    "chess analytics",
    "game analysis"
  ],
  authors: [{ name: "pom-pom.ch" }],
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/favicon.svg', type: 'image/svg+xml' },
    ],
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    siteName: 'Reykjavik 2026 Stats',
    title: 'Reykjavik 2026 - Chess Tournament Statistics',
    description: 'Game statistics and analysis for the Reykjavik 2026 chess tournament.',
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full font-syne antialiased bg-background text-foreground">
        <div className="min-h-full flex flex-col">
          <Navigation />
          <main className="flex-grow pb-10">
            {children}
          </main>
          <Footer />
        </div>
      </body>
    </html>
  );
}
