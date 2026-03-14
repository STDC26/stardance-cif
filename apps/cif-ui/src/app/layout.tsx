import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CIF Console",
  description: "Stardance Creative Intelligence Factory",
};

const navLinks = [
  { href: "/", label: "Dashboard" },
  { href: "/surfaces", label: "Assets" },
  { href: "/deployments", label: "Deployments" },
  { href: "/experiments", label: "Experiments" },
  { href: "/analytics", label: "Analytics" },
  { href: "/drafts", label: "Drafts" },
  { href: "/copilot", label: "Copilot" },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <nav className="border-b border-gray-200 bg-white">
          <div className="max-w-6xl mx-auto px-6 flex items-center h-12 gap-6">
            <Link
              href="/"
              className="text-sm font-bold text-gray-900 tracking-tight mr-4"
            >
              CIF
            </Link>
            {navLinks.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className="text-xs text-gray-500 hover:text-gray-900 transition-colors"
              >
                {label}
              </Link>
            ))}
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
