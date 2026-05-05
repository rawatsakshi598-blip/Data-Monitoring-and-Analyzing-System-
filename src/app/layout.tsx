import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DataGuard - Unified Data Intelligence Platform",
  description:
    "OpenMetadata-inspired unified metadata platform for data discovery, quality monitoring, lineage tracking, and governance.",
  keywords: [
    "data quality",
    "data governance",
    "data lineage",
    "metadata management",
    "data discovery",
    "DataGuard",
    "OpenMetadata",
  ],
  authors: [{ name: "DataGuard Team" }],
  icons: {
    icon: "https://z-cdn.chatglm.cn/z-ai/static/logo.svg",
  },
  openGraph: {
    title: "DataGuard - Unified Data Intelligence Platform",
    description:
      "OpenMetadata-inspired unified metadata platform for data discovery, quality monitoring, lineage tracking, and governance.",
    siteName: "DataGuard",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "DataGuard - Unified Data Intelligence Platform",
    description:
      "OpenMetadata-inspired unified metadata platform for data discovery, quality monitoring, lineage tracking, and governance.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
