"""Rank the next review steps of a verified run by how many open requirements each one unblocks.

A step is workflow guidance derived from recorded declarations and dispositions. Completing
one never establishes compliance; it only removes a recorded reason a requirement is open.
"""
from __future__ import annotations

from pathlib import Path

from . import models as m
from .grounding import NOT_OBSERVABLE

class NoRun(LookupError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


# Earlier kinds unblock later ones (facts feed decisions, reviewed text feeds provisions).
KINDS = ("retrieve", "fact", "source", "applicability", "mapping", "family")


def _step(kind: str, subject: str, unblocks: set[str], action: str, command: str | None = None) -> dict:
    return {"kind": kind, "subject": subject, "unblocks": len(unblocks), "requirements": sorted(unblocks),
            "action": action, "command": command}


def next_steps(bundle: m.RevalidationBundle, top: int = 3) -> list[dict]:
    declared = bundle.declarations
    open_requirements = {item.requirement.id for item in bundle.requirement_assessments if item.state != "supported"}
    requirements = [item for item in declared.requirements if item.id in open_requirements]
    by_obligation: dict[str, set[str]] = {}
    for requirement in requirements:
        for ref in requirement.obligation_refs:
            by_obligation.setdefault(ref.id, set()).add(requirement.id)
    decisions = {item.obligation.id: item for item in bundle.effective_applicability_decisions}
    obligations = {item.id: item for item in declared.obligations}
    steps = []

    selected_targets = {item.target_id for item in declared.sources}
    unselected = [target for target in declared.source_targets if target.id not in selected_targets]

    def citing(target_id: str) -> set[str]:
        return {requirement for obligation, mapped in by_obligation.items() if obligation in obligations
                and any(pin.source_target_id == target_id for pin in obligations[obligation].source_provisions)
                for requirement in mapped}

    retrieved = {item.source_target_id for item in bundle.source_attempts if item.retrieved_source}
    missing = [target for target in unselected if target.id not in retrieved]
    if missing:
        unblocks = set().union(*(citing(target.id) for target in missing))
        steps.append(_step("retrieve", "", unblocks,
                           f"Retrieve the official text of {len(missing)} declared source target(s) so provisions can be read.",
                           "eu-compliance-guard revalidate --fetch-official --input <declarations> --output <new run>"))
    for target in unselected:
        if target.id in retrieved:
            steps.append(_step("source", target.id, citing(target.id),
                               f"Read the retrieved text of {target.id}, then select it as a source with an accountable review."))

    relied: dict[str, set[str]] = {}
    for requirement in requirements:
        for ref in requirement.fact_refs:
            relied.setdefault(ref.id, set()).add(requirement.id)
    for obligation, decision in decisions.items():
        for ref in decision.fact_refs:
            relied.setdefault(ref.id, set()).update(by_obligation.get(obligation, set()))
    for fact in m.scope_facts(declared.scope):
        if fact.basis in ("assumed", "unknown") or fact.conflicts:
            observable = not NOT_OBSERVABLE.search(fact.key)
            steps.append(_step("fact", fact.id, relied.get(fact.id, set()),
                               f"Confirm '{fact.key}' (now {fact.basis})"
                               + (": look for code evidence." if observable else f": ask {fact.owner or 'the project owner'}."),
                               "eu-compliance-guard ground" if observable else None))

    for obligation, mapped in sorted(by_obligation.items()):
        decision = decisions.get(obligation)
        if decision is not None and decision.applicability == "unresolved":
            pins = obligations[obligation].source_provisions if obligation in obligations else []
            where = ", ".join(pin.locator for pin in pins[:2])
            steps.append(_step("applicability", obligation, mapped,
                               f"Record whether {obligation} applies" + (f" after reading {where}." if where else ".")))

    for requirement in requirements:
        if not requirement.obligation_refs:
            steps.append(_step("mapping", requirement.id, {requirement.id},
                               f"Map {requirement.id} to a candidate obligation; the report lists articles to read."))

    unscreened = [item.family for item in bundle.family_screenings if item.applicability == "unresolved"]
    if unscreened:
        steps.append(_step("family", "", set(),
                           f"Screen {len(unscreened)} legal families (applicable, not applicable or out of scope)."))

    steps.sort(key=lambda step: (-step["unblocks"], KINDS.index(step["kind"]), step["subject"]))
    return steps[:top]


def format_steps(steps: list[dict]) -> str:
    if not steps:
        return "No recorded step is open. That is not a compliance conclusion."
    lines = []
    for number, step in enumerate(steps, 1):
        lines.append(f"{number}. {step['action']} Unblocks {step['unblocks']} open requirement(s).")
        if step["command"]:
            lines.append(f"   {step['command']}")
    lines.append("Workflow guidance from the recorded run; not a compliance verdict.")
    return "\n".join(lines)


def latest_run(state: str | Path) -> Path | None:
    """Newest run directory (by its timestamped name) that has a completion marker."""
    try:
        names = sorted((item for item in Path(state).iterdir()
                        if item.name.startswith("run-") and item.is_dir() and not item.is_symlink()), reverse=True)
    except OSError:
        return None
    return next((item for item in names if (item / "complete.json").is_file()), None)
