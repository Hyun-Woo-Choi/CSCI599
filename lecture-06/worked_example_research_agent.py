"""Worked example (slides 29-31): multi-document research agent.

Composes three patterns from this lecture, matching slide 31's diagram:

  - Plan-and-Execute is the outer loop (decompose -> execute each
    subtask -> synthesize) - see pattern_plan_and_execute.py.
  - Tree-of-Thought runs *inside* the executor for each subtask: before
    touching a tool, it branches over a few candidate investigation
    angles ("which doc to read, what to search for"), scores each one,
    and starts from the best-scoring branch - see
    pattern_tree_of_thought.py for ToT on its own.
  - Reflexion fires once the run completes: it reflects on the finished
    comparison and persists that reflection to research_agent_memory.json,
    which the *next* run of this same task reads back - see
    pattern_reflexion.py for Reflexion on its own.

Per the lecture's own framing (slide 30): "the delivered package
implements the four component patterns; this exact three-pattern
composition is a worked architecture, not a bundled script." Read the
three pattern_*.py files first - this file wires their ideas together on
one task, reusing the same local doc corpus (docs/, via docs_tools.py)
as pattern_plan_and_execute.py.

Run it twice in a row to see Reflexion's memory feed into the second
run's plan:
    python worked_example_research_agent.py
    python worked_example_research_agent.py
"""
from __future__ import annotations

import json
import pathlib
import re
import time

import docs_tools
from llm import DEFAULT_MODEL as MODEL, ask, ask_full

STEP_BUDGET = 4
MEMORY_PATH = pathlib.Path(__file__).parent / "research_agent_memory.json"

TASK = (
    "Compare how LangGraph, CrewAI, and AutoGen represent and hand off "
    "an agent's state, and summarize the key differences."
)


# ---- Reflexion memory (dedicated file - see pattern_reflexion.py for the
# standalone version this is adapted from) ----------------------------------

def load_memory() -> list[dict]:
    if MEMORY_PATH.exists():
        return json.loads(MEMORY_PATH.read_text())
    return []


def save_entry(entry: dict) -> None:
    memory = load_memory()
    memory.append(entry)
    MEMORY_PATH.write_text(json.dumps(memory, indent=2))


def format_reflections(entries: list[dict], k: int = 3) -> str:
    recent = entries[-k:]
    if not recent:
        return ""
    lines = ["Lessons from previous runs of this task:"]
    lines += [f"- {e['reflection']}" for e in recent]
    return "\n".join(lines)


# ---- Plan-and-Execute: outer loop -----------------------------------------

def planner_llm(task: str) -> list[str]:
    text = ask(
        "Break this task into 3-5 concrete, ordered subtasks, one per "
        "line, no numbering, no extra commentary.\n\nTask: " + task,
        model=MODEL,
        max_tokens=400,
        effort="medium",
    )
    return [line.strip("- ").strip() for line in text.splitlines() if line.strip()]


def synthesize(task: str, results: list[dict]) -> str:
    joined = "\n\n".join(f"- {r['result']}" for r in results)
    return ask(
        f"Task: {task}\n\nSubtask findings:\n{joined}\n\n"
        "Write a concise final comparison synthesizing these findings.",
        model=MODEL,
        max_tokens=800,
        effort="medium",
    )


# ---- Tree-of-Thought: branching investigation inside the executor --------

def propose_investigation_angles(subtask: str) -> list[str]:
    docs = docs_tools.list_docs().splitlines()
    angles = [f"read_doc({d})" for d in docs]
    angles += ["search_docs('state')", "search_docs('graph')"]
    return angles


def tot_pick_investigation(subtask: str, options: list[str]) -> str:
    """Score each candidate investigation angle, return the best one -
    the "generate, evaluate, prune" mechanics from pattern_tree_of_thought.py,
    applied to picking a first move instead of an arithmetic step."""
    scored = []
    for option in options:
        text = ask(
            f"Subtask: {subtask}\nCandidate first move: {option}\n\n"
            "Rate 0-10 how likely this move is to surface the fact this "
            "subtask needs. Answer with ONLY the number.",
            model=MODEL,
            max_tokens=20,
        )
        match = re.search(r"(\d+(\.\d+)?)", text)
        scored.append((option, float(match.group(1)) if match else 0.0))
    scored.sort(key=lambda x: -x[1])
    print("    ToT branch scores: " + ", ".join(f"{o!r}={s:.1f}" for o, s in scored))
    return scored[0][0]


# ---- Execute: ToT branch selection, then a small ReAct tool loop ---------

def execute_subtask(subtask: str, context: list[str]) -> dict:
    best_angle = tot_pick_investigation(subtask, propose_investigation_angles(subtask))

    messages = [
        {
            "role": "user",
            "content": (
                f"Subtask: {subtask}\n"
                f"Start by following this lead: {best_angle}\n\n"
                "Context from earlier subtasks:\n" + ("\n".join(context) or "(none yet)")
            ),
        }
    ]
    system = (
        "You are the executor for one subtask of a larger research plan. "
        "Use the available tools to gather the fact this subtask needs, "
        "then answer with a concise result (2-4 sentences)."
    )

    for i in range(STEP_BUDGET):
        response = ask_full(
            messages, system=system, tools=docs_tools.TOOLS, model=MODEL, max_tokens=1024
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text")
            return {"status": "ok", "result": text, "steps_used": i + 1}

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result_text = docs_tools.call_tool(block.name, block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result_text}
                )
        messages.append({"role": "user", "content": tool_results})

    return {"status": "failed", "result": "step budget exhausted", "steps_used": STEP_BUDGET}


# ---- Reflexion: reflect on the finished run, persist for next time -------

def reflect_on_run(task: str, final_answer: str, run_idx: int) -> None:
    reflection_text = ask(
        f"Task: {task}\nFinal answer produced:\n{final_answer}\n\n"
        "Reflect briefly (1-2 sentences): what would make the next run of "
        "this same research task faster or more accurate?",
        model=MODEL,
        max_tokens=100,
        effort="low",
    )
    save_entry(
        {
            "task_id": "research_agent",
            "run_idx": run_idx,
            "reflection": reflection_text,
            "outcome": {"status": "ok"},
            "ts": time.time(),
        }
    )
    print(f"\nReflection stored: {reflection_text}")


# ---- Plan-and-Execute driver ----------------------------------------------

def run() -> str:
    prior = load_memory()
    task_with_memory = TASK
    if prior:
        print(f"(loaded {len(prior)} prior reflection(s) for this task)")
        task_with_memory += "\n\n" + format_reflections(prior)

    plan = planner_llm(task_with_memory)
    print("Plan:")
    for i, s in enumerate(plan, 1):
        print(f"  {i}. {s}")

    results: list[dict] = []
    for i, step in enumerate(plan, 1):
        print(f"\nExecuting subtask {i}/{len(plan)}: {step}")
        outcome = execute_subtask(step, [r["result"] for r in results])
        results.append(outcome)
        print(f"  -> {outcome['status']} in {outcome['steps_used']} tool round(s)")

    answer = synthesize(TASK, results)
    print("\n=== Final answer ===")
    print(answer)

    reflect_on_run(TASK, answer, run_idx=len(prior) + 1)
    return answer


if __name__ == "__main__":
    run()
