"""Is a newer consolidated version in force? (1.5 bolt 008, part two)

With `revalidate --fetch-official` only, each act target with a CELEX number gets one fixed
query to the Publications Office's official SPARQL endpoint, through the same bounded, pinned,
registry-checked retrieval as the act text. The query is built only from the parsed CELEX
number. The answer becomes a review gap; declarations are never changed.
"""
from __future__ import annotations

import csv
import io
from urllib.parse import urlencode

from . import models as m
from .sources import TargetRequest, celex_version

ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"
CSV = frozenset({"text/csv"})


def base_celex(version: dict) -> str:
    """The act's own CELEX number: '02016R0679-20160504' and '32016R0679' both give '32016R0679'."""
    number = version["celex"].partition("-")[0]
    return "3" + number[1:] if number[0] == "0" else number


def query_url(base: str) -> str:
    # `base` comes from celex_version, which admits only ASCII letters and digits here.
    query = ("PREFIX cdm: <http://publications.europa.eu/ontology/cdm#> "
             "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> "
             f'SELECT ?celex ?date WHERE {{ ?act cdm:resource_legal_id_celex "{base}"^^xsd:string . '
             "?cons cdm:act_consolidated_consolidates_resource_legal ?act . "
             "?cons cdm:resource_legal_id_celex ?celex . OPTIONAL { ?cons cdm:act_consolidated_date ?date } }")
    return ENDPOINT + "?" + urlencode({"query": query, "format": "text/csv"})


def requests(declared: m.RevalidationInput) -> list[tuple[m.SourceTarget, dict, TargetRequest]]:
    found = []
    for target in declared.source_targets:
        version = celex_version(target.intended_identifier, target.intended_url)
        if target.intended_type != "eu_act" or version is None:
            continue
        base = base_celex(version)
        if not (base.isascii() and base.isalnum()):
            continue
        found.append((target, version, TargetRequest(f"{target.id}-consolidation", query_url(base), media_types=CSV)))
    return found


def latest(content: bytes, base: str) -> tuple[str, str] | None:
    """The newest consolidation of this act alone: (CELEX, date). Other acts' rows are ignored."""
    prefix = "0" + base[1:] + "-"
    rows = []
    for row in csv.reader(io.StringIO(content.decode("utf-8", "replace"))):
        if len(row) >= 1 and row[0].startswith(prefix):
            version = celex_version(row[0])
            if version and version["consolidated"]:
                rows.append((version["date"], version["celex"]))
    return (max(rows)[1], max(rows)[0]) if rows else None


def notes(found: list[tuple[m.SourceTarget, dict, TargetRequest]], results: list) -> list[str]:
    """Review gaps: a newer consolidation, or an answer that could not be read. Never a change."""
    by_id = {item.target_id: item for item in results}
    gaps = []
    for target, version, request in found:
        result = by_id.get(request.target_id)
        if result is None or result.failure or result.content is None or result.status != 200:
            code = result.failure if result is not None and result.failure else "no-answer"
            gaps.append(f"Source target {target.id}: whether a newer consolidation exists could not be checked ({code}).")
            continue
        newest = latest(result.content, base_celex(version))
        if newest is None:
            continue
        celex, date = newest
        if not version["consolidated"]:
            gaps.append(f"Source target {target.id}: declared as first published; the latest consolidation is "
                        f"CELEX {celex} of {date}. Review it and declare the version in force.")
        elif date > version["date"]:
            gaps.append(f"Source target {target.id}: a newer consolidation exists (CELEX {celex} of {date}) than the "
                        f"declared one of {version['date']}. Review it and update the declaration.")
    return gaps
