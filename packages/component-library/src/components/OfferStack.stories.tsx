import type { Meta, StoryObj } from "@storybook/react";
import { OfferStack } from "./OfferStack";

const meta: Meta<typeof OfferStack> = { title: "Primitives/OfferStack", component: OfferStack, tags: ["autodocs"] };
export default meta;
type Story = StoryObj<typeof OfferStack>;

export const Default: Story = {
  args: {
    offer_title: "Growth Package",
    price: "$497",
    compare_at_price: "$997",
    urgency_text: "Only 3 spots remaining this month.",
    items: [
      { label: "Full CIF Platform Access", included: true },
      { label: "5 Active Conversion Surfaces", included: true },
      { label: "Signal Intelligence Dashboard", included: true },
      { label: "Custom Domain", included: false },
    ],
    bonus_items: ["30-min Strategy Session", "Conversion Audit Report"],
  },
};
