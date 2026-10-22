"""Agents: planner, coder, reviewer, memory. Sab shared workspace folder ke
through baat karte hain (plan.md, tasks.md, messages.md, notes.md)."""
import os
import re

from . import llm

WORKSPACE = "workspace"
PROJECT = os.path.join(WORKSPACE, "project")


def _read(path, default=""):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return default


def _write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _append(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


def say(who, to, note):
    """messages.md me ek line: agents ki baat-chit ka visible record."""
    _append(os.path.join(WORKSPACE, "messages.md"), f"- **{who} -> {to}:** {note}\n")


def recent_messages(n=12):
    lines = _read(os.path.join(WORKSPACE, "messages.md")).strip().splitlines()
    return "\n".join(lines[-n:]) if lines else "(abhi koi message nahi)"


PLANNER_SYS = """You are PLANNER, the team lead of a small dev team. Your job: take the user's goal and break it into a short plan plus concrete tasks for the CODER.

Rules:
- Keep the plan realistic for a static website or a single-file browser game (HTML/CSS/JS only, no backend).
- Style guide (must follow): {style}
- Output format, exactly:
1. A short plan in markdown (goal, pages/sections, design direction, how to test).
2. Then a line with exactly: ===TASKS===
3. Then 3-8 checkbox tasks like: - [ ] task description
- All visible website text must be English. Your plan can be English too."""

CODER_SYS = """You are CODER. You receive a plan, a task list, and the team's shared messages. You write complete, working code.

Output format (exact, nothing else):
===FILE: index.html===
<full file content>
===END===
===FILE: style.css===
<full file content>
===END===

Rules:
- Every file must be COMPLETE and working. No placeholders, no "TODO", no lorem ipsum.
- Static site or browser game only: HTML, CSS, JS. No backend, no build step.
- All visible text in English only.
- Style guide (must follow): {style}
- Mobile-first: it must look good on a phone.
- If the tasks list contains FAIL items from the tester, fix exactly those.
- Do not reference external images; CSS gradients/shapes/emoji/SVG only. Google Fonts link is allowed."""

REVIEWER_SYS = """You are REVIEWER, a strict code reviewer. Read the file list and the tester report. Write a short review: what's broken or weak, and 2-5 concrete fixes. Be brief."""

MEMORY_SYS = """You are MEMORY, the team's notes keeper. Write a short dated entry for notes.md: goal, what was built, which files exist, test result, and the suggested next step. Keep it under 12 lines, simple English. Output ONLY the entry, nothing else."""


def run_planner(goal, cfg):
    msgs = [
        {"role": "system", "content": PLANNER_SYS.format(style=cfg["style_guide"])},
        {"role": "user", "content": f"User goal: {goal}"},
    ]
    out = llm.chat(cfg["models"]["planner"], cfg, msgs)
    if "===TASKS===" in out:
        plan, tasks = out.split("===TASKS===", 1)
    else:
        plan, tasks = out, "- [ ] Build the project files\n- [ ] Verify it opens in a browser\n"
    _write(os.path.join(WORKSPACE, "plan.md"), plan.strip() + "\n")
    _write(os.path.join(WORKSPACE, "tasks.md"), tasks.strip() + "\n")
    say("planner", "coder", "plan.md + tasks.md ready")
    return plan.strip()


FILE_RE = re.compile(r"===FILE:\s*([^\n=]+?)\s*===\n(.*?)\n?===END===", re.S)


def _safe_path(name):
    name = name.strip().replace("\\", "/").lstrip("/")
    if not name or ".." in name.split("/"):
        return None
    return os.path.join(PROJECT, *name.split("/"))


def run_coder(cfg, extra_context=""):
    plan = _read(os.path.join(WORKSPACE, "plan.md"))
    tasks = _read(os.path.join(WORKSPACE, "tasks.md"))
    user = (
        f"PLAN:\n{plan}\n\nTASKS:\n{tasks}\n\n"
        f"TEAM MESSAGES:\n{recent_messages()}\n"
    )
    if extra_context:
        user += f"\nEXTRA CONTEXT:\n{extra_context}\n"
    msgs = [
        {"role": "system", "content": CODER_SYS.format(style=cfg["style_guide"])},
        {"role": "user", "content": user},
    ]
    out = llm.chat(cfg["models"]["coder"], cfg, msgs, max_tokens=8000)
    files = FILE_RE.findall(out)
    if not files:
        raise llm.LLMError("Coder ne koi file block nahi diya (===FILE: format missing)")
    written = []
    for name, content in files:
        path = _safe_path(name)
        if not path:
            continue
        _write(path, content.rstrip() + "\n")
        written.append(os.path.relpath(path, PROJECT))
    say("coder", "tester", f"{len(written)} files likhi: {', '.join(written)}")
    return written


def run_reviewer(cfg, test_report):
    listing = []
    for root, _, files in os.walk(PROJECT):
        for fn in files:
            p = os.path.join(root, fn)
            listing.append(os.path.relpath(p, PROJECT) + f" ({os.path.getsize(p)} bytes)")
    user = (
        "FILES:\n" + ("\n".join(listing) or "(none)") +
        "\n\nTESTER REPORT:\n" + test_report +
        "\n\nTEAM MESSAGES:\n" + recent_messages()
    )
    msgs = [
        {"role": "system", "content": REVIEWER_SYS},
        {"role": "user", "content": user},
    ]
    out = llm.chat(cfg["models"]["reviewer"], cfg, msgs, max_tokens=1500)
    _write(os.path.join(WORKSPACE, "review.md"), out.strip() + "\n")
    say("reviewer", "coder", "review.md likha")
    return out.strip()


def run_memory(cfg, goal, result_line):
    old = _read(os.path.join(WORKSPACE, "notes.md"))
    user = (
        f"GOAL: {goal}\nRESULT: {result_line}\n"
        f"TEAM MESSAGES:\n{recent_messages(20)}\n\n"
        f"PREVIOUS NOTES (last part):\n{old[-1500:]}\n\nWrite the new dated entry."
    )
    msgs = [
        {"role": "system", "content": MEMORY_SYS},
        {"role": "user", "content": user},
    ]
    out = llm.chat(cfg["models"]["memory"], cfg, msgs, max_tokens=800)
    _append(os.path.join(WORKSPACE, "notes.md"), "\n" + out.strip() + "\n")
    say("memory", "team", "notes.md update ho gaya")
    return out.strip()


def fallback_notes(goal, result_line):
    from datetime import datetime
    entry = (
        f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"- Goal: {goal}\n- Result: {result_line}\n"
        f"- Files: workspace/project/ dekho\n"
    )
    _append(os.path.join(WORKSPACE, "notes.md"), entry)
