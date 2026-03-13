import type { Meta, StoryObj } from "@storybook/react";
import { CTA } from "./CTA";

const meta: Meta<typeof CTA> = {
  title: "Primitives/CTA",
  component: CTA,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof CTA>;

export const Primary: Story = {
  args: {
    label: "Get Started Now",
    action_type: "link",
    action_target: "/signup",
    style_variant: "primary",
    tracking_label: "hero-primary-cta",
  },
};

export const Secondary: Story = {
  args: {
    label: "Learn More",
    action_type: "scroll",
    action_target: "#features",
    style_variant: "secondary",
  },
};

export const Ghost: Story = {
  args: {
    label: "See Examples",
    action_type: "link",
    action_target: "/examples",
    style_variant: "ghost",
  },
};
