"""Tree-of-Thought (Yao et al. 2023, arXiv:2305.10601) - slides 10-13.

Classic ToT benchmark: Game of 24. Given 4 numbers, combine them with
+ - * / (each number used exactly once) to reach 24. A wrong first move
can make the puzzle unsolvable from then on - exactly the failure mode
ToT is built to avoid ("first step matters more than the last", slide 13).

Candidate moves (which two remaining numbers to combine, and how) are
enumerated in code - the arithmetic is deterministic and doesn't need an
LLM call. `evaluate()` is the LLM call: it scores how promising a partial
state looks, and that's the piece slide 12's failure mode is about
("evaluator quality bounds tree quality") - swap the prompt in `evaluate`
for a worse one and the search degrades even though nothing else changed.

Run:
    python pattern_tree_of_thought.py
"""
from __future__ import annotations

import itertools
import re

from llm import ask

# Evaluator kept cheap/fast on purpose - it's just a 0-10 rating call, and
# using Haiku here makes "swap the evaluator model and see what changes"
# a one-line experiment (try MODEL = "claude-opus-5" and re-run).
MODEL = "claude-haiku-4-5"

NUMBERS: tuple[int, ...] = (4, 9, 10, 13)  # solvable: (13-9) * (10-4) = 24
TARGET = 24
DEPTH = 3          # combine 4 numbers down to 1 in 3 steps
BRANCH_CAP = 24     # safety cap on candidates considered per state (k)
BEAM_WIDTH = 3       # states kept after evaluate + prune (b)


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:.2f}"


class State:
    def __init__(self, numbers: tuple[float, ...], trail: list[str]):
        self.numbers = numbers
        self.trail = trail

    def done(self) -> bool:
        return len(self.numbers) == 1

    def solved(self) -> bool:
        return self.done() and abs(self.numbers[0] - TARGET) < 1e-6


def generate_thoughts(state: State, k: int = BRANCH_CAP) -> list[State]:
    """Enumerate up to k candidate next moves - deterministic arithmetic."""
    candidates = []
    idxs = range(len(state.numbers))
    for i, j in itertools.combinations(idxs, 2):
        a, b = state.numbers[i], state.numbers[j]
        rest = [state.numbers[x] for x in idxs if x not in (i, j)]
        ops = [("+", a + b), ("-", a - b), ("-", b - a), ("*", a * b)]
        if b != 0:
            ops.append(("/", a / b))
        if a != 0:
            ops.append(("/", b / a))
        for op, value in ops:
            trail_step = f"{_fmt(a)} {op} {_fmt(b)} = {_fmt(value)}"
            candidates.append(State(tuple(rest + [value]), state.trail + [trail_step]))

    # De-dup states that land on the same multiset of remaining numbers.
    seen: set[tuple] = set()
    unique = []
    for c in candidates:
        key = tuple(sorted(round(n, 4) for n in c.numbers))
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique[:k]


def evaluate(state: State) -> float:
    """LLM call: score 0-10 on how promising this partial state looks."""
    if state.solved():
        return 10.0
    if state.done():
        return 0.0
    prompt = (
        f"Game of 24. Target: {TARGET}.\n"
        f"Remaining numbers: {list(state.numbers)}\n"
        f"Steps so far: {state.trail}\n\n"
        "Rate 0-10 how likely these remaining numbers can still be combined "
        "(using +, -, *, /, each number used exactly once, any order) to "
        "reach the target. Answer with ONLY the number."
    )
    text = ask(prompt, model=MODEL, max_tokens=50)
    match = re.search(r"(\d+(\.\d+)?)", text)
    return float(match.group(1)) if match else 0.0


def tot_bfs(numbers: tuple[int, ...], depth: int, b: int) -> State | None:
    frontier: list[tuple[State, float]] = [(State(numbers, []), 0.0)]
    for step in range(depth):
        candidates = []
        for state, _ in frontier:
            for thought in generate_thoughts(state):
                candidates.append((thought, evaluate(thought)))

        candidates.sort(key=lambda x: -x[1])
        frontier = candidates[:b]

        print(f"\nDepth {step + 1} - kept top {len(frontier)}:")
        for state, score in frontier:
            print(f"  score={score:4.1f}  numbers={list(state.numbers)}  trail={state.trail}")

        solved = [s for s, _ in frontier if s.solved()]
        if solved:
            return solved[0]

    return frontier[0][0] if frontier else None


def main() -> None:
    print(f"Numbers: {list(NUMBERS)}  Target: {TARGET}")
    result = tot_bfs(NUMBERS, DEPTH, BEAM_WIDTH)

    print("\n--- Result ---")
    if result and result.solved():
        print("Solved!")
        for step in result.trail:
            print(f"  {step}")
    else:
        print("No exact solution survived the beam - closest state kept:")
        if result:
            print(f"  numbers={list(result.numbers)}  trail={result.trail}")
        print(
            "(This is itself the slide-12 failure mode in action: the "
            "evaluator pruned the winning branch. Try raising BEAM_WIDTH "
            "or switching MODEL to claude-opus-5 and re-running.)"
        )


if __name__ == "__main__":
    main()
