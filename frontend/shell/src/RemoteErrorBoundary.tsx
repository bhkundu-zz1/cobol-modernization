import { Component, type ReactNode } from "react";

interface RemoteErrorBoundaryProps {
  remoteName: string;
  children: ReactNode;
}

interface RemoteErrorBoundaryState {
  hasError: boolean;
}

/**
 * Wraps one remote's mount point (architecture.md section 8). If the
 * remote's Module Federation import throws (network error, remote down,
 * runtime exception), only this boundary's fallback renders — sibling
 * remotes mounted elsewhere in the shell are unaffected, since each is a
 * separately fetched bundle and separately rendered subtree.
 */
export class RemoteErrorBoundary extends Component<RemoteErrorBoundaryProps, RemoteErrorBoundaryState> {
  state: RemoteErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): RemoteErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    // eslint-disable-next-line no-console
    console.error(`[shell] remote "${this.props.remoteName}" failed to load or render:`, error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div role="alert" style={{ padding: "1rem", border: "1px solid #fca5a5", borderRadius: "0.5rem" }}>
          <strong>{this.props.remoteName}</strong> is temporarily unavailable.
        </div>
      );
    }
    return this.props.children;
  }
}
