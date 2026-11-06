"""Jurisdictions (2.2): each one's official hosts, identifiers and well-known acts.

A jurisdiction is a module of fixed data and pure functions, so adding one never changes the
records: declarations, runs, locks and signatures stay the same files. The EU is the first;
the UK (legislation.gov.uk) the second. Official hosting shows where a text came from, never
that it is binding, complete, applicable or current; reviewers decide that.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Jurisdiction:
    code: str
    name: str
    # Exact hosts law text may be retrieved from, and the official domain each must sit under.
    hosts: frozenset[str]
    domain: str
    # Hosts that redirect their own https requests to http on the same host (upgraded back to https).
    https_upgrade_hosts: frozenset[str] = frozenset()
    # Well-known acts: identifier -> common names, used to tell which act a citation names.
    known_acts: dict[str, tuple[str, ...]] = field(default_factory=dict)


EU = Jurisdiction(
    code="EU", name="European Union",
    hosts=frozenset({"eur-lex.europa.eu", "curia.europa.eu", "commission.europa.eu", "digital-strategy.ec.europa.eu",
                     "www.edpb.europa.eu", "publications.europa.eu"}),
    domain=".europa.eu",
    https_upgrade_hosts=frozenset({"publications.europa.eu"}),
    # By the CELEX number of the act as first published.
    known_acts={
        "32016R0679": ("GDPR", "General Data Protection Regulation"),
        "32024R1689": ("AI Act", "Artificial Intelligence Act"),
        "32002L0058": ("ePrivacy Directive", "ePrivacy", "Directive on privacy and electronic communications"),
        "32022R2065": ("DSA", "Digital Services Act"),
        "32022R1925": ("DMA", "Digital Markets Act"),
        "32023R2854": ("Data Act",),
        "32022L2555": ("NIS2", "NIS 2 Directive"),
        "32024R2847": ("CRA", "Cyber Resilience Act"),
        "32019L0882": ("European Accessibility Act", "EAA"),
        "32011L0083": ("Consumer Rights Directive",),
        "32018R1725": ("EUDPR",),
    })

UK = Jurisdiction(
    code="UK", name="United Kingdom",
    hosts=frozenset({"www.legislation.gov.uk"}),
    domain=".legislation.gov.uk",
    # By legislation.gov.uk identifier (type/year/number).
    known_acts={
        "eur/2016/679": ("UK GDPR",),
        "ukpga/2018/12": ("Data Protection Act 2018", "DPA 2018"),
        "uksi/2003/2426": ("PECR", "Privacy and Electronic Communications Regulations"),
        "ukpga/2023/50": ("Online Safety Act 2023", "Online Safety Act"),
        "ukpga/2015/15": ("Consumer Rights Act 2015",),
        "ukpga/2024/13": ("Digital Markets, Competition and Consumers Act 2024", "DMCC Act"),
        "ukpga/2010/15": ("Equality Act 2010",),
    })

ALL = (EU, UK)
OFFICIAL_HOSTS = frozenset().union(*(item.hosts for item in ALL))
HTTPS_UPGRADE_HOSTS = frozenset().union(*(item.https_upgrade_hosts for item in ALL))
# legislation.gov.uk document types: Acts, statutory instruments, retained (assimilated) EU law.
UK_TYPES = frozenset({"ukpga", "uksi", "asp", "asc", "anaw", "mwa", "nia", "nisi", "nisr", "ssi", "wsi", "eur", "eudr",
                      "eudn", "ukla", "ukcm"})


def _date(text: str) -> bool:
    parts = text.split("-")
    return len(parts) == 3 and [len(part) for part in parts] == [4, 2, 2] and all(p.isascii() and p.isdigit() for p in parts)


def uk_version(identifier: str | None, url: str | None = None) -> dict | None:
    """A legislation.gov.uk identifier, from 'ukpga/2018/12' or a URL on www.legislation.gov.uk.

    Without a date the site serves the latest revised text (the law as amended, possibly with
    effects not yet applied); '/YYYY-MM-DD' is that text on a date; '/enacted' or '/made' is the
    text as first published. Returns None when no identifier is recognised.
    """
    candidates = []
    for value in (url, identifier):
        if value and "://" in value:
            parts = urlsplit(value)
            if parts.hostname in UK.hosts or parts.hostname == "legislation.gov.uk":
                candidates.append(parts.path)  # the site's own URIs: http://www.legislation.gov.uk/id/...
    if identifier and "://" not in identifier:
        candidates.append(identifier)
    for candidate in candidates:
        segments = [segment for segment in candidate.strip().strip("/").split("/") if segment]
        if segments[:1] == ["id"]:
            segments = segments[1:]
        if len(segments) < 3 or segments[0] not in UK_TYPES or not (segments[1].isascii() and segments[1].isdigit()
                                                                    and len(segments[1]) == 4):
            continue
        if not (segments[2].isascii() and segments[2].isdigit()):
            continue
        rest = segments[3:]
        first_published = any(segment in ("enacted", "made", "adopted") for segment in rest)
        date = next((segment for segment in rest if _date(segment)), None)
        return {"jurisdiction": "UK", "id": "/".join(segments[:3]), "consolidated": not first_published, "date": date}
    return None


def version(identifier: str | None, url: str | None = None) -> dict | None:
    """The act version a target names, in any jurisdiction: {"jurisdiction", "id", "consolidated", "date"}."""
    from .sources import celex_version
    found = celex_version(identifier, url)
    if found:
        return {"jurisdiction": "EU", "id": found["celex"], **found}
    return uk_version(identifier, url)


def version_note(found: dict | None) -> str:
    """How far a retained text can be relied on as the law in force, in one sentence."""
    if found is None:
        return "check the official consolidated version before relying on it."
    if "jurisdiction" not in found:  # a bare CELEX result
        found = {"jurisdiction": "EU", "id": found["celex"], **found}
    if found["jurisdiction"] == "UK":
        if not found["consolidated"]:
            return f"the text as first published ({found['id']}), not the law in force; check the revised version."
        if found["date"]:
            return f"the revised text as on {found['date']} ({found['id']}); check that no later change applies."
        return (f"the latest revised text on legislation.gov.uk ({found['id']}), which may list changes not yet "
                "applied; check its status note.")
    if found["consolidated"]:
        return f"consolidated version of {found['date']} (CELEX {found['id']}); check that no newer one applies."
    return f"the act as first published (base CELEX {found['id']}), not the law in force; check the consolidated version."
