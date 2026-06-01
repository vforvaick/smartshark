"""Analysis Profile service — profile configs, weighting, progressive questions.

Four profiles:
- general: default, equal weighting, no special assumptions
- f5_load_balancer: VIP/pool/SNAT assumptions, TCP+HTTP weighting, F5 mapping questions
- infoblox_dns: DNS appliance assumptions, DNS weighting, Infoblox context questions
- verifone_intellinac: terminal connectivity assumptions, TCP+TLS weighting, payment limitations
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import ProfileConfig, AnalysisProfile


# ---------------------------------------------------------------------------
# Profile metadata
# ---------------------------------------------------------------------------

PROFILE_DESCRIPTIONS: dict[AnalysisProfile, str] = {
    AnalysisProfile.general: (
        "General Network Troubleshooting — runs generic network playbooks "
        "with no vendor assumptions."
    ),
    AnalysisProfile.f5_load_balancer: (
        "F5 Load Balancer — tunes checks for client-side vs server-side "
        "connection behavior, VIP/pool/pool-member mapping, SNAT, health checks, "
        "and F5-generated resets."
    ),
    AnalysisProfile.infoblox_dns: (
        "Infoblox DNS — tunes checks for DNS response/no-response patterns, "
        "response codes, latency, TCP/UDP 53 behavior."
    ),
    AnalysisProfile.verifone_intellinac: (
        "Verifone intelliNAC — tunes checks for terminal connectivity, "
        "authentication/authorization path behavior, transaction-path network reachability, "
        "with stricter payment-sensitive redaction."
    ),
}

# Assumptions per profile
PROFILE_ASSUMPTIONS: dict[AnalysisProfile, list[str]] = {
    AnalysisProfile.general: [],
    AnalysisProfile.f5_load_balancer: [
        "Capture may contain client-side and server-side connections through an F5 device.",
        "VIP/pool/pool-member mapping may be needed to interpret traffic correctly.",
        "SNAT may obscure true client IPs on the server side.",
        "F5 health checks may appear as synthetic TCP connections.",
        "F5-generated RSTs may appear for pool member failures or iRule actions.",
    ],
    AnalysisProfile.infoblox_dns: [
        "Capture contains DNS traffic involving an Infoblox appliance.",
        "DNS queries may show recursive or authoritative behavior depending on appliance role.",
        "Timeouts may indicate appliance-side service issues.",
        "TCP/UDP 53 behavior may differ based on query size and appliance configuration.",
    ],
    AnalysisProfile.verifone_intellinac: [
        "Capture contains network access or transaction-path traffic involving Verifone intelliNAC.",
        "Terminal connectivity issues may present as TCP/TLS handshake failures.",
        "Authentication/authorization paths may involve multiple network hops.",
        "Payment-sensitive data may be present and requires stricter redaction.",
    ],
}

# Limitations per profile
PROFILE_LIMITATIONS: dict[AnalysisProfile, list[str]] = {
    AnalysisProfile.general: [
        "Capture vantage point is unknown — path visibility may be incomplete.",
    ],
    AnalysisProfile.f5_load_balancer: [
        "One-arm vs two-arm visibility ambiguity not resolved without F5 mapping.",
        "SNAT addresses may mask true client IPs without mapping configuration.",
        "F5 iRule behavior cannot be inferred from packet data alone.",
        "Capture vantage point is unknown — client-side and server-side visibility may be asymmetric.",
    ],
    AnalysisProfile.infoblox_dns: [
        "DNS appliance role (recursive, authoritative, forwarding) not confirmed from packet data alone.",
        "Internal DNS response codes may differ from public DNS behavior.",
        "Appliance-side service visibility limited to observed query/response patterns.",
    ],
    AnalysisProfile.verifone_intellinac: [
        "Payment-sensitive data requires strict redaction before AI analysis.",
        "Terminal authentication details may be encrypted and not inspectable.",
        "Transaction-path network reachability may depend on configuration not visible in packets.",
        "Cardholder data (PAN, CVV, expiry) must be masked per PCI-DSS requirements.",
        "Raw context sharing is tightly restricted for payment-sensitive profiles.",
    ],
}

# Check weighting per profile: check_name → weight (1.0 = default)
# Higher weight = check runs with more emphasis
PROFILE_CHECK_WEIGHTING: dict[AnalysisProfile, dict[str, float]] = {
    AnalysisProfile.general: {
        "tcp_health": 1.0,
        "dns_resolution": 1.0,
        "http_api": 1.0,
        "tls_handshake": 1.0,
        "path_visibility": 1.0,
    },
    AnalysisProfile.f5_load_balancer: {
        "tcp_health": 1.5,
        "dns_resolution": 0.5,
        "http_api": 1.5,
        "tls_handshake": 1.0,
        "path_visibility": 1.0,
    },
    AnalysisProfile.infoblox_dns: {
        "tcp_health": 0.5,
        "dns_resolution": 2.0,
        "http_api": 0.5,
        "tls_handshake": 0.5,
        "path_visibility": 1.0,
    },
    AnalysisProfile.verifone_intellinac: {
        "tcp_health": 1.5,
        "dns_resolution": 0.5,
        "http_api": 1.0,
        "tls_handshake": 1.5,
        "path_visibility": 1.0,
    },
}

# Progressive mapping questions per profile
PROFILE_MAPPING_QUESTIONS: dict[AnalysisProfile, list[dict]] = {
    AnalysisProfile.general: [],
    AnalysisProfile.f5_load_balancer: [
        {
            "id": "f5_vip_address",
            "question": "What is the F5 VIP address (if known)?",
            "type": "text",
            "required": False,
        },
        {
            "id": "f5_pool_members",
            "question": "What are the pool member IP addresses?",
            "type": "text",
            "required": False,
        },
        {
            "id": "f5_snat_mode",
            "question": "Is SNAT enabled (automap, SNAT pool, or none)?",
            "type": "select",
            "options": ["automap", "snat_pool", "none", "unknown"],
            "required": False,
        },
        {
            "id": "f5_vlan_side",
            "question": "Which VLAN side was captured (client, server, or both)?",
            "type": "select",
            "options": ["client", "server", "both", "unknown"],
            "required": False,
        },
    ],
    AnalysisProfile.infoblox_dns: [
        {
            "id": "infoblox_role",
            "question": "What is the Infoblox appliance role?",
            "type": "select",
            "options": ["recursive", "authoritative", "forwarding", "hybrid", "unknown"],
            "required": False,
        },
        {
            "id": "infoblox_grid_member",
            "question": "Is this a Grid Master or Grid Member?",
            "type": "select",
            "options": ["grid_master", "grid_member", "standalone", "unknown"],
            "required": False,
        },
    ],
    AnalysisProfile.verifone_intellinac: [
        {
            "id": "verifone_terminal_type",
            "question": "What type of terminals are involved?",
            "type": "select",
            "options": ["pos", "atm", "unattended", "mixed", "unknown"],
            "required": False,
        },
        {
            "id": "verifone_network_segment",
            "question": "Is the capture from the management network, transaction network, or both?",
            "type": "select",
            "options": ["management", "transaction", "both", "unknown"],
            "required": False,
        },
    ],
}


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def get_profile_config_data(profile: AnalysisProfile) -> dict:
    """Return config for a profile: assumptions, limitations, weighting, questions."""
    return {
        "profile": profile,
        "assumptions": PROFILE_ASSUMPTIONS.get(profile, []),
        "limitations": PROFILE_LIMITATIONS.get(profile, []),
        "check_weighting": PROFILE_CHECK_WEIGHTING.get(profile, {}),
        "mapping_questions": PROFILE_MAPPING_QUESTIONS.get(profile, []),
    }


def get_progressive_questions(
    profile: AnalysisProfile,
    prescan_data: dict | None = None,
) -> list[dict]:
    """Return progressive questions based on profile and prescan data.

    For vendor profiles, always return their mapping questions.
    For general, return empty (no progressive questions).
    Future: filter/sort questions based on prescan findings.
    """
    return PROFILE_MAPPING_QUESTIONS.get(profile, [])


async def set_run_profile(
    db: AsyncSession, run_id: int, profile: AnalysisProfile
) -> ProfileConfig:
    """Attach a profile config to an analysis run. Raises ValueError if already set."""
    result = await db.execute(
        select(ProfileConfig).where(ProfileConfig.analysis_run_id == run_id)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise ValueError("Profile already set for this analysis run")

    config_data = get_profile_config_data(profile)
    config = ProfileConfig(
        analysis_run_id=run_id,
        profile=profile,
        assumptions=config_data["assumptions"],
        limitations=config_data["limitations"],
        mapping_questions=config_data["mapping_questions"],
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


async def get_run_profile(db: AsyncSession, run_id: int) -> ProfileConfig | None:
    """Get the profile config for a run, or None."""
    result = await db.execute(
        select(ProfileConfig).where(ProfileConfig.analysis_run_id == run_id)
    )
    return result.scalar_one_or_none()
