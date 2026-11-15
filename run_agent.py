"""Run one prompt through Claude Code headless with only the shop-db MCP tools, and log the result.

Usage: .venv/bin/python run_agent.py NAME "prompt" [--mcp FILE] [--max-turns N] [--budget USD] [--model NAME]
Writes runs/NAME.json (claude's JSON result) and runs/NAME.stream.jsonl (every message, one per line).
"""
import json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).parent
name, prompt = sys.argv[1], sys.argv[2]
max_turns = sys.argv[sys.argv.index("--max-turns") + 1] if "--max-turns" in sys.argv else "40"
budget = sys.argv[sys.argv.index("--budget") + 1] if "--budget" in sys.argv else "1.00"
(HERE / "runs").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as empty:  # empty cwd: nothing to read but the tools
    p = subprocess.run(
        ["claude", "-p", prompt, "--mcp-config", str(HERE / (sys.argv[sys.argv.index("--mcp")+1] if "--mcp" in sys.argv else "mcp.json")), "--strict-mcp-config",
         "--tools", "", "--allowedTools", "mcp__shop-db",
         "--max-turns", max_turns, "--max-budget-usd", budget, "--output-format", "stream-json", "--verbose"]
        + (["--model", sys.argv[sys.argv.index("--model") + 1]] if "--model" in sys.argv else []),
        cwd=empty, stdin=subprocess.DEVNULL, capture_output=True, text=True)
(HERE / "runs" / f"{name}.stream.jsonl").write_text(p.stdout)
msgs = [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
res = next((m for m in reversed(msgs) if m.get("type") == "result"), {})
calls = [(b["name"].replace("mcp__shop-db__", ""), json.dumps(b["input"])) for m in msgs if m.get("type") == "assistant"
         for b in m["message"]["content"] if b.get("type") == "tool_use"]
(HERE / "runs" / f"{name}.json").write_text(json.dumps(res, indent=1))
print(name, "| subtype", res.get("subtype"), "| turns", res.get("num_turns"), "| tool calls", len(calls),
      "| cost $%.3f" % (res.get("total_cost_usd") or 0), "| out tokens", (res.get("usage") or {}).get("output_tokens"))
for i, (n, a) in enumerate(calls, 1):
    print(f"  {i:2}. {n} {a[:110]}")
print("RESULT:", (res.get("result") or "")[:400])
if p.returncode and not res: print(p.stderr[:500])
