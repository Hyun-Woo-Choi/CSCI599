# Lecture 06 — Planning Patterns, runnable

The slide deck ("From ReAct to LangGraph — Planning Patterns", CSCI 599
Lecture 6) shows each pattern as a short pseudocode snippet: it calls
`client.chat.completions.create(...)` (an OpenAI-shaped call) and leans on
helper functions — `parse_answer`, `generate_thoughts`, `evaluate`,
`planner_llm`, `react_loop`, `should_replan`, `synthesize`, `llm`,
`format_reflections`, and so on — that are named but never defined. That's
normal for slides; it's not something you can paste into a terminal.

This folder fills in every one of those helpers and swaps the client for
the **Anthropic** Claude API, so each pattern actually runs end to end.

## Setup

```bash
cd lecture-06
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # console.anthropic.com/settings/keys
```

(See `../demo_venv_setup.md` for the Windows / Linux / macOS venv boilerplate
this project follows, and `../claude_code_cli_install.md` if you also want
the Claude Code CLI itself.)

## Files, mapped to slides

| File | Slides | Pattern |
|---|---|---|
| `llm.py` | — | Shared Anthropic client wrapper every script imports |
| `pattern_self_consistency.py` | 7-9 | Self-consistency — sample N paths, majority vote |
| `pattern_tree_of_thought.py` | 10-13 | Tree-of-Thought — branch, evaluate, prune, search (Game of 24) |
| `docs_tools.py` | — | Tiny local doc corpus + tools, used by the two files below |
| `pattern_plan_and_execute.py` | 14-17 | Plan-and-Execute — plan, ReAct-execute, re-plan on failure |
| `pattern_reflexion.py` | 18-20 | Reflexion — reflect after each run, persist to memory, feed forward |
| `worked_example_research_agent.py` | 29-31 | The closing worked example: Plan-and-Execute (outer) + ToT (branching inside the executor) + Reflexion (memory across runs) |
| `docs/*.txt` | — | 3 short local "framework" docs (LangGraph / CrewAI / AutoGen) the executor tools read, so the demos run offline — no web search required |

Run any of them directly:

```bash
python pattern_self_consistency.py
python pattern_tree_of_thought.py
python pattern_plan_and_execute.py
python pattern_reflexion.py
python worked_example_research_agent.py
python worked_example_research_agent.py   # run twice - the 2nd run reads the 1st run's reflection
```

## Design choices worth knowing about

- **Model per pattern, not one model for everything.** Self-consistency
  needs sampling diversity via `temperature`, but `temperature` is a
  removed/400 parameter on the newest Claude models (Opus 5, Sonnet 5,
  Fable 5) — their diversity instead comes from adaptive thinking. That's
  literally slide 9's "2026 reality" bullet: on those models, repeated
  samples can collapse to a unanimous vote. So `pattern_self_consistency.py`
  pins the model to Claude Haiku 4.5, which still takes `temperature`, to
  keep the demo showing real vote diversity instead of looking broken.
  Everything else defaults to Claude Opus 5 (`llm.DEFAULT_MODEL`).
- **Tree-of-Thought uses the Game of 24** (the paper's own benchmark):
  4 numbers, reach 24 with `+ - * /`. Candidate moves are enumerated in
  code (deterministic arithmetic, no need for an LLM to invent numbers);
  `evaluate()` is the one LLM call, scoring how promising a partial state
  is. That's deliberate — slide 12's failure mode ("evaluator quality
  bounds tree quality") is about that exact function, so it's isolated
  and easy to swap out and re-run.
- **No web search.** The worked example's task ("compare how LangGraph,
  CrewAI, and AutoGen handle agent state") is answered from three short
  local `docs/*.txt` files instead of the live internet, via a `list_docs`
  / `read_doc` / `search_docs` toolset in `docs_tools.py`. Those docs are
  course notes for this exercise, not vendor documentation — good enough
  to demo the pattern, not a citation.
- **Reflexion memory is bounded.** `format_reflections(entries, k=3)`
  only loads the last 3 reflections into the next run's prompt — the
  "recency cap" extension from slide 34, applied rather than just
  described, so memory doesn't grow the prompt forever.
- **`pattern_reflexion.py` and `worked_example_research_agent.py` use
  separate memory files** (`reflexion_memory.json` vs.
  `research_agent_memory.json`) even though both demonstrate Reflexion —
  each script is meant to be read and run on its own, so they don't share
  state. Both files are gitignored (they're run output, not source).

## What's not included

The slide deck's LangGraph/production section (slides 22-28: `StateGraph`,
the supervisor pattern via `langgraph_supervisor`, hierarchical
supervisors) isn't wired up here — it needs the `langgraph` /
`langchain` / `langgraph_supervisor` packages and, per the slide's own
"When NOT to use LangGraph" rule (slide 28), is overkill for a single
offline demo. The orchestration those slides show (`plan → execute →
re-plan-or-synthesize`, as a compiled graph instead of the hand-rolled
`while` loop in `pattern_plan_and_execute.py`) is a natural next exercise
once you're comfortable with the bare version here — ask if you want that
filled in too.
