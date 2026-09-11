"""Self-consistency (Wang et al. 2022, arXiv:2203.11171) - slides 7-9.

Sample N independent reasoning paths for the same question and take the
majority-vote answer: diversity in reasoning, consensus in the answer.

Diversity here comes from `temperature`, which is why this demo pins the
model to Claude Haiku 4.5 instead of the lecture's default Opus 5:
`temperature` is a removed/400 parameter on Claude Opus 5, Sonnet 5, and
Fable 5 (their diversity comes from adaptive thinking instead). That's
exactly the "2026 reality" bullet on slide 9 - on those newer models,
repeated samples can collapse to a unanimous vote, which would make this
demo look broken rather than illustrate the pattern.

Run:
    python pattern_self_consistency.py
"""
from __future__ import annotations

import re
from collections import Counter

from llm import ask

MODEL = "claude-haiku-4-5"
N = 7  # odd, so majority vote never ties

QUESTION = (
    "A store had 120 apples. They sold 35% of them in the morning and "
    "28 more in the afternoon. How many apples are left?"
)

SYSTEM = (
    "Think step by step, briefly. "
    "End your answer on its own line as: ANSWER=<integer>"
)


def parse_answer(text: str) -> str:
    match = re.search(r"ANSWER\s*=\s*(-?\d+)", text)
    if match:
        return match.group(1)
    # Fallback: last line, in case the model didn't follow the format.
    return text.strip().splitlines()[-1]


def self_consistency(question: str, n: int = N) -> tuple[str, Counter]:
    answers = []
    for i in range(n):
        text = ask(
            question,
            system=SYSTEM,
            model=MODEL,
            max_tokens=400,
            temperature=1.0,
        )
        answer = parse_answer(text)
        answers.append(answer)
        print(f"  path {i + 1}/{n}: ANSWER={answer}")
    votes = Counter(answers)
    return votes.most_common(1)[0][0], votes


def main() -> None:
    print(f"Question: {QUESTION}\n")
    winner, votes = self_consistency(QUESTION)

    print(f"\nVotes: {dict(votes)}")
    print(f"Majority answer: {winner}")

    # Slide 9 diagnostic: a close top-2 split means "low agreement, escalate"
    # (e.g. to Tree-of-Thought - see pattern_tree_of_thought.py) instead of
    # trusting the vote blindly.
    top_two = votes.most_common(2)
    if len(top_two) == 2 and (top_two[0][1] - top_two[1][1]) <= 2:
        total = sum(votes.values())
        print(
            f"Diagnostic: top-2 vote split is close "
            f"({top_two[0][1]} vs {top_two[1][1]} of {total}) - "
            "treat this as low-agreement and escalate."
        )
    else:
        print("Diagnostic: clear majority - agreement is high.")


if __name__ == "__main__":
    main()
