"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { SurfaceRenderer, ResolvedSurface } from "@/components/SurfaceRenderer";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SurfaceDetailPage() {
  const params = useParams();
  const surfaceId = params.id as string;
  const [surface, setSurface] = useState<ResolvedSurface | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/surfaces/${surfaceId}/resolve`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => { setSurface(data); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, [surfaceId]);

  if (loading) return <div style={{ padding: "48px", textAlign: "center" }}>Loading surface...</div>;
  if (error) return <div style={{ padding: "48px", color: "red" }}>Error: {error}</div>;
  if (!surface) return <div style={{ padding: "48px" }}>Surface not found.</div>;

  return <SurfaceRenderer surface={surface} />;
}
