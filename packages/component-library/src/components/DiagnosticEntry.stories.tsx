import type { Meta, StoryObj } from "@storybook/react";
import { DiagnosticEntry } from "./DiagnosticEntry";

const meta: Meta<typeof DiagnosticEntry> = { title: "Primitives/DiagnosticEntry", component: DiagnosticEntry, tags: ["autodocs"] };
export default meta;
type Story = StoryObj<typeof DiagnosticEntry>;

export const Default: Story = {
  args: { entry_label: "Find Your Conversion Gaps in 5 Minutes", entry_mode: "button", diagnostic_id: "diag-conversion-001", tracking_label: "homepage-diagnostic-entry" },
};
