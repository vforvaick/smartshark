"""Evidence Map Validator — enforces Claim Status rules.

This is the critical anti-hallucination module. It ensures:
- Verified claims have evidence links
- Likely claims have evidence links
- Hypotheses have verification steps
- Unsupported claims cannot be marked reportable
"""

from app.models.evidence import Claim, ClaimStatus, EvidenceMap


class ValidationError(Exception):
    """Raised when a claim violates Evidence Map rules."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def validate_claim_for_create(
    status: ClaimStatus,
    evidence_refs: list[dict],
    verification_step: str | None,
) -> None:
    """Validate claim data before creation. Raises ValidationError on violation."""
    if status in (ClaimStatus.verified, ClaimStatus.likely):
        if not evidence_refs:
            raise ValidationError(
                f"{status.value.capitalize()} claims require at least one evidence reference."
            )

    if status == ClaimStatus.hypothesis:
        if not verification_step:
            raise ValidationError(
                "Hypothesis claims require a verification step."
            )


def validate_claim_status_update(
    claim: Claim,
    new_status: ClaimStatus,
    evidence_refs: list[dict] | None = None,
) -> None:
    """Validate a status transition. Raises ValidationError on violation."""
    # Merge existing refs with any new ones provided
    effective_refs = evidence_refs if evidence_refs is not None else claim.evidence_refs

    if new_status in (ClaimStatus.verified, ClaimStatus.likely):
        if not effective_refs:
            raise ValidationError(
                f"{new_status.value.capitalize()} claims require at least one evidence reference."
            )

    if new_status == ClaimStatus.hypothesis:
        if not claim.verification_step:
            raise ValidationError(
                "Hypothesis claims require a verification step."
            )


def validate_reportable(claim: Claim, is_reportable: bool) -> None:
    """Validate whether a claim can be marked reportable."""
    if is_reportable and claim.status not in (ClaimStatus.verified, ClaimStatus.likely):
        raise ValidationError(
            f"Only verified or likely claims can be marked reportable. "
            f"Current status: {claim.status.value}."
        )


def validate_evidence_map(evidence_map: EvidenceMap) -> list[str]:
    """Validate all claims in an evidence map. Returns list of violation messages."""
    violations = []
    for claim in evidence_map.claims:
        try:
            if claim.status in (ClaimStatus.verified, ClaimStatus.likely):
                if not claim.evidence_refs:
                    violations.append(
                        f"Claim {claim.id}: {claim.status.value} requires evidence references."
                    )
                if claim.is_reportable and not claim.evidence_refs:
                    violations.append(
                        f"Claim {claim.id}: reportable claim has no evidence references."
                    )

            if claim.status == ClaimStatus.hypothesis and not claim.verification_step:
                violations.append(
                    f"Claim {claim.id}: hypothesis requires a verification step."
                )

            if claim.status == ClaimStatus.unsupported and claim.is_reportable:
                violations.append(
                    f"Claim {claim.id}: unsupported claim cannot be reportable."
                )
        except Exception as e:
            violations.append(f"Claim {claim.id}: validation error — {e}")

    return violations
