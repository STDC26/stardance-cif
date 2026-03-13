"use client";

import React, { useEffect, useRef } from "react";
import { COMPONENT_REGISTRY } from "@/lib/componentRegistry";
import { useSignal } from "@/hooks/useSignal";
import { useViewport } from "@/hooks/useViewport";

export interface ResolvedComponent {
  component_id: string;
  component_type: string;
  name: string;
  section_id: string;
  position: number;
  config: Record<string, any>;
}

export interface ResolvedSection {
  section_id: string;
  components: ResolvedComponent[];
}

export interface ResolvedSurface {
  surface_id: string;
  surface_version_id: string;
  name: string;
  status: string;
  sections: ResolvedSection[];
  components: ResolvedComponent[];
}

interface SurfaceRendererProps {
  surface: ResolvedSurface;
}

export function SurfaceRenderer({ surface }: SurfaceRendererProps) {
  const { emit } = useSignal({
    surface_id: surface.surface_id,
    surface_version_id: surface.surface_version_id,
  });

  const surfaceRef = useRef<HTMLDivElement>(null);
  const viewFiredRef = useRef(false);

  // Fire surface_view on mount
  useEffect(() => {
    if (!viewFiredRef.current) {
      viewFiredRef.current = true;
      emit("surface_view", {});
    }
  }, [emit]);

  const { observeComponent } = useViewport({
    onImpression: (componentId, componentType) => {
      emit("component_impression", { component_id: componentId, component_type: componentType });
    },
    onEngaged: (dwellMs, scrollPct) => {
      emit("surface_engaged", { dwell_time_ms: dwellMs, scroll_depth_pct: scrollPct });
    },
  });

  return (
    <div
      ref={surfaceRef}
      data-surface-id={surface.surface_id}
      data-surface-version={surface.surface_version_id}
    >
      {surface.sections.map((section) => (
        <div key={section.section_id} data-section-id={section.section_id}>
          {section.components.map((component) => {
            const Component = COMPONENT_REGISTRY[component.component_type];

            if (!Component) {
              return (
                <div key={component.component_id} style={{ padding: "16px", background: "#fff3cd", border: "1px solid #ffc107", margin: "8px" }}>
                  Unknown component: {component.component_type}
                </div>
              );
            }

            const signalProps = buildSignalProps(component, emit);

            return (
              <div
                key={component.component_id}
                data-component-id={component.component_id}
                data-component-type={component.component_type}
                ref={(el) => { if (el) observeComponent(el); }}
              >
                <Component {...component.config} {...signalProps} />
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

function buildSignalProps(
  component: ResolvedComponent,
  emit: (eventType: string, payload: Record<string, any>) => void
): Record<string, any> {
  const base = {
    component_id: component.component_id,
    component_type: component.component_type,
  };

  switch (component.component_type) {
    case "cta":
      return {
        onClick: () => emit("component_click", {
          ...base,
          action_type: component.config.action_type,
          action_target: component.config.action_target,
          tracking_label: component.config.tracking_label,
        }),
      };
    case "form":
      return {
        onFormStart: () => emit("form_start", { ...base, form_type: component.config.form_type }),
        onFormSubmit: (data: Record<string, string>) => {
          emit("form_submit", { ...base, form_type: component.config.form_type });
          emit("conversion", { ...base, conversion_type: "form_submit", conversion_value: 0 });
        },
      };
    case "diagnostic_entry":
      return {
        onStart: () => emit("diagnostic_start", {
          ...base,
          diagnostic_id: component.config.diagnostic_id,
          entry_mode: component.config.entry_mode,
        }),
      };
    default:
      return {};
  }
}
