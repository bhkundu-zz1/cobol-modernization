"""Mainframe SCM adapter interface + registry (architecture.md section 1a).

`get_adapter(tool)` is the single seam mainframe_tools.py depends on.
Selecting a real (non-mock) tool returns a real adapter class implementing
the shared interface, but its HTTP methods raise NotImplementedError with a
message naming the wire protocol that's still future work — see
docs/deferred_scope.md. This must fail loudly, never silently fall back to
mock data.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

_FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "sample_cobol" / "PAYROLL01.CBL"


class MainframeAdapter(ABC):
    """Common interface every SCM tool adapter implements (architecture.md section 1a)."""

    @abstractmethod
    def list_elements(
        self, *, host: str, credential_ref: str, system: str, subsystem: str, element_type: str
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_source(
        self,
        *,
        host: str,
        credential_ref: str,
        system: str,
        subsystem: str,
        element_type: str,
        element_id: str,
    ) -> str: ...

    @abstractmethod
    def get_metadata(
        self,
        *,
        host: str,
        credential_ref: str,
        system: str,
        subsystem: str,
        element_type: str,
        element_id: str,
    ) -> dict[str, Any]: ...


class MockAdapter(MainframeAdapter):
    """The only adapter with a real, runnable implementation this pass.
    Returns fixture COBOL content simulating a real element list/pull, so
    the full ingestion -> structural -> recommendation pipeline can be
    exercised end-to-end without a live mainframe (see plan's vertical-slice
    scope decision)."""

    _KNOWN_ELEMENTS = [{"element_id": "PAYROLL01", "element_type": "COBOL", "version": "12"}]

    def list_elements(self, *, host, credential_ref, system, subsystem, element_type):
        return [e for e in self._KNOWN_ELEMENTS if e["element_type"] == element_type] or self._KNOWN_ELEMENTS

    def get_source(self, *, host, credential_ref, system, subsystem, element_type, element_id):
        if element_id != "PAYROLL01":
            raise ValueError(f"mock adapter has no fixture content for element_id={element_id!r}")
        return _FIXTURE_PATH.read_text(encoding="utf-8")

    def get_metadata(self, *, host, credential_ref, system, subsystem, element_type, element_id):
        return {
            "tool": "mock",
            "system": system,
            "subsystem": subsystem,
            "type": element_type,
            "element_id": element_id,
            "version": "12",
        }


class _NotYetImplementedAdapter(MainframeAdapter):
    """Base for real (non-mock) adapters: real class, real interface, but
    every method fails loudly rather than silently returning mock data."""

    tool_name: str
    protocol_description: str

    def _not_implemented(self) -> NotImplementedError:
        return NotImplementedError(
            f"{self.tool_name} connector wire protocol not yet implemented "
            f"({self.protocol_description}); only the mock adapter is "
            f"available this pass. See docs/deferred_scope.md."
        )

    def list_elements(self, *, host, credential_ref, system, subsystem, element_type):
        raise self._not_implemented()

    def get_source(self, *, host, credential_ref, system, subsystem, element_type, element_id):
        raise self._not_implemented()

    def get_metadata(self, *, host, credential_ref, system, subsystem, element_type, element_id):
        raise self._not_implemented()


class EndevorAdapter(_NotYetImplementedAdapter):
    tool_name = "Endevor"
    protocol_description = "Endevor Web Services REST API v2"


class PanvaletAdapter(_NotYetImplementedAdapter):
    tool_name = "PanValet"
    protocol_description = "PAM API for browsing, or batch-extract via PAN#1 to a PDS read via z/OSMF"


class ChangemanAdapter(_NotYetImplementedAdapter):
    tool_name = "ChangeMan ZMF"
    protocol_description = "ChangeMan ZMF REST API Server (v8.1+)"


_ADAPTERS: dict[str, type[MainframeAdapter]] = {
    "mock": MockAdapter,
    "endevor": EndevorAdapter,
    "panvalet": PanvaletAdapter,
    "changeman": ChangemanAdapter,
}


def get_adapter(tool: str) -> MainframeAdapter:
    try:
        adapter_cls = _ADAPTERS[tool]
    except KeyError:
        raise ValueError(f"unknown mainframe SCM tool: {tool!r}; expected one of {sorted(_ADAPTERS)}") from None
    return adapter_cls()
