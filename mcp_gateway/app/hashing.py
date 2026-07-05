"""Canonicalization + sha256 helpers for the audit log's hash chain (architecture.md section 6.2).

Kept dependency-free (stdlib only) so it's trivially unit-testable without a
running CouchDB instance.
"""

import hashlib
import json
from typing import Any

GENESIS_HASH = "0" * 64


def canonicalize(payload: dict[str, Any]) -> str:
    """Deterministic JSON serialization so the same logical event always hashes
    the same way regardless of dict key insertion order."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_event_hash(event_payload: dict[str, Any], prev_event_hash: str) -> str:
    """this_event_hash = sha256(canonicalize(event) + prev_event_hash) — architecture.md section 6.2.

    `event_payload` must exclude `this_event_hash` itself (it doesn't exist yet)
    but must include every other field, including `prev_event_hash`.
    """
    canonical = canonicalize(event_payload)
    return sha256_hex(canonical + prev_event_hash)


# Fields CouchDB (or the storage layer) attaches after the fact, which were
# never part of the payload audit_append originally hashed.
_STORAGE_ONLY_FIELDS = {"this_event_hash", "_id", "_rev"}


def verify_chain(events: list[dict[str, Any]]) -> bool:
    """Walk prev_event_hash -> this_event_hash links across events (already
    ordered by timestamp ascending). Returns False on the first break found."""
    expected_prev = GENESIS_HASH
    for event in events:
        if event.get("prev_event_hash") != expected_prev:
            return False
        recomputed = compute_event_hash(
            {k: v for k, v in event.items() if k not in _STORAGE_ONLY_FIELDS},
            event["prev_event_hash"],
        )
        if recomputed != event.get("this_event_hash"):
            return False
        expected_prev = event["this_event_hash"]
    return True
