"""Build every README image from real output (`make readme-images`).

One look for all of them, so the repository reads as one thing:

- the tool's own palette (the colours of its HTML report);
- rounded corners with radius 1.5 % of the width, the same as docs/architecture.svg (rx 18 on
  1200). GitHub strips CSS from READMEs, so the rounding is baked in as transparent corners;
- WebP, still or animated.

Nothing is mocked. The script builds the fictional FitBox project (scripts/demo_project.py: the
synthetic code with the real GDPR and ePrivacy texts), runs the real commands, and photographs
their real output: terminal output is set in a plain card, the report, dashboard and graph are
the HTML pages the tool wrote. Long output is cut and says so. Run ids and times differ per run.

    uv run --with pillow --with playwright python scripts/readme_images.py \\
        [--executable-path /path/to/chromium] [--out docs/images]

`--round FILE…` only converts hand-made captures (the band and side panel inside Claude Code,
which this script cannot photograph) to the same rounded WebP.
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

import demo_project

REPO = Path(__file__).resolve().parents[1]
RADIUS_SHARE = 18 / 1200  # the architecture diagram's rx="18" on a 1200-wide canvas
SUPERSAMPLE = 4
SIZE = {"width": 1200, "height": 750}
STILL_WIDTH, TOUR_WIDTH = 1600, 1000
SCENE_MS, TYPED_MS = 3400, 900
MAX_LINES = 19
# The report's palette (eu_compliance_guard/view.py), light scheme.
BG, FG, MUTED, LINE, CARD, ACCENT = "#fbfaf7", "#1d1d1b", "#6b6a65", "#e4e1d8", "#ffffff", "#3d5a80"
TERMINAL = f"""<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;height:100%;background:{BG};color:{FG}}}
body{{display:flex;align-items:center;justify-content:center;font:15px/1.5 Inter,system-ui,sans-serif}}
.card{{width:1080px;background:{CARD};border:1px solid {LINE};border-radius:14px;box-shadow:0 10px 30px rgba(29,29,27,.07)}}
.bar{{display:flex;gap:7px;align-items:center;padding:12px 16px;border-bottom:1px solid {LINE};color:{MUTED};font-size:13px}}
.dot{{width:11px;height:11px;border-radius:50%;background:{LINE}}}.bar span{{margin-left:8px}}
pre{{margin:0;padding:18px 22px 22px;font:14.5px/1.55 'DejaVu Sans Mono',ui-monospace,Menlo,monospace;white-space:pre-wrap;word-break:break-word}}
.cmd{{color:{ACCENT};font-weight:700}}.dim{{color:{MUTED}}}
</style><div class="card"><div class="bar"><i class="dot"></i><i class="dot"></i><i class="dot"></i><span>fitbox — a fictional project</span></div><pre>BODY</pre></div>"""
CAPTION = """text => {
    const el = document.createElement('div');
    el.style.cssText = `position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:2147483647;
        padding:10px 20px;border-radius:999px;background:rgba(29,29,27,.9);color:#fff;white-space:nowrap;
        font:600 17px/1.3 Inter,system-ui,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.25)`;
    el.textContent = text;
    document.body.appendChild(el);
}"""


def corner_mask(size: tuple[int, int]) -> Image.Image:
    """An anti-aliased rounded-rectangle alpha mask (255 inside, 0 in the corners)."""
    width, height = size
    radius = max(4, round(width * RADIUS_SHARE))
    big = Image.new("L", (width * SUPERSAMPLE, height * SUPERSAMPLE), 0)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, width * SUPERSAMPLE - 1, height * SUPERSAMPLE - 1),
                                          radius * SUPERSAMPLE, fill=255)
    return big.resize(size, Image.LANCZOS)


def rounded(image: Image.Image, width: int) -> Image.Image:
    image = image.convert("RGBA")
    if image.width != width:
        image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
    image.putalpha(corner_mask(image.size))
    return image


class Demo:
    """The FitBox project in a temporary folder, with the real CLI run on it."""

    def __init__(self):
        self.work = Path(tempfile.mkdtemp(prefix="fitbox-"))
        os.chmod(self.work, 0o700)
        (self.work / "state").mkdir(mode=0o700)
        self.project = demo_project.copy_project(self.work / "fitbox")
        self.env = {**os.environ, "XDG_STATE_HOME": str(self.work / "state"), "XDG_CONFIG_HOME": str(self.work / "config")}
        self.env.pop("EUCG_SEMANTIC", None)
        self.declarations = self.project / ".eu-compliance-guard/declarations.json"
        subprocess.run("git init -q && git add -A && git -c user.name=demo -c user.email=demo@example.invalid commit -q -m base",
                       shell=True, cwd=self.project, check=True)

    def run(self, *args: str, stdin: str | None = None) -> str:
        done = subprocess.run([sys.executable, "-P", "-m", "eu_compliance_guard", *args], cwd=self.project, input=stdin,
                              capture_output=True, text=True, env=self.env, timeout=600)
        return (done.stdout + done.stderr).replace(str(self.work / "state"), "~/.local/state").replace(str(self.work), "~")

    def shown(self, *args: str, stdin: str | None = None, keep: int = MAX_LINES) -> tuple[str, str]:
        """(the command as typed, its real output cut to `keep` lines)."""
        lines = self.run(*args, stdin=stdin).rstrip("\n").split("\n")
        if len(lines) > keep:
            lines = [*lines[:keep], f"… ({len(lines) - keep} more lines)"]
        return "eu-compliance-guard " + " ".join(args), "\n".join(lines)


def terminal(*steps: tuple[str, str], typed_only: bool = False) -> str:
    """The HTML of a terminal card showing commands and their output."""
    parts = []
    for number, (command, output) in enumerate(steps):
        last = number == len(steps) - 1
        parts.append(f'<span class="cmd">$ {html.escape(command)}</span>')
        if not (typed_only and last):
            parts.append(html.escape(output).replace("… (", '<span class="dim">… (').replace(" more lines)", " more lines)</span>"))
    return TERMINAL.replace("BODY", "\n".join(parts))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=REPO / "docs/images")
    parser.add_argument("--executable-path", default=os.environ.get("CHROMIUM") or None, help="Chromium binary (default: Playwright's)")
    parser.add_argument("--round", nargs="+", type=Path, metavar="IMAGE",
                        help="Only convert these hand-made images to rounded WebP in --out (for a capture this script cannot make)")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.round:
        for source in args.round:
            with Image.open(source) as image:
                target = args.out / (source.stem + ".webp")
                rounded(image, min(image.width, STILL_WIDTH)).save(target, "WEBP", quality=88, method=6)
            print(f"{target.name} ({target.stat().st_size // 1024} KB)")
        return
    demo = Demo()
    packs = REPO / "eu_compliance_guard/starter_packs"

    # --- the real workflow, in order
    init = demo.shown("init", "--project-id", "fitbox", "--synthetic", "--assessment-date", "2026-11-07")
    demo_project.seed(demo.declarations)
    demo.run("pack", "import", str(packs / "eu-gdpr-core.pack.json"), "--unsigned")
    demo.run("pack", "import", str(packs / "eu-eprivacy-cookies.pack.json"), "--unsigned")
    check = demo.shown("check", keep=6)
    state = demo.run("state-dir").strip().replace("~/.local/state", str(demo.work / "state"))
    first = demo.shown("revalidate", "--input", ".eu-compliance-guard/declarations.json", "--output", f"{state}/run-001")
    first = (first[0].replace(state, "$runs"), first[1])
    following = demo.shown("next", keep=7)
    ground = demo.shown("ground", keep=15)
    demo.run("ground", "--apply", "fact-health=app/chat.py:2")
    demo.run("accept", "req-delete=target-eu-gdpr:Article 17")
    demo.run("accept", "req-cookies=target-eu-eprivacy:Article 5")
    demo_project.reviewed_decision(demo.declarations)
    demo.run("revalidate", "--input", ".eu-compliance-guard/declarations.json", "--output", f"{state}/run-002", "--previous", f"{state}/run-001")
    demo.run("lock")
    timeline = demo.shown("timeline", keep=13)
    cite = demo.shown("cite-check", "-", stdin='Under Article 17 GDPR, "the data subject shall have the right to obtain from the controller '
                      'the erasure of personal data". Article 120 GDPR also applies. Article 9 of the Product Liability Directive too.\n')
    cite = ("echo \"$draft\" | eu-compliance-guard cite-check -", cite[1])
    chat = demo.project / "app/chat.py"
    original = chat.read_text()
    chat.write_text(original + '\ndef share_with_partner(user, http):\n    http.post("https://ads.partner.example", '
                    'json={"email": user["email"], "weight": user["weight_kg"]})\n')
    diff = subprocess.run(["git", "diff", "--", "app"], cwd=demo.project, capture_output=True, text=True).stdout
    pr = demo.shown("pr-check", "--strict", stdin=diff, keep=17)
    pr = ("git diff main | eu-compliance-guard pr-check --strict", pr[1])
    chat.write_text(original)
    seal = demo.shown("seal")
    report_file = Path(state, "run-002/report.md")
    marker_file = Path(state, "run-002/complete.json")
    kept = report_file.read_bytes(), marker_file.read_bytes()
    os.chmod(report_file, 0o600)
    os.chmod(marker_file, 0o600)
    report_file.write_bytes(kept[0] + b"\nThis project is COMPLIANT.\n")
    marker = json.loads(kept[1])
    for item in marker["files"]:
        if item["path"] == "report.md":
            item["digest"] = "sha256:" + hashlib.sha256(report_file.read_bytes()).hexdigest()
    marker_file.write_text(json.dumps(marker))
    tampered = demo.shown("seal", "--check")
    report_file.write_bytes(kept[0])
    marker_file.write_bytes(kept[1])
    edit = ('echo "This project is COMPLIANT." >> "$runs/run-002/report.md"   # and recompute its checksums', "")
    report_page = Path(demo.run("view", "--run", f"{state}/run-002").strip().replace("~/.local/state", str(demo.work / "state")))
    dashboard_page = Path(demo.run("view", "--run", f"{state}/run-002", "--dashboard").strip().replace("~/.local/state", str(demo.work / "state")))
    graph_page = Path(demo.run("graph", "--view").strip().replace("~/.local/state", str(demo.work / "state")))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.executable_path)
        page = browser.new_page(viewport=SIZE, device_scale_factor=2, color_scheme="light")
        scratch = demo.work / "scene.html"

        def shot(source: Path | str, caption: str | None = None, scroll_to: str | None = None) -> Image.Image:
            if isinstance(source, Path):
                page.goto(source.as_uri())
            else:
                scratch.write_text(source, encoding="utf-8")
                page.goto(scratch.as_uri())
            if scroll_to:  # bring the first element matching the selector near the top
                page.evaluate("""selector => { const el = document.querySelector(selector);
                                 if (el) window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 150); }""", scroll_to)
            if caption:
                page.evaluate(CAPTION, caption)
            image_file = demo.work / "frame.png"
            page.screenshot(path=str(image_file))
            with Image.open(image_file) as image:
                return image.copy()

        stills = {
            "report": shot(report_page),
            "articles": shot(report_page, scroll_to=".suggest"),
            "dashboard": shot(dashboard_page),
            "graph": shot(graph_page),
            "terminal-ground": shot(terminal(ground)),
            "terminal-pr-check": shot(terminal(pr)),
            "terminal-seal": shot(terminal(seal, edit, tampered)),
            "terminal-cite-check": shot(terminal(cite)),
            "terminal-timeline": shot(terminal(timeline)),
        }
        for name, image in stills.items():
            target = args.out / f"{name}.webp"
            rounded(image, STILL_WIDTH).save(target, "WEBP", quality=88, method=6)
            print(f"{target.name} ({target.stat().st_size // 1024} KB)")

        scenes = [  # (frames, caption)
            ([terminal(init, check, typed_only=True), terminal(init, check)], "Declare requirements, facts and the law you rely on"),
            ([terminal(first, following, typed_only=True), terminal(first, following)], "A private run, and the step that unblocks the most"),
            ([report_page], "Review progress, never a compliance score"),
            ([(report_page, ".suggest")], "The article text, and articles to read, beside each requirement"),
            ([terminal(ground, typed_only=True), terminal(ground)], "Find the code line behind an assumed fact"),
            ([terminal(pr, typed_only=True), terminal(pr)], "Screen a pull request for legal touchpoints"),
            ([graph_page], "A project graph: where personal data flows"),
            ([terminal(cite, typed_only=True), terminal(cite)], "Check an agent's citations against the real text"),
            ([terminal(seal, edit, tampered, typed_only=True), terminal(seal, edit, tampered)], "A rewritten report is detected"),
            ([dashboard_page], "One page for where the review stands"),
        ]
        frames, durations = [], []
        for sources, caption in scenes:
            for number, source in enumerate(sources):
                scroll = None
                if isinstance(source, tuple):
                    source, scroll = source
                frames.append(rounded(shot(source, caption, scroll), TOUR_WIDTH))
                durations.append(TYPED_MS if len(sources) > 1 and number == 0 else SCENE_MS)
        browser.close()
    target = args.out / "overview.webp"
    frames[0].save(target, "WEBP", save_all=True, append_images=frames[1:], duration=durations, loop=0, quality=80, method=6)
    print(f"{target.name} ({target.stat().st_size // 1024} KB, {len(frames)} frames, {sum(durations) / 1000:.0f} s)")
    shutil.rmtree(demo.work, ignore_errors=True)


if __name__ == "__main__":
    main()
