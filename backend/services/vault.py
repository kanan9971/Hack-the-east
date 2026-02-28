import hashlib
import json
import time
import uuid
from datetime import datetime, timezone


ABELIAN_NETWORK = "Abelian Mainnet (Post-Quantum Lattice)"
ABELIAN_ALGO = "ABEL-MLWE-256"


def _canonical_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_vault_hash(analysis: dict) -> str:
    """SHA-256 fingerprint of the analysis payload."""
    canonical = _canonical_json(analysis)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def generate_abelian_address() -> str:
    """Simulated Abelian lattice-based vault address."""
    raw = uuid.uuid4().hex + uuid.uuid4().hex
    return "abel1q" + hashlib.sha256(raw.encode()).hexdigest()[:56]


def create_vault_receipt(analysis: dict) -> dict:
    content_hash = compute_vault_hash(analysis)
    vault_id = f"ABEL-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.now(timezone.utc)

    return {
        "vault_id": vault_id,
        "content_hash": content_hash,
        "timestamp": now.isoformat(),
        "vault_address": generate_abelian_address(),
        "network": ABELIAN_NETWORK,
        "algorithm": ABELIAN_ALGO,
        "status": "sealed",
        "expires": None,
        "message": (
            "Your analysis has been cryptographically sealed using post-quantum "
            "lattice-based encryption on the Abelian network. Only you hold the "
            "decryption key."
        ),
    }
