import type { Meta, StoryObj } from "@storybook/react";
import { SocialProof } from "./SocialProof";

const meta: Meta<typeof SocialProof> = { title: "Primitives/SocialProof", component: SocialProof, tags: ["autodocs"] };
export default meta;
type Story = StoryObj<typeof SocialProof>;

export const WithQuotes: Story = {
  args: {
    proof_type: "quotes",
    rating: 4.8,
    review_count: 1240,
    quotes: [
      { text: "CIF cut our surface build time by 80%.", author: "Sarah K., Head of Growth" },
      { text: "Every surface now ships with full signal instrumentation. Game changer.", author: "Marcus T., CTO" },
    ],
    logo_asset_ids: ["logo-001", "logo-002", "logo-003"],
  },
};
