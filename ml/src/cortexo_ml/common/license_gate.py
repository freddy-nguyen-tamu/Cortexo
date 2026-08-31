from dataclasses import dataclass

ALLOWLISTED = {
    "mit", "mit-0", "apache-2.0", "apache-2", "bsd-3-clause", "bsd-2-clause",
    "isc", "unlicense", "cc0-1.0", "mpl-2.0", "lgpl-2.1", "lgpl-2.1-only",
    "lgpl-2.1-or-later", "python-2.0", "zlib", "postgresql",
}
BLOCKLISTED = {
    "agpl-3.0", "agpl-3.0-only", "agpl-3.0-or-later", "sspl-1.0", "business-source",
    "busl-1.1", "elastic-2.0",
}
UNKNOWN = None


@dataclass
class LicenseDecision:
    license_id: str | None
    allowed_for_training: bool
    allowed_for_redistribution: bool
    reason: str


def classify_license(
    license_id: str | None,
    explicit_verified: bool = False,
) -> LicenseDecision:
    """Gate corpus sources before collection/training.

    Rules (configurable elsewhere, kept conservative here):
    - An explicitly verified permissive identifier is trainable and redistributable.
    - Missing/unknown license is never trainable by default.
    - Strong copyleft is excluded from training unless the operator provides
      explicit verified permission records.
    """
    if not license_id:
        return LicenseDecision(None, False, False, "unknown license: excluded by default")
    norm = license_id.strip().lower()

    if norm in ALLOWLISTED:
        if explicit_verified:
            return LicenseDecision(license_id, True, True, "permissive + verified")
        return LicenseDecision(license_id, True, False, "permissive but redistribution needs re-check")
    if norm in BLOCKLISTED:
        return LicenseDecision(license_id, False, False, "copyleft/commercial restriction")
    return LicenseDecision(license_id, False, False, f"unrecognized license: {license_id}")


def verify_license_for_training(manifest_entry: dict) -> tuple[bool, str]:
    license_id = manifest_entry.get("license")
    verified = bool(manifest_entry.get("license_verified"))
    decision = classify_license(license_id, explicit_verified=verified)
    if not decision.allowed_for_training and not verified:
        return False, decision.reason
    return True, decision.reason


def is_public_domain_note(license_id: str | None) -> bool:
    if not license_id:
        return False
    norm = license_id.strip().lower()
    return norm in {"unlicense", "cc0-1.0", "public-domain"}