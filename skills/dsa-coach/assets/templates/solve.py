"""{problem}

{url}
Started {date}.{pattern_line}

Plan card: fill it in before you write code (stage 6).
    State:
    Invariant:
    Relies on:
    Breaks if:
    Termination:
    Complexity:
"""


def solve(*args):
    # Give it the problem's parameters. Subgoal comments first (stage 7), then the code under each one.
    raise NotImplementedError


if __name__ == "__main__":
    # Stage 1: two or three examples, one of them an edge case. Predict each output before you run this.
    examples = [
        # ((args, ...), expected),
    ]
    for args, expected in examples:
        got = solve(*args)
        print("ok  " if got == expected else "FAIL", args, "->", got, "expected", expected)
