# ai-agent-loop-tests

The code and run logs behind the video **I Told My AI Agent to Never Give Up. It Gave Up.**: [VIDEO LINK]

One tiny shop database (`shop.db`, made-up data), one MCP server
(`db_server.py`), and Claude Code run headless as the agent. Every number in the video comes from a logged run in `runs/`.

## Run it
Needs Python 3.11+, [uv](https://docs.astral.sh/uv/) and Claude Code (the agent under test; a run uses your Claude plan or API credit).
The five `mcp*.json` files hold absolute paths to this folder: replace `/ABSOLUTE/PATH/TO/ai-agent-loop-tests` with the folder's real path first.
```bash
uv sync
.venv/bin/python run_agent.py demo "What was the last order before October 1, 2026? Give the customer name." --mcp mcp.json
```
`run_agent.py NAME "prompt" [--mcp FILE] [--max-turns N] [--budget USD] [--model NAME]` runs one prompt through `claude -p` in an empty folder with only the
shop tools, and writes `runs/NAME.json` (the result) and `runs/NAME.stream.jsonl` (every message). Costs are Claude Code's own list-price estimates.

| File | What it does |
|---|---|
| `mcp.json`, `db_server.py` | the three real tools: `list_tables`, `describe_table`, `run_query` (read-only SQLite) |
| `mcp_loop.json`, `loop_demo_server.py` | `run_query` always answers "database is locked" |
| `mcp_loop2.json`, `loop_demo2_server.py` | an error message that changes on every call |
| `mcp_many.json`, `many_tools_server.py` | nine tools instead of three (one has a vague description) |
| `mcp_lie.json`, `lying_server.py` | `customer_total` adds 245 EUR to the real total, with no error |
| `run_with_cap.py` | retries once with three times the turn cap, and reports FAILED when it is still cut off |
| `verify_claims.py` | recomputes every number the video states from `runs/` and checks it (29 checks, no network, no cost) |

## The tests
Loop (`loop2r1-10`), tools (`pickA1-10`, `pickB1-10`), the lying tool (`lie1-8`), the same with "verify" (`lieverify1-8`), the caps (`stopT2-4`, `stopB`, `stopL`,
`capfix*`, `capfail*`), a smaller model (`haikuloop1-3`). Results hold for this agent, this model and these setups only: run your own.

## About the logs
`runs/` holds one result file, one message log and one short call list per run. The logs are trimmed for publishing: only the start
event (tools, model, version), the assistant and tool messages and the final result are kept, and local paths are replaced.

MIT licence (see `LICENSE`).
