import type { Meta, StoryObj } from "@storybook/react";
import { TextBlock } from "./TextBlock";

const meta: Meta<typeof TextBlock> = { title: "Primitives/TextBlock", component: TextBlock, tags: ["autodocs"] };
export default meta;
type Story = StoryObj<typeof TextBlock>;

export const Default: Story = {
  args: { title: "Why CIF Works", body: "The Creative Intelligence Factory turns behavioral data into optimized conversion surfaces — automatically.", alignment: "left" },
};
export const Centered: Story = {
  args: { body: "Every surface is instrumented, versioned, and experiment-ready.", alignment: "center" },
};
