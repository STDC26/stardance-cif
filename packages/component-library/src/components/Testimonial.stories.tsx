import type { Meta, StoryObj } from "@storybook/react";
import { Testimonial } from "./Testimonial";

const meta: Meta<typeof Testimonial> = { title: "Primitives/Testimonial", component: Testimonial, tags: ["autodocs"] };
export default meta;
type Story = StoryObj<typeof Testimonial>;

export const Default: Story = {
  args: { quote: "The signal layer alone has transformed how we think about conversion optimization.", author_name: "Priya Sharma", author_title: "VP Marketing, Nexus Health", variant: "card" },
};
export const Large: Story = {
  args: { quote: "We shipped 12 surfaces in the time it used to take to build one.", author_name: "Daniel Wu", author_title: "Founder, Clearpath", variant: "large" },
};
