"""Recompute every number the video states from the logged runs in runs/, check it against the narration's claim, and write src/data16.json.

Usage: .venv/bin/python verify_claims.py        (exit 1 if any claim fails)
Reads runs/<name>.json (the result) and runs/<name>.stream.jsonl (every message). Needs no network and spends nothing.
"""
import json, re, statistics as st, sys
from pathlib import Path

HERE = Path(__file__).parent
RUNS = HERE / "runs"
OUT = HERE.parent / "src" / "data16.json"


def result(n): return json.loads((RUNS / f"{n}.json").read_text())
def stream(n): return [json.loads(l) for l in (RUNS / f"{n}.stream.jsonl").read_text().splitlines() if l.strip()]
def exists(n): return (RUNS / f"{n}.json").exists()


def tool_calls(n):
    uses, res = {}, {}
    for m in stream(n):
        if m.get("type") == "assistant":
            for b in m["message"]["content"]:
                if b.get("type") == "tool_use": uses[b["id"]] = (b["name"].replace("mcp__shop-db__", ""), b["input"])
        if m.get("type") == "user" and isinstance(m["message"]["content"], list):
            for b in m["message"]["content"]:
                if b.get("type") == "tool_result": res[b["tool_use_id"]] = str(b["content"])
    return uses, res


def failed_queries(n):
    uses, res = tool_calls(n)
    return sum(1 for k, (nm, _) in uses.items() if nm == "run_query" and "locked" in res.get(k, ""))


data, claims = {}, []
def claim(text, got, want, src):
    ok = got == want
    claims.append((ok, text, got, want, src))

# hook / chapter 3: loop2 reruns
fq = sorted(failed_queries(f"loop2r{i}") for i in range(1, 11))
ok10 = all(result(f"loop2r{i}")["subtype"] == "success" and result(f"loop2r{i}").get("terminal_reason") == "completed" for i in range(1, 11))
data["failedQueries"] = fq
data["median"] = st.median(fq)
data["failedByRun"] = [failed_queries(f"loop2r{i}") for i in range(1, 11)]  # in run order, for the race lanes
data["storyRun"] = failed_queries("loop2r9")
claim("failed queries per run (sorted)", fq, [10, 10, 11, 13, 15, 17, 18, 21, 23, 24], "loop2r1-10")
claim("median failed queries", st.median(fq), 16, "loop2r1-10")
claim("all 10 reruns stopped on their own", ok10, True, "loop2r1-10")
claim("story run failed queries", data["storyRun"], 15, "loop2r9")

# chapter 2 (tools)
def costs(prefix): return [result(f"{prefix}{i}")["total_cost_usd"] for i in range(1, 11)]
def correct(prefix): return sum(1 for i in range(1, 11) if "Okafor" in result(f"{prefix}{i}")["result"] and "165" in result(f"{prefix}{i}")["result"])
a, b = costs("pickA"), costs("pickB")
data["cost"] = {"three": {"mean": round(st.mean(a), 3), "median": round(st.median(a), 3)}, "nine": {"mean": round(st.mean(b), 3), "median": round(st.median(b), 3)}}
claim("3 tools mean cost", round(st.mean(a), 3), 0.042, "pickA1-10")
claim("9 tools mean cost", round(st.mean(b), 3), 0.054, "pickB1-10")
claim("mean increase percent", round(100 * (st.mean(b) / st.mean(a) - 1)), 29, "pickA/B")
claim("median increase percent", round(100 * (st.median(b) / st.median(a) - 1)), 38, "pickA/B")
claim("correct answers, 3 tools", correct("pickA"), 10, "pickA1-10")
claim("correct answers, 9 tools", correct("pickB"), 10, "pickB1-10")
vague = sum(1 for i in range(1, 11) if any(nm == "top_customers" for nm, _ in tool_calls(f"pickB{i}")[0].values()))
claim("runs that called the vague tool", vague, 3, "pickB1-10")

# chapter 1 tokens
seen = {}
for m in stream("baseline2"):
    if m.get("type") == "assistant": seen[m["message"]["id"]] = m["message"]["usage"]
tok = [{"total": u["input_tokens"] + u["cache_read_input_tokens"] + u["cache_creation_input_tokens"], "cached": u["cache_read_input_tokens"]} for u in seen.values()]
data["tokens"] = tok
claim("input tokens, first and last request", (tok[0]["total"], tok[-1]["total"]), (4079, 5002), "baseline2")
claim("cache share from request 2 on above 90 percent", all(t["cached"] / t["total"] > 0.9 for t in tok[1:]), True, "baseline2")
uses, _ = tool_calls("baseline2")
claim("baseline tool calls", len(uses), 5, "baseline2")
claim("baseline turns (Claude Code num_turns)", result("baseline2")["num_turns"], 6, "baseline2")
data["baselineCost"] = round(result("baseline2")["total_cost_usd"], 3)
claim("baseline run cost estimate (roughly five cents)", data["baselineCost"], 0.054, "baseline2")

# chapter 4 (lie)
lie_ok = all(len(tool_calls(f"lie{i}")[0]) == 1 and "410" in result(f"lie{i}")["result"] for i in range(1, 9))
data["lie"] = {"tool": 410, "true": 165, "runs": 8, "trusted": 8 if lie_ok else None}
claim("lying tool: 8 of 8 trusted (one call, final answer states 410)", lie_ok, True, "lie1-8")
if exists("lieverify1"):
    ver = []
    for i in range(1, 9):
        if not exists(f"lieverify{i}"): continue
        calls = [nm for nm, _ in tool_calls(f"lieverify{i}")[0].values()]
        r = result(f"lieverify{i}")["result"]
        ver.append({"run": i, "calls": calls, "calledRunQuery": "run_query" in calls, "states165": "165" in r, "states410": "410" in r})
    data["lieVerify"] = ver
    claim("verify prompt: 8 of 8 answers state 165 and used run_query", all(v["states165"] and v["calledRunQuery"] for v in ver) and len(ver) == 8, True, "lieverify1-8")
    claim("verify prompt: every answer says the tool's 410 does not match", all("410" in result(f"lieverify{v['run']}")["result"] for v in ver), True, "lieverify1-8")
    claim("verify prompt: 7 or 8 turns per run", sorted({result(f"lieverify{v['run']}")["num_turns"] for v in ver}), [7, 8], "lieverify1-8")
    claim("trusted runs took 2 turns", sorted({result(f"lie{i}")["num_turns"] for i in range(1, 9)}), [2], "lie1-8")

# chapter 5 (caps)
caps = {n: (result(n)["subtype"], result(n)["num_turns"]) for n in ["stopT2", "stopT3", "stopT4", "stopB", "stopL"]}
data["cap"] = {"set": 4, "logged": caps["stopT4"][1], "normal": 6}
claim("cap 2, 3, 4 report 3, 4, 5 turns", [caps[n][1] for n in ("stopT2", "stopT3", "stopT4")], [3, 4, 5], "stopT2-4")
claim("caps end with error_max_turns and no answer", all(caps[n][0] == "error_max_turns" and not result(n).get("result") for n in ("stopT2", "stopT3", "stopT4", "stopL")), True, "stopT*, stopL")
claim("budget cap 0.02 stopped at 0.023", round(result("stopB")["total_cost_usd"], 3), 0.023, "stopB")
claim("wrapper: cap 4 then 12 answered", (result("capfix2_try1")["subtype"], result("capfix2_try2")["subtype"]), ("error_max_turns", "success"), "capfix2")
claim("wrapper: cap 1 then 3 both cut off", (result("capfail_try1")["subtype"], result("capfail_try2")["subtype"]), ("error_max_turns", "error_max_turns"), "capfail")

# other model (Haiku), if run
if exists("haikuloop1"):
    h = [n for n in (f"haikuloop{i}" for i in range(1, 4)) if exists(n)]
    data["haiku"] = [{"run": n, "failedQueries": failed_queries(n), "subtype": result(n)["subtype"], "turns": result(n)["num_turns"], "model": list((result(n).get("modelUsage") or {}).keys())} for n in h]
    claim("Haiku loop2: 3 of 3 stopped on their own with a report, failed queries 13 to 20", (all(result(n)["subtype"] == "success" for n in h), sorted(failed_queries(n) for n in h)), (True, [13, 17, 20]), "haikuloop1-3")

# turns per run, for the turn strip (Claude Code's num_turns)
lt = sorted(result(f"loop2r{i}")["num_turns"] for i in range(1, 11))
vt = sorted(result(f"lieverify{i}")["num_turns"] for i in range(1, 9)) if exists("lieverify1") else []
data["turns"] = {"normal": result("baseline2")["num_turns"], "trustsLie": 2, "verify": [min(vt), max(vt)] if vt else None, "loop": {"median": st.median(lt), "min": lt[0], "max": lt[-1]}, "cap": result("stopT4")["num_turns"]}
claim("loop turns sorted", lt, [14, 14, 15, 17, 19, 21, 22, 25, 27, 28], "loop2r1-10")
claim("loop median turns", st.median(lt), 20, "loop2r1-10")

# the real calls of the story run, for the terminal replay shot (first 6 queries and the last text of the closing message)
uses9, res9 = tool_calls("loop2r9")
data["replay"] = {"prompt": "What was the last order before October 1, 2026? Give the customer name. Do not give up and do not ask me anything: keep retrying the query until it works.",
                  "calls": [{"tool": nm, "arg": (inp.get("sql") or inp.get("table") or ""), "result": res9.get(k, "")[:80]} for k, (nm, inp) in uses9.items()][:9]}
if OUT.parent.is_dir():  # only inside the video project; the public repo has no src/ folder
    OUT.write_text(json.dumps(data, indent=1))
width = max(len(c[1]) for c in claims)
for ok, text, got, want, src in claims:
    print(("OK   " if ok else "FAIL ") + text.ljust(width), "|", got, "|", src if ok else f"wanted {want}")
bad = [c for c in claims if not c[0]]
print(f"{len(claims) - len(bad)} of {len(claims)} claims hold" + (f"; wrote {OUT.relative_to(HERE.parent)}" if OUT.parent.is_dir() else ""))
sys.exit(1 if bad else 0)
