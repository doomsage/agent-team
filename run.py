#!/usr/bin/env python3
"""Agent Team - chhota multi-agent system (Groq cloud + Ollama local).

Use:
  python run.py "ek gym ki website banao"
  python run.py --check        (setup sahi hai ya nahi)
"""
import argparse
import json
import os
import sys

from crew import agents, llm, tester


def load_config():
    with open("config.json", encoding="utf-8") as f:
        return json.load(f)


def banner():
    print("=" * 52)
    print("  AGENT TEAM  (planner + coder + tester + memory)")
    print("=" * 52)


def cmd_check(cfg):
    ok = True
    print(f"Python: {sys.version.split()[0]}")
    key = os.environ.get("GROQ_API_KEY", "")
    if key and "yaha_apni_key" not in key:
        print("GROQ_API_KEY: set hai")
        try:
            models = llm.list_models("groq", cfg)
            want = {cfg["models"][r]["model"] for r in ("planner", "coder")}
            missing = want - set(models)
            if missing:
                ok = False
                print(f"Groq: connect hua, par ye models list me nahi: {missing}")
                print("  config.json me model naam update karo (console.groq.com/docs/models)")
            else:
                print(f"Groq: connect OK, models mil gaye: {sorted(want)}")
        except Exception as e:
            ok = False
            print(f"Groq: FAIL - {e}")
    else:
        ok = False
        print("GROQ_API_KEY: missing - .env file me key paste karo (console.groq.com/keys)")
    try:
        models = llm.list_models("ollama", cfg)
        print(f"Ollama: chal raha hai, {len(models)} model(s) installed")
        used = {cfg["models"][r]["model"] for r in cfg.get("agents_enabled", [])
                if r in cfg["models"] and cfg["models"][r]["provider"] == "ollama"}
        names = {m.split(":")[0] + ":" + (m.split(":")[1] if ":" in m else "latest") for m in models}
        for m in sorted(used):
            base = m.split(":")[0]
            if not any(n.startswith(base) for n in names):
                ok = False
                print(f"  Ollama model missing: {m}  ->  chalao: ollama pull {m}")
            else:
                print(f"  Ollama model OK: {m}")
    except Exception:
        print("Ollama: connect nahi hua (local agents ke liye chahiye; Groq-only kaam chalega)")
        print("  Install: https://ollama.com/download/windows  fir: ollama pull qwen2.5:3b")
    print("\nSETUP OK" if ok else "\nKuch cheezein baaki hain (upar dekho)")
    return 0 if ok else 1


def cmd_run(goal, cfg):
    enabled = cfg.get("agents_enabled", ["planner", "coder", "tester", "memory"])
    os.makedirs(agents.PROJECT, exist_ok=True)
    banner()
    print(f"GOAL: {goal}\n")

    if "planner" in enabled:
        print("[1] PLANNER (Groq) soch raha hai...")
        agents.run_planner(goal, cfg)
        print("    plan.md + tasks.md ready")

    rounds = int(cfg.get("max_fix_rounds", 2)) + 1
    failures = []
    for i in range(rounds):
        print(f"[2] CODER (Groq) code likh raha hai... (round {i + 1}/{rounds})")
        written = agents.run_coder(cfg)
        print(f"    {len(written)} files: {', '.join(written)}")

        print("[3] TESTER chala raha hai (asli checks, LLM nahi)...")
        failures = tester.run_tests()
        if not failures:
            print("    ALL PASS")
            break
        print(f"    {len(failures)} problem mili, tester ne report likhi")
        for f in failures[:5]:
            print(f"    - {f}")
        if i + 1 < rounds:
            report = open(tester.REPORT, encoding="utf-8").read()
            with open(os.path.join("workspace", "tasks.md"), "a", encoding="utf-8") as f:
                f.write("\n## TESTER FAILURES (fix these)\n")
                for line in failures:
                    f.write(f"- [ ] {line}\n")
            if "reviewer" in enabled:
                try:
                    print("[*] REVIEWER (Ollama) dekh raha hai...")
                    agents.run_reviewer(cfg, report)
                except llm.LLMError as e:
                    print(f"    reviewer skip: {e}")
            agents.say("tester", "coder", f"{len(failures)} fixes chahiye")
    result = "ALL TESTS PASS" if not failures else f"{len(failures)} tests fail (report dekho)"

    if "memory" in enabled:
        print("[4] MEMORY (Ollama) notes likh raha hai...")
        try:
            agents.run_memory(cfg, goal, result)
        except llm.LLMError as e:
            print(f"    Ollama nahi mila, basic notes likh raha hu ({e})")
            agents.fallback_notes(goal, result)

    print("\n" + "=" * 52)
    print(f"RESULT: {result}")
    print("Website/game yaha hai:  workspace\\project\\")
    print("Chalane ke liye:  cd workspace\\project  fir  python -m http.server 8000")
    print("Fir browser me kholo:  http://localhost:8000")
    print("Team ki baat-cheet:     workspace\\messages.md")
    print("Notes (memory):         workspace\\notes.md")
    print("=" * 52)
    return 0 if not failures else 1


def main():
    llm.load_env()
    cfg = load_config()
    ap = argparse.ArgumentParser(description="Agent Team")
    ap.add_argument("goal", nargs="?", help="kya banwana hai, quotes me")
    ap.add_argument("--check", action="store_true", help="setup check")
    args = ap.parse_args()
    if args.check:
        sys.exit(cmd_check(cfg))
    if not args.goal:
        ap.print_help()
        sys.exit(1)
    sys.exit(cmd_run(args.goal, cfg))


if __name__ == "__main__":
    main()
