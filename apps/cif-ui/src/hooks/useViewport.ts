"use client";

import { useEffect, useRef, useCallback } from "react";

interface UseViewportOptions {
  onImpression?: (componentId: string, componentType: string) => void;
  onEngaged?: (dwellMs: number, scrollPct: number) => void;
  engageDwellMs?: number;
  engageScrollPct?: number;
}

export function useViewport({
  onImpression,
  onEngaged,
  engageDwellMs = 10000,
  engageScrollPct = 50,
}: UseViewportOptions) {
  const engagedRef = useRef(false);
  const dwellTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const startTimeRef = useRef<number>(Date.now());

  // Intersection observer for component impressions
  const observeComponent = useCallback(
    (el: HTMLElement | null) => {
      if (!el || !onImpression) return;
      const componentId = el.dataset.componentId;
      const componentType = el.dataset.componentType;
      if (!componentId || !componentType) return;

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              onImpression(componentId, componentType);
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.5 }
      );
      observer.observe(el);
      return () => observer.disconnect();
    },
    [onImpression]
  );

  // Dwell time + scroll depth for surface_engaged
  useEffect(() => {
    if (!onEngaged) return;

    // Dwell timer
    dwellTimerRef.current = setTimeout(() => {
      if (!engagedRef.current) {
        engagedRef.current = true;
        onEngaged(Date.now() - startTimeRef.current, getCurrentScrollPct());
      }
    }, engageDwellMs);

    // Scroll depth
    function handleScroll() {
      if (engagedRef.current) return;
      const pct = getCurrentScrollPct();
      if (pct >= engageScrollPct) {
        engagedRef.current = true;
        if (dwellTimerRef.current) clearTimeout(dwellTimerRef.current);
        onEngaged(Date.now() - startTimeRef.current, pct);
      }
    }

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", handleScroll);
      if (dwellTimerRef.current) clearTimeout(dwellTimerRef.current);
    };
  }, [onEngaged, engageDwellMs, engageScrollPct]);

  return { observeComponent };
}

function getCurrentScrollPct(): number {
  const el = document.documentElement;
  const scrolled = el.scrollTop || document.body.scrollTop;
  const total = el.scrollHeight - el.clientHeight;
  return total > 0 ? Math.round((scrolled / total) * 100) : 0;
}
