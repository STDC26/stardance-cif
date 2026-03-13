import type { Meta, StoryObj } from "@storybook/react";
import { Hero } from "./Hero";

const meta: Meta<typeof Hero> = {
  title: "Primitives/Hero",
  component: Hero,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Hero>;

export const Default: Story = {
  args: {
    headline: "Transform Your Business With Intelligence",
    subheadline: "CIF turns configuration into conversion.",
    primary_cta: "Get Started",
    secondary_cta: "Learn More",
    layout_variant: "centered",
  },
};

export const LeftAligned: Story = {
  args: {
    headline: "Built for Results",
    primary_cta: "Start Free Trial",
    layout_variant: "left",
  },
};

export const HeadlineOnly: Story = {
  args: {
    headline: "Simple. Powerful. Trackable.",
  },
};
