import type { Meta, StoryObj } from "@storybook/react";
import { FAQ } from "./FAQ";

const meta: Meta<typeof FAQ> = { title: "Primitives/FAQ", component: FAQ, tags: ["autodocs"] };
export default meta;
type Story = StoryObj<typeof FAQ>;

export const Default: Story = {
  args: {
    default_open_index: 0,
    items: [
      { question: "How long does it take to deploy a surface?", answer: "With CIF, a fully instrumented surface can be configured and deployed in under an hour." },
      { question: "Can I run A/B tests on surfaces?", answer: "Yes. Every surface supports experiment variants with full signal tracking per variant." },
      { question: "What data do signals capture?", answer: "Signals capture behavioral events — views, clicks, form interactions, and conversions — tied to session and surface context." },
    ],
  },
};
