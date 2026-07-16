"use client";

import { useEffect, useState } from "react";
import { api, type ManagerApiAccess } from "@/lib/api";
import { Badge, Button, Card, Spinner } from "@/components/ui";

// A business manager can generate/rotate an API key and see the endpoints they can
// call programmatically (integrate Build Trust into their own tools).
export function ManagerApiPanel({ managerId }: { managerId: string }) {
  const [data, setData] = useState<ManagerApiAccess | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setData(null);
    api.managerApiAccess(managerId).then(setData).catch(() => setData(null));
  }, [managerId]);

  const rotate = async () => {
    setBusy(true);
    try {
      const r = await api.rotateApiKey(managerId);
      setData((d) => (d ? { ...d, api_key: r.api_key } : d));
    } finally {
      setBusy(false);
    }
  };
  const copy = async () => {
    if (!data?.api_key) return;
    try {
      await navigator.clipboard.writeText(data.api_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };

  return (
    <Card className="mb-6 p-4">
      <button onClick={() => setOpen((v) => !v)} className="flex w-full items-center justify-between">
        <span className="flex items-center gap-2 font-semibold text-ink">
          🔑 API access <Badge tone="brand">for integrations</Badge>
        </span>
        <span className="text-ink-faint">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-4">
          {data === null ? (
            <Spinner />
          ) : (
            <>
              <p className="text-sm text-ink-soft">
                Use this key to pull your queue and act on listings from your own dashboards. Send it
                as a bearer token.
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <code className="flex-1 rounded-lg bg-[#1c1c28] px-3 py-2 font-mono text-xs text-[#a5f3c0]">
                  {data.api_key}
                </code>
                <Button variant="secondary" size="sm" onClick={copy}>
                  {copied ? "✓ Copied" : "Copy"}
                </Button>
                <Button size="sm" disabled={busy} onClick={rotate}>
                  {busy ? <Spinner /> : "Rotate key"}
                </Button>
              </div>

              <div className="mt-4">
                <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-faint">
                  Sample request
                </div>
                <pre className="overflow-x-auto rounded-lg bg-[#1c1c28] p-3 font-mono text-[11px] leading-relaxed text-[#e6e6f0]">
{`curl ${data.base_url}/manager/${data.manager_id}/queue \\
  -H "Authorization: Bearer ${data.api_key}"`}
                </pre>
              </div>

              <div className="mt-4">
                <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-faint">
                  Endpoints you can call
                </div>
                <div className="space-y-1.5">
                  {data.endpoints.map((e, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span
                        className={`rounded px-1.5 py-0.5 font-mono font-semibold ${
                          e.method === "GET" ? "bg-teal-wash text-teal" : "bg-amber-wash text-amber"
                        }`}
                      >
                        {e.method}
                      </span>
                      <code className="font-mono text-ink-soft">{e.path}</code>
                      <span className="text-ink-faint">— {e.desc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </Card>
  );
}
