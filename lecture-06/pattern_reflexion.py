"""Reflexion (Shinn et al. 2023, arXiv:2303.11366) - slides 18-20.

After each run over a small task family, the agent reflects in natural
language on what it got wrong, and that reflection is persisted (to
reflexion_memory.json) and fed back into the system prompt for the next
run - the same agent, same kind of task, improving across attempts rather
than within a single attempt.

Task family: "how many times does <letter> appear in <word>?" - a known
weak spot for LLMs (tokenization obscures repeated letters), with an
objective grader (Python's own str.count). That objective signal is the
part a Reflexion demo actually needs: slide 18 says Reflexion fits
"environments where the same agent runs the same task repeatedly" - a
chat-only task with no pass/fail has nothing to reflect on.

Memory is capped to the last 3 reflections when building the next
system prompt (see format_reflections) - the bounded-memory extension
from slide 34, applied rather than just described.

Run:
    python pattern_reflexion.py
"""
from __future__ import annotations

import json
import pathlib
import time

from llm import DEFAULT_MODEL as MODEL, ask

MEMORY_PATH = pathlib.Path(__file__).parent / "reflexion_memory.json"

TASK_FAMILY = [
    ("strawberry", "r"),
    ("mississippi", "s"),
    ("bookkeeper", "e"),
    ("possession", "s"),
    ("committee", "t"),
]

BASE_SYSTEM = (
    "Count how many times the given letter appears in the given word. "
    "Answer with ONLY the integer count."
)

REFLECTION_PROMPT = """You just attempted: {task}
Your answer: {answer}
Correct answer: {correct}
Outcome: wrong

Reflect briefly (1-2 sentences). What went wrong, and what should a future
you do differently on similar letter-counting tasks?"""


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
    lines = ["Lessons from previous runs:"]
    lines += [f"- {e['reflection']}" for e in recent]
    return "\n".join(lines)


def attempt(word: str, letter: str, system: str) -> str:
    return ask(f"Word: {word}\nLetter: {letter}", system=system, model=MODEL, max_tokens=20, effort="low")


def run_once(run_idx: int) -> float:
    memory = load_memory()
    system = BASE_SYSTEM + "\n\n" + format_reflections(memory)
    correct_count = 0

    for word, letter in TASK_FAMILY:
        raw = attempt(word, letter, system)
        digits = "".join(ch for ch in raw if ch.isdigit() or ch == "-")
        answer = int(digits) if digits else None
        correct = word.lower().count(letter.lower())
        ok = answer == correct
        correct_count += int(ok)
        status = "OK" if ok else "WRONG"
        print(f"  '{letter}' in '{word}': model={answer} correct={correct}  {status}")

        if not ok:
            reflection = ask(
                REFLECTION_PROMPT.format(
                    task=f"count '{letter}' in '{word}'", answer=answer, correct=correct
                ),
                model=MODEL,
                max_tokens=100,
                effort="low",
            )
            save_entry(
                {
                    "task_id": "letter_count",
                    "run_idx": run_idx,
                    "reflection": reflection,
                    "outcome": {"word": word, "letter": letter, "answer": answer, "correct": correct},
                    "ts": time.time(),
                }
            )

    accuracy = correct_count / len(TASK_FAMILY)
    print(f"Run {run_idx} accuracy: {accuracy:.0%}")
    return accuracy


def main() -> None:
    if MEMORY_PATH.exists():
        MEMORY_PATH.unlink()  # start fresh so the demo is reproducible run-to-run

    accuracies = []
    for run_idx in range(1, 4):
        print(f"\n=== Run {run_idx} ===")
        accuracies.append(run_once(run_idx))

    print(f"\nAccuracy across runs: {[f'{a:.0%}' for a in accuracies]}")
    print(f"Memory persisted to {MEMORY_PATH.name} - inspect it to see the stored reflections.")


if __name__ == "__main__":
    main()
