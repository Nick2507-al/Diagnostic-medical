import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const pjs = localFont({ src: "./pjs.woff2", variable: "--font-pjs", weight: "200 800", display: "swap" });

export const metadata: Metadata = {
  title: { default: "MediAI", template: "%s · MediAI" },
  description: "Aide à la décision clinique pour les médecins exerçant en Afrique",
  robots: { index: false, follow: false }, // private medical application
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={pjs.variable}>
      <body>{children}</body>
    </html>
  );
}
