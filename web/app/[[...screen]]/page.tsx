import Script from "next/script";
import { notFound } from "next/navigation";

const screens = new Set(["demo", "privacy", "check-in", "insights", "goals-habits", "coach", "settings"]);

export default async function Page({ params }: { params: Promise<{ screen?: string[] }> }) {
  const path = (await params).screen ?? [];
  if (path.length > 1 || (path.length === 1 && !screens.has(path[0] ?? ""))) notFound();
  return (
    <>
      <div id="steadyday"><p className="boot" role="status">Opening SteadyDay…</p></div>
      <noscript>Enable JavaScript to use the SteadyDay demo.</noscript>
      <Script src="/steadyday/app.js?v=4" type="module" strategy="afterInteractive" />
    </>
  );
}
