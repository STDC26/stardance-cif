import type { Meta, StoryObj } from "@storybook/react";
import { Form } from "./Form";

const meta: Meta<typeof Form> = { title: "Primitives/Form", component: Form, tags: ["autodocs"] };
export default meta;
type Story = StoryObj<typeof Form>;

export const LeadCapture: Story = {
  args: {
    form_type: "lead_capture",
    submit_label: "Get My Free Analysis",
    success_state: "We'll be in touch within 24 hours.",
    fields: [
      { name: "first_name", label: "First Name", type: "text", required: true, placeholder: "Jane" },
      { name: "email", label: "Email", type: "email", required: true, placeholder: "jane@company.com" },
      { name: "company", label: "Company", type: "text", placeholder: "Acme Inc." },
    ],
  },
};
