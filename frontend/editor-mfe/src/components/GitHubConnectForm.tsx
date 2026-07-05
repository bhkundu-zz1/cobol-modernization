import { useState } from "react";

export interface GitHubConnectFormProps {
  onChange: (connectionConfig: Record<string, string>) => void;
}

export function GitHubConnectForm({ onChange }: GitHubConnectFormProps) {
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [credentialRef, setCredentialRef] = useState("env://GITHUB_PAT_ACME2026");

  function emit(next: { owner: string; repo: string; credentialRef: string }) {
    onChange({ owner: next.owner, repo: next.repo, credential_ref: next.credentialRef });
  }

  return (
    <div>
      <label htmlFor="github-owner">Owner</label>
      <input
        id="github-owner"
        value={owner}
        onChange={(e) => {
          setOwner(e.target.value);
          emit({ owner: e.target.value, repo, credentialRef });
        }}
      />

      <label htmlFor="github-repo">Repo</label>
      <input
        id="github-repo"
        value={repo}
        onChange={(e) => {
          setRepo(e.target.value);
          emit({ owner, repo: e.target.value, credentialRef });
        }}
      />

      <label htmlFor="github-credential-ref">Credential reference</label>
      <input
        id="github-credential-ref"
        value={credentialRef}
        onChange={(e) => {
          setCredentialRef(e.target.value);
          emit({ owner, repo, credentialRef: e.target.value });
        }}
      />
    </div>
  );
}
