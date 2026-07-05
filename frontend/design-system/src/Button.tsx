import type { ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const VARIANT_STYLES: Record<ButtonVariant, string> = {
  primary: "background-color:#c15f3c;color:#fff;border:none;",
  secondary: "background-color:#f3ede3;color:#2b2823;border:none;",
  danger: "background-color:#dc2626;color:#fff;border:none;",
};

export function Button({ variant = "primary", style, children, ...rest }: ButtonProps) {
  return (
    <button
      {...rest}
      data-variant={variant}
      style={{
        padding: "0.5rem 1rem",
        borderRadius: "0.5rem",
        cursor: "pointer",
        fontSize: "0.875rem",
        fontFamily: "inherit",
        fontWeight: 500,
        ...parseInlineStyle(VARIANT_STYLES[variant]),
        ...style,
      }}
    >
      {children}
    </button>
  );
}

function parseInlineStyle(css: string): Record<string, string> {
  return Object.fromEntries(
    css
      .split(";")
      .filter(Boolean)
      .map((rule) => {
        const [key, value] = rule.split(":");
        const camelKey = key.trim().replace(/-([a-z])/g, (_, c) => c.toUpperCase());
        return [camelKey, value.trim()];
      })
  );
}
