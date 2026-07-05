export type BadgeTone = "neutral" | "success" | "warning" | "danger";

export interface BadgeProps {
  tone?: BadgeTone;
  children: React.ReactNode;
}

const TONE_COLORS: Record<BadgeTone, { bg: string; fg: string }> = {
  neutral: { bg: "#e5e7eb", fg: "#111827" },
  success: { bg: "#dcfce7", fg: "#166534" },
  warning: { bg: "#fef3c7", fg: "#92400e" },
  danger: { bg: "#fee2e2", fg: "#991b1b" },
};

export function Badge({ tone = "neutral", children }: BadgeProps) {
  const colors = TONE_COLORS[tone];
  return (
    <span
      data-tone={tone}
      style={{
        display: "inline-block",
        padding: "0.125rem 0.5rem",
        borderRadius: "9999px",
        fontSize: "0.75rem",
        fontWeight: 600,
        backgroundColor: colors.bg,
        color: colors.fg,
      }}
    >
      {children}
    </span>
  );
}
