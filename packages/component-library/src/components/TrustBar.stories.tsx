import type { Meta, StoryObj } from "@storybook/react";
import { TrustBar } from "./TrustBar";

const meta: Meta<typeof TrustBar> = { title: "Primitives/TrustBar", component: TrustBar, tags: ["autodocs"] };
export default meta;
type Story = StoryObj<typeof TrustBar>;

export const Light: Story = {
  args: { variant: "light", items: [{ label: "SOC 2 Compliant", icon: "🔒" }, { label: "99.9% Uptime", icon: "⚡" }, { label: "GDPR Ready", icon: "✓" }, { label: "24/7 Support", icon: "💬" }] },
};
export const Dark: Story = {
  args: { variant: "dark", items: [{ label: "No Credit Card Required", icon: "✓" }, { label: "Cancel Anytime", icon: "✓" }, { label: "14-Day Free Trial", icon: "🎁" }] },
};
