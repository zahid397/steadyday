import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "SteadyDay | Wellbeing demo",
  description: "Track fictional routines and find a small next step in this wellbeing prototype.",
  icons: { icon: "/steadyday/mark.svg" },
  robots: { index: false, follow: false },
};

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head><link rel="stylesheet" href="/steadyday/styles.css?v=4" /></head>
      <body>{children}</body>
    </html>
  );
}
