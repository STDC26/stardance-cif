import type { Meta, StoryObj } from "@storybook/react";
import { Image } from "./Image";

const meta: Meta<typeof Image> = { title: "Primitives/Image", component: Image, tags: ["autodocs"] };
export default meta;
type Story = StoryObj<typeof Image>;

export const Default: Story = {
  args: { asset_id: "img-001", alt_text: "Product screenshot", caption: "CIF Dashboard Overview", aspect_ratio: "16:9" },
};
