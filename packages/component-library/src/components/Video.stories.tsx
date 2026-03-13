import type { Meta, StoryObj } from "@storybook/react";
import { Video } from "./Video";

const meta: Meta<typeof Video> = { title: "Primitives/Video", component: Video, tags: ["autodocs"] };
export default meta;
type Story = StoryObj<typeof Video>;

export const Default: Story = {
  args: { asset_id: "vid-001", caption: "See CIF in action", autoplay: false, controls: true },
};
