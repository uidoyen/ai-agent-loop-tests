"""Handle the empty result of a capped run: if the cap cut it off, retry once with a bigger cap.

Usage: .venv/bin/python run_with_cap.py NAME "prompt" CAP
Logs runs/NAME_try1.json and, only if the first try was cut off, runs/NAME_try2.json.
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
name, prompt, cap = sys.argv[1], sys.argv[2], int(sys.argv[3])


def run(tag: str, max_turns: int) -> dict:
    subprocess.run([str(HERE / ".venv/bin/python"), str(HERE / "run_agent.py"), f"{name}_{tag}", prompt,
                    "--max-turns", str(max_turns)], check=True, capture_output=True)
    return json.loads((HERE / "runs" / f"{name}_{tag}.json").read_text())


result = run("try1", cap)
retried = False
if result.get("subtype") == "error_max_turns":
    retried = True
    result = run("try2", cap * 3)
answer = (result.get("result") or "").strip()
if result.get("subtype") == "success" and answer:
    outcome = "ANSWERED" + (" after one retry" if retried else " on the first try")
else:  # still cut off, or an empty answer: report it, never pass an empty answer on as a result
    outcome = "FAILED: no answer" + (" even after the retry" if retried else "")
print(outcome, "|", result.get("subtype"), "| turns", result.get("num_turns"), "|", answer[:160])
sys.exit(0 if outcome.startswith("ANSWERED") else 1)
