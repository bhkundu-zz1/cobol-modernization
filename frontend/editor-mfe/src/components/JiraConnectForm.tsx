import { useState } from "react";

export interface JiraConnectFormProps {
  onChange: (connectionConfig: Record<string, string>) => void;
}

export function JiraConnectForm({ onChange }: JiraConnectFormProps) {
  const [projectKey, setProjectKey] = useState("");
  const [credentialRef, setCredentialRef] = useState("env://JIRA_API_TOKEN_ACME2026");

  function emit(next: { projectKey: string; credentialRef: string }) {
    onChange({ project_key: next.projectKey, credential_ref: next.credentialRef });
  }

  return (
    <div>
      <label htmlFor="jira-project-key">Project key</label>
      <input
        id="jira-project-key"
        value={projectKey}
        onChange={(e) => {
          setProjectKey(e.target.value);
          emit({ projectKey: e.target.value, credentialRef });
        }}
      />

      <label htmlFor="jira-credential-ref">Credential reference</label>
      <input
        id="jira-credential-ref"
        value={credentialRef}
        onChange={(e) => {
          setCredentialRef(e.target.value);
          emit({ projectKey, credentialRef: e.target.value });
        }}
      />
    </div>
  );
}
