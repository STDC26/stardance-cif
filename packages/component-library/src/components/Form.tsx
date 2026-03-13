import React, { useState } from "react";

export interface FormField {
  name: string;
  label: string;
  type: "text" | "email" | "tel" | "textarea" | "select";
  required?: boolean;
  placeholder?: string;
}

export interface FormProps {
  form_type: string;
  fields: FormField[];
  submit_label: string;
  success_state?: string;
  onFormStart?: () => void;
  onFormSubmit?: (data: Record<string, string>) => void;
}

export function Form({ fields, submit_label, success_state = "Thank you!", onFormStart, onFormSubmit }: FormProps) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [started, setStarted] = useState(false);

  function handleChange(name: string, value: string) {
    if (!started) { setStarted(true); onFormStart?.(); }
    setValues(v => ({ ...v, [name]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    onFormSubmit?.(values);
  }

  if (submitted) {
    return (
      <div data-component="form" style={{ padding: "40px 32px", textAlign: "center" }}>
        <p style={{ fontSize: "1.25rem", color: "#1F3A6E", fontWeight: 600 }}>{success_state}</p>
      </div>
    );
  }

  return (
    <form data-component="form" onSubmit={handleSubmit} style={{ padding: "40px 32px", display: "flex", flexDirection: "column", gap: "16px", maxWidth: "480px" }}>
      {fields.map(field => (
        <div key={field.name} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label style={{ fontWeight: 600, fontSize: "0.9rem" }}>{field.label}{field.required && " *"}</label>
          {field.type === "textarea" ? (
            <textarea placeholder={field.placeholder} required={field.required} rows={4}
              style={{ padding: "10px", border: "1px solid #ccc", borderRadius: "4px", fontSize: "1rem" }}
              onChange={e => handleChange(field.name, e.target.value)} />
          ) : (
            <input type={field.type} placeholder={field.placeholder} required={field.required}
              style={{ padding: "10px", border: "1px solid #ccc", borderRadius: "4px", fontSize: "1rem" }}
              onChange={e => handleChange(field.name, e.target.value)} />
          )}
        </div>
      ))}
      <button type="submit" style={{ padding: "12px 24px", background: "#1F3A6E", color: "#fff", border: "none", borderRadius: "6px", fontSize: "1rem", fontWeight: 600, cursor: "pointer", marginTop: "8px" }}>
        {submit_label}
      </button>
    </form>
  );
}
