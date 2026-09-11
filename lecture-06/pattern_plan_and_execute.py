"""Plan-and-Execute (Wang et al. 2023, Plan-and-Solve Prompting,
arXiv:2305.04091) - slides 14-17.

LangGraph's three-loop pattern, run by hand: a planner LLM call produces
an ordered task list, an executor runs each task (a ReAct sub-loop with
tools), and a re-planner fires when execution diverges from the plan.

Contrast with ReAct: ReAct decides as it goes; Plan-and-Execute commits to
a sequence first, then adapts only when should_replan() says to.

Uses the local doc corpus in docs/ (via docs_tools.py) as the executor's
tools, so the whole thing runs offline once you have an API key - no web
search needed.

Run:
    python pattern_plan_and_execute.py
"""
from __future__ import annotations

import docs_tools
from llm import DEFAULT_MODEL as MODEL, ask, ask_full

STEP_BUDGET = 4       # Trigger 3 from slide 17: depth limit hit on current step
MAX_REPLANS = 2

TASK = (
    "Find the docs for LangGraph and CrewAI, and summarize the key "
    "difference in how they represent an agent's state."
)


def planner_llm(task: str) -> list[str]:
    text = ask(
        "Break this task into 3-5 concrete, ordered subtasks, one per "
        "line, no numbering, no extra commentary.\n\nTask: " + task,
        model=MODEL,
        max_tokens=400,
        effort="medium",
    )
    return [line.strip("- ").strip() for line in text.splitlines() if line.strip()]


def react_loop(step: str, context: list[str], max_steps: int = STEP_BUDGET) -> dict:
    """Minimal ReAct tool loop that executes one plan step.

    Returns an outcome dict shaped for should_replan() below: {status,
    result, steps_used}.
    """
    messages = [
        {
            "role": "user",
            "content": (
                f"Task step: {step}\n\n"
                "Context from earlier steps:\n" + ("\n".join(context) or "(none yet)")
            ),
        }
    ]
    system = (
        "You are the executor for one step of a larger plan. Use the "
        "available tools to complete just this step, then answer with a "
        "concise result. Call list_docs before read_doc/search_docs if "
        "you don't already know the filenames."
    )

    for i in range(max_steps):
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

    return {"status": "failed", "result": "step budget exhausted", "steps_used": max_steps}


def should_replan(outcome: dict) -> bool:
    """Slide 17's re-plan triggers 1 and 3 (trigger 2, a plan-invalidating
    observation, would need a domain-specific check - out of scope for
    this offline doc corpus)."""
    if outcome.get("status") == "failed":
        return True
    if outcome.get("steps_used", 0) >= STEP_BUDGET:
        return True
    return False


def replanner_llm(task: str, done_steps: list[str], results: list[dict]) -> list[str]:
    summary = "\n".join(
        f"- {s}: {r['result'][:200]}" for s, r in zip(done_steps, results)
    )
    text = ask(
        f"Original task: {task}\n\nSteps completed so far:\n{summary}\n\n"
        "One step failed or ran out of budget. Propose a revised list of "
        "at most 3 remaining subtasks to still complete the task, one per "
        "line, no numbering.",
        model=MODEL,
        max_tokens=300,
        effort="medium",
    )
    new_steps = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
    return done_steps + new_steps


def synthesize(task: str, results: list[dict]) -> str:
    joined = "\n\n".join(f"- {r['result']}" for r in results)
    return ask(
        f"Task: {task}\n\nStep results:\n{joined}\n\n"
        "Write a concise final answer synthesizing these results.",
        model=MODEL,
        max_tokens=800,
        effort="medium",
    )


def plan_and_execute(task: str) -> str:
    plan = planner_llm(task)
    print("Plan:")
    for i, s in enumerate(plan, 1):
        print(f"  {i}. {s}")

    results: list[dict] = []
    step_idx = 0
    replans = 0

    while step_idx < len(plan):
        step = plan[step_idx]
        print(f"\nExecuting step {step_idx + 1}/{len(plan)}: {step}")
        outcome = react_loop(step, [r["result"] for r in results])
        results.append(outcome)
        print(f"  -> {outcome['status']} in {outcome['steps_used']} tool round(s)")

        if should_replan(outcome):
            replans += 1
            if replans > MAX_REPLANS:
                print("  re-plan budget exhausted - moving on with what we have")
                step_idx += 1
                continue
            print("  re-planning...")
            plan = replanner_llm(task, plan[: step_idx + 1], results)
            step_idx = len(results)
        else:
            step_idx += 1

    return synthesize(task, results)


def main() -> None:
    answer = plan_and_execute(TASK)
    print("\n=== Final answer ===")
    print(answer)


if __name__ == "__main__":
    main()
