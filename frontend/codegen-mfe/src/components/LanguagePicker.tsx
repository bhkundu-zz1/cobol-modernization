import type { CodeGenTarget } from "../api/codegenBffClient";

export interface LanguagePickerProps {
  value: CodeGenTarget;
  onChange: (value: CodeGenTarget) => void;
  disabled?: boolean;
}

const OPTIONS: { value: CodeGenTarget; label: string }[] = [
  { value: "python", label: "Python" },
  { value: "java_spring_boot", label: "Java Spring Boot" },
];

export function LanguagePicker({ value, onChange, disabled }: LanguagePickerProps) {
  return (
    <fieldset style={{ border: "none", padding: 0, margin: 0, display: "flex", gap: "1rem" }}>
      <legend style={{ padding: 0, marginBottom: "0.375rem", fontSize: "0.875rem", fontWeight: 600 }}>
        Target language
      </legend>
      {OPTIONS.map((option) => (
        <label key={option.value} style={{ display: "flex", alignItems: "center", gap: "0.375rem", cursor: "pointer" }}>
          <input
            type="radio"
            name="codegen-target-language"
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
            disabled={disabled}
          />
          {option.label}
        </label>
      ))}
    </fieldset>
  );
}
