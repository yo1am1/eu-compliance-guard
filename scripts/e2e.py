"""End-to-end test (`make e2e`): every command, driven from outside like a user would.

It builds a fresh fictional project in a temporary folder (the synthetic code of
fixtures/eval/project, with the real GDPR and ePrivacy texts of fixtures/official as its declared
sources) and runs each command, checking exit codes, output, files and the legal notice.
Offline by default. `--live` also fetches both acts from the Publications Office and expects
them confirmed as current. Needs git and ssh-keygen (for a real diff and real signatures).
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import demo_project

REPO = Path(__file__).resolve().parents[1]
WORK = Path(tempfile.mkdtemp(prefix="eucg-e2e-"))
PY = sys.executable
ENV = {**os.environ, "XDG_STATE_HOME": str(WORK / "state"), "XDG_CONFIG_HOME": str(WORK / "config")}
ENV.pop("EUCG_SEMANTIC", None)
for tool in ("git", "ssh-keygen"):
    if shutil.which(tool) is None:
        sys.exit(f"e2e needs {tool}")
CITED = ('Under Article 17 GDPR, "the data subject shall have the right to obtain from the controller the erasure of personal data".\n'
         "Article 5(3) of the ePrivacy Directive requires consent for cookies.\n"
         "Article 120 GDPR does not exist. Article 6 DSA is a different act.\n")
NOTICE = "see LICENSE and NOTICE."
results = []


def run(*args, cwd=None, stdin=None, env=None):
    done = subprocess.run([PY, "-P", "-m", "eu_compliance_guard", *map(str, args)], cwd=cwd or PROJ, input=stdin,
                          capture_output=True, text=True, env=env or ENV, timeout=600)
    return done.returncode, done.stdout, done.stderr


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"\n      {str(detail)[:600]}"))


def expect(name, result, code=0, has=(), lacks=(), notice=None):
    rc, out, err = result
    text = out + err
    ok = rc == code and all(h in text for h in has) and not any(l in text for l in lacks)
    if notice:
        ok = ok and out.rstrip().endswith(NOTICE)
    check(name, ok, f"exit {rc}: {text[-500:]}")
    return out


PROJ = WORK / "proj"
(WORK / "state").mkdir(mode=0o700)
os.chmod(WORK, 0o700)
demo_project.copy_project(PROJ)
subprocess.run("git init -q && git add -A && git -c user.name=t -c user.email=t@example.invalid commit -q -m base", shell=True, cwd=PROJ, check=True)
DECL = PROJ / ".eu-compliance-guard/declarations.json"

# --- basics
expect("version", run("--version"), has=["eu-compliance-guard 2."])
expect("help lists seal and semantic", run("--help"), has=["seal", "semantic", "timeline"])
expect("bad arguments give a fixed code, no echo", run("nope", "--secret-value"), code=2, has=["invalid-arguments"], lacks=["secret-value"])
expect("init", run("init", "--project-id", "fitbox", "--synthetic", "--assessment-date", "2026-11-07"), has=["declarations.json"], notice=True)
expect("init never overwrites", run("init", "--project-id", "fitbox"), code=2)
expect("check on the starter file", run("check"), has=["declarations: valid"], notice=True)
demo_project.seed(DECL)
expect("check with requirements, facts and two real acts", run("check"), has=["declarations: valid"])
state = expect("state-dir", run("state-dir")).strip()
check("state-dir is private", os.stat(state).st_mode & 0o777 == 0o700)

# --- packs: starters into the project
starters = expect("pack starters", run("pack", "starters"), has=["pack-eu-gdpr-core", "reviewed by no one"], notice=True)
PACKS = REPO / "eu_compliance_guard/starter_packs"
expect("pack import refuses without --unsigned or signers", run("pack", "import", PACKS / "eu-gdpr-core.pack.json"), code=2)
expect("pack import gdpr core", run("pack", "import", PACKS / "eu-gdpr-core.pack.json", "--unsigned"), has=["13"])
expect("pack import eprivacy", run("pack", "import", PACKS / "eu-eprivacy-cookies.pack.json", "--unsigned"))
expect("check after imports", run("check"), has=["declarations: valid"])

# --- first run and its views
R1 = f"{state}/run-001"
expect("revalidate offline", run("revalidate", "--input", DECL, "--output", R1, "--offline"), has=["not a compliance verdict"], notice=True)
expect("revalidate refuses an existing output", run("revalidate", "--input", DECL, "--output", R1), code=2, has=["output-exists"])
report = Path(R1, "report.md").read_text()
check("report ends with the legal notice and never says compliant", report.rstrip().endswith(NOTICE) and "is compliant" not in report.lower())
check("run files are private", all(os.stat(p).st_mode & 0o077 == 0 for p in Path(R1).iterdir()))
out = expect("next", run("next"), has=["1."], notice=True)
score = json.loads(expect("score --json", run("score", "--json")))
check("score has separate meters and no total", {"alignment", "law_text", "facts"} <= {m["key"] for m in score["scorecard"]["dimensions"]} and "total" not in score["scorecard"])
view = expect("view", run("view", "--run", R1)).strip()
html = Path(view).read_text()
check("view: no script, escaped, notice, article text and suggestions", "<script" not in html and NOTICE in html and "Articles to read" in html and "Text search suggestion" in html)
dash = expect("view --dashboard", run("view", "--run", R1, "--dashboard")).strip()
check("dashboard written, private", Path(dash).is_file() and os.stat(dash).st_mode & 0o077 == 0)

# --- grounding
ground = json.loads(expect("ground --json", run("ground", "--json")))
locations = [c["location"] for f in ground["facts"] for c in f["candidates"]]
check("ground finds code and never offers the law text", any(l.startswith("app/chat.py") for l in locations) and not any(l.startswith("law/") for l in locations), locations)
expect("ground text", run("ground"), notice=True)
expect("ground --apply refuses the law text", run("ground", "--apply", "fact-cookies=law/eprivacy.html:65"), code=2, has=["bad-location"])
expect("ground --apply refuses an unrelated line", run("ground", "--apply", "fact-health=app/billing.py:1"), code=2, has=["unrelated-line"])
expect("ground --apply pins a fact", run("ground", "--apply", "fact-health=app/chat.py:2"), has=["observed, pinned to app/chat.py:2"])
expect("check after grounding", run("check", "--previous", R1), has=["declarations: valid"])

# --- accept
expect("accept refuses an article the act does not have", run("accept", "req-delete=target-eu-gdpr:Article 999"), code=2, has=["unknown-article"])
expect("accept maps a requirement", run("accept", "req-delete=target-eu-gdpr:Article 17"), has=["req-delete now maps to obligation-gdpr-erasure", "existing candidate obligation"], lacks=["not checked"], notice=True)
expect("accept is idempotent", run("accept", "req-delete=target-eu-gdpr:Article 17"), has=["nothing changed"])
expect("accept: cookies", run("accept", "req-cookies=target-eu-eprivacy:Article 5"))

# --- a reviewed decision
demo_project.reviewed_decision(DECL)
expect("check with a reviewed decision", run("check"), has=["declarations: valid"])
R2 = f"{state}/run-002"
expect("revalidate with a predecessor", run("revalidate", "--input", DECL, "--output", R2, "--previous", R1))
expect("score against the previous run", run("score", "--against", R1), notice=True)

# --- law lock, impact, timeline, citations
expect("lock", run("lock"), has=["2 act(s)", "locked from run"])
expect("impact: nothing changed", run("impact", "--strict"), has=["No locked article changed"])
timeline = expect("timeline", run("timeline"), has=["2018-05-25", "2003-10-31", "not reflected unless that version includes it"], lacks=["2002-03-07"], notice=True)
cite = expect("cite-check finds the wrong citations", run("cite-check", "-", stdin=CITED), code=1,
              has=["Article 17 of target-eu-gdpr: exists", "Article 120 of target-eu-gdpr: NOT FOUND", "NOT CHECKED"], notice=True)
expect("cite-check passes correct text", run("cite-check", "-", stdin='Article 17 GDPR: "the right to obtain from the controller the erasure of personal data".'), has=["verbatim"])
expect("cite-check: an unknown act is not checked against another", run("cite-check", "-", stdin="Article 9 of the Product Liability Directive applies."), code=1, has=["does not recognise"])

# --- signing
subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "fictional", "-f", str(WORK / "key")], check=True)
(WORK / "allowed").write_text("reviewer@example.invalid " + (WORK / "key.pub").read_text())
expect("sign a reviewed decision", run("sign", "--decision", "decision-erasure", "--key", WORK / "key", "--principal", "reviewer@example.invalid"), has=["signed by"], lacks=["No eu-law.lock"])
expect("sign refuses an unknown decision", run("sign", "--decision", "nope", "--key", WORK / "key", "--principal", "r@example.invalid"), code=2, has=["unknown-id"])
expect("verify", run("verify", "--allowed-signers", WORK / "allowed"), has=["decision, law and evidence unchanged"], notice=True)
tampered = json.loads(DECL.read_text())
tampered["applicability_decisions"][0]["rationale"] = "Edited after signing."
backup = DECL.read_text()
DECL.write_text(json.dumps(tampered, indent=2))
expect("verify reports a decision changed after signing", run("verify", "--allowed-signers", WORK / "allowed"), code=1, has=["changed: decision"])
DECL.write_text(backup)

# --- sealed runs
expect("seal the newest run", run("seal"), has=["sealed as entry 1", "Commit runs.log"], notice=True)
expect("seal the older run, signed", run("seal", "--run", R1, "--key", WORK / "key", "--principal", "reviewer@example.invalid"), has=["entry 2, signed"])
expect("seal again changes nothing", run("seal"), has=["was already sealed"])
expect("seal --check", run("seal", "--check", "--allowed-signers", WORK / "allowed"), has=["run intact", "signature of reviewer@example.invalid valid"], lacks=["CHANGED", "BROKEN"])
report_file = Path(R2, "report.md")
original_report, marker_file = report_file.read_bytes(), Path(R2, "complete.json")
original_marker = marker_file.read_bytes()
os.chmod(report_file, 0o600)
os.chmod(marker_file, 0o600)
report_file.write_bytes(original_report + b"\nThis project is COMPLIANT.\n")
marker = json.loads(original_marker)
for item in marker["files"]:
    if item["path"] == "report.md":
        item["digest"] = "sha256:" + hashlib.sha256(report_file.read_bytes()).hexdigest()
marker_file.write_text(json.dumps(marker))
expect("a rewritten report with recomputed checksums still passes the run's own check", run("view", "--run", R2))
expect("...but seal --check reports it changed", run("seal", "--check"), code=1, has=["CHANGED since it was sealed"])
report_file.write_bytes(original_report)
marker_file.write_bytes(original_marker)
expect("seal --check is clean again after restoring", run("seal", "--check"), lacks=["CHANGED"])

# --- graph and pr-check
graph = json.loads(expect("graph --json", run("graph", "--json")))
check("graph has nodes, edges and no omissions", len(graph["nodes"]) > 5 and graph["edges"] and graph["omitted_edges"] == 0)
expect("graph text", run("graph"), has=["Python and Rust files parsed"], notice=True)
page = expect("graph --view", run("graph", "--view")).strip()
check("graph page has no script", "<script" not in Path(page).read_text())
RUST = WORK / "rust"
shutil.copytree(REPO / "fixtures/eval/graph-project-rust", RUST)
expect("init for the Rust crate", run("init", "--project-id", "crate", "--synthetic", cwd=RUST))
rust = json.loads(expect("graph on a Rust crate", run("graph", "--json", cwd=RUST)))
check("Rust functions and calls are found", any(n["path"].endswith(".rs") and n["kind"] == "function" for n in rust["nodes"]) and any(e["kind"] == "calls" for e in rust["edges"]))
(PROJ / "app/chat.py").write_text((PROJ / "app/chat.py").read_text() + '\ndef share_with_partner(user, http):\n    http.post("https://ads.partner.example", json={"email": user["email"], "weight": user["weight_kg"]})\n')
diff = subprocess.run(["git", "diff", "--", "app"], cwd=PROJ, capture_output=True, text=True).stdout
pr = expect("pr-check --strict flags health data sent to a web address", run("pr-check", "--strict", "--json", stdin=diff), code=1)
concepts = {t["concept"] for t in json.loads(pr)["touchpoints"]}
check("pr-check concepts", {"special_category", "third_party", "personal_data"} <= concepts, concepts)
expect("pr-check --markdown", run("pr-check", "--markdown", stdin=diff), has=["<!-- eu-compliance-guard-pr-check -->", "not a legal conclusion"])
expect("pr-check refuses input that is no diff", run("pr-check", stdin="hello"), code=2)
stale = expect("ground lists the fact whose pinned file changed", run("ground"), has=["fact-health"])
subprocess.run(["git", "checkout", "-q", "--", "app/chat.py"], cwd=PROJ, check=True)

# --- exports and imports
expect("export ropa markdown", run("export", "ropa"), has=["Article 30", "DRAFT"], notice=True)
ropa = json.loads(expect("export ropa json", run("export", "ropa", "--format", "json")))
expect("export ropa csv", run("export", "ropa", "--format", "csv"))
dpia = json.loads(expect("export dpia json", run("export", "dpia", "--format", "json")))
check("dpia has 12 unanswered criteria", len(dpia["criteria"]) == 12 and all(c["answer"] is None for c in dpia["criteria"]))
expect("export dpia csv is refused", run("export", "dpia", "--format", "csv"), code=2, has=["invalid-input"])
expect("export to a file", run("export", "dpia", "--output", WORK / "dpia.md"), has=["draft dpia export written"])
expect("import-evidence sarif", run("import-evidence", REPO / "fixtures/imports/sarif-synthetic.json", "--kind", "sarif"), has=["untrusted tool output", "declarations were not changed"], notice=True)
expect("import-evidence wec", run("import-evidence", REPO / "fixtures/imports/wec-synthetic.json", "--kind", "wec"), has=["tracking"])
expect("import-evidence refuses the wrong kind", run("import-evidence", REPO / "fixtures/imports/sarif-synthetic.json", "--kind", "wec"), code=2)
check("imports are owner-only", all(os.stat(p).st_mode & 0o077 == 0 for p in (PROJ / ".eu-compliance-guard/imports").iterdir()))

# --- packs: build, sign, verify, import elsewhere
PACK = WORK / "fitbox.pack.json"
expect("pack build", run("pack", "build", "--id", "pack-fitbox", "--title", "Fitbox", "--obligation", "obligation-gdpr-erasure", "--output", PACK), has=["1 obligation(s)"])
expect("pack sign", run("pack", "sign", PACK, "--key", WORK / "key", "--principal", "reviewer@example.invalid"))
expect("pack verify", run("pack", "verify", PACK, "--allowed-signers", WORK / "allowed"), has=["valid"])
PACK.write_text(PACK.read_text().replace("Fitbox", "Fitbox!"))
expect("pack verify fails after an edit", run("pack", "verify", PACK, "--allowed-signers", WORK / "allowed"), code=1)
PACK.write_text(PACK.read_text().replace("Fitbox!", "Fitbox"))
OTHER = WORK / "other"
OTHER.mkdir()
expect("init a second project", run("init", "--project-id", "other", "--synthetic", cwd=OTHER))
expect("import a signed pack into another project", run("pack", "import", PACK, "--allowed-signers", WORK / "allowed", cwd=OTHER), has=["obligation-gdpr-erasure"])
expect("the second project still validates", run("check", cwd=OTHER), has=["declarations: valid"])

# --- determinism: the same command twice gives the same bytes
for name, args in (("ground", ["ground", "--json"]), ("graph", ["graph", "--json"]), ("score", ["score", "--json"]), ("next", ["next", "--json"]),
                   ("timeline", ["timeline", "--json"]), ("export", ["export", "ropa"]), ("seal --check", ["seal", "--check", "--json"])):
    check(f"deterministic: {name}", run(*args)[1] == run(*args)[1])
view_a = Path(run("view", "--run", R2)[1].strip()).read_bytes()
check("deterministic: view", view_a == Path(run("view", "--run", R2)[1].strip()).read_bytes())

# --- semantic: off by default
expect("semantic status says off", run("semantic", "status"), has=["Semantic search: off"], notice=True)

# --- MCP over stdio
proc = subprocess.Popen([PY, "-P", "-m", "eu_compliance_guard", "mcp"], cwd=PROJ, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=ENV)
counter = 0
def rpc(method, params=None, reply=True):
    global counter
    counter += 1
    message = {"jsonrpc": "2.0", "method": method, **({"id": counter} if reply else {}), **({"params": params} if params is not None else {})}
    proc.stdin.write(json.dumps(message) + "\n"); proc.stdin.flush()
    return json.loads(proc.stdout.readline()) if reply else None
init = rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "e2e", "version": "0"}})
rpc("notifications/initialized", reply=False)
tools = [t["name"] for t in rpc("tools/list")["result"]["tools"]]
check("mcp lists six tools", tools == ["cite_check", "article_search", "ground", "pr_check", "timeline", "next_steps"], tools)
arguments = {"cite_check": {"text": "Article 17 GDPR and Article 120 GDPR."}, "article_search": {"query": "right to erasure of personal data", "top": 3},
             "ground": {"top": 2}, "pr_check": {"diff": diff}, "timeline": {}, "next_steps": {"top": 2}}
for tool in tools:
    answer = rpc("tools/call", {"name": tool, "arguments": arguments[tool]}).get("result", {})
    text = answer.get("content", [{}])[0].get("text", "")
    check(f"mcp {tool}: answers, structured, ends with the notice", not answer.get("isError") and "structuredContent" in answer and text.rstrip().endswith(NOTICE), text[-300:])
    if tool == "article_search":
        check("mcp article_search finds Article 17 by word match", "Article 17" in text and "word match" in text, text)
unknown = rpc("tools/call", {"name": "nope", "arguments": {}})
check("mcp refuses an unknown tool with an error result", unknown.get("result", {}).get("isError"), unknown)
bad = rpc("tools/call", {"name": "ground", "arguments": {"top": 99}})
check("mcp bad arguments are an error result", "error" in bad or bad.get("result", {}).get("isError"), bad)
proc.stdin.write("{not json\n"); proc.stdin.flush()
check("mcp survives a malformed line", "error" in json.loads(proc.stdout.readline()))
check("mcp still answers afterwards", "result" in rpc("tools/list"))
proc.stdin.close(); proc.wait(timeout=10)
check("mcp exits cleanly", proc.returncode == 0, proc.stderr.read()[:300])

# --- live: official retrieval confirms freshness
if "--live" in sys.argv:
    R3 = f"{state}/run-003"
    rc, out, err = run("revalidate", "--input", DECL, "--output", R3, "--previous", R2, "--fetch-official")
    check("revalidate --fetch-official runs", rc == 0, err)
    if rc == 0:
        bundle = json.loads(Path(R3, "bundle.json").read_text())
        attempts = {a["source_target_id"]: (a["state"], a["retrieval"]["comparison"]) for a in bundle["source_attempts"]}
        check("both acts retrieved from the Publications Office, same bytes", all(v == ("retrieved", "same_bytes") for v in attempts.values()) and len(attempts) == 2, attempts)
        gaps = " ".join(bundle["gaps"])
        check("no 'did not confirm the declared bytes' and no identifier gap", "did not confirm the declared bytes" not in gaps and "intended-identifier-not-found" not in gaps, [g for g in bundle["gaps"] if "retriev" in g][:4])
        expect("impact after the live run: law unchanged", run("impact", "--run", R3, "--strict"), has=["No locked article changed"])

failed = [name for name, ok in results if not ok]
shutil.rmtree(WORK, ignore_errors=True)
print(f"\n{len(results) - len(failed)} of {len(results)} checks passed" + (f"; FAILED: {failed}" if failed else ""))
sys.exit(1 if failed else 0)
