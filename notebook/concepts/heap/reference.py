"""Generate and verify the teaching trace before rendering it."""
import heapq
import json
import random
from pathlib import Path


def valid(a):
    return all(a[(i - 1) // 2] <= a[i] for i in range(1, len(a)))


def trace(initial, value=None):
    a = initial.copy()
    frames = []

    def record(label, active=(), question=None, choices=None, answer=None):
        violations = [i for i in range(1, len(a)) if a[(i-1)//2] > a[i]]
        assert all(i in active or (i-1)//2 in active for i in violations)
        frames.append(dict(a=a.copy(), label=label, active=list(active),
                           valid=not violations, question=question,
                           choices=choices, answer=answer))

    assert valid(a)
    if value is not None:
        record('Initial min-heap', question=f'Where does {value} go first?',
               choices=['Next empty position', 'Replace the root'], answer='Next empty position')
        a.append(value)
        i = len(a)-1
        while i:
            p = (i-1)//2
            swap = a[i] < a[p]
            record('Compare with parent', (i, p), f'{a[i]} and parent {a[p]}: next move?',
                   ['Swap with parent', 'Stop sifting'], 'Swap with parent' if swap else 'Stop sifting')
            if not swap:
                break
            a[i], a[p] = a[p], a[i]
            i = p
        record('Push complete')
        expected = initial + [value]
    else:
        removed = a[0]
        record('Initial min-heap', question=f'Remove {removed}: which item fills the root?',
               choices=[str(a[-1]), str(a[1])], answer=str(a[-1]))
        a[0] = a.pop()
        i = 0
        while 2*i+1 < len(a):
            left = 2*i+1
            right = left+1
            child = right if right < len(a) and a[right] < a[left] else left
            if a[i] <= a[child]:
                record('Compare with children', (i, child), 'Is another swap needed?', ['Yes', 'No'], 'No')
                break
            choices = [f'Swap with {a[left]}']
            if right < len(a):
                choices.append(f'Swap with {a[right]}')
            choices.append('Stop sifting')
            record('Choose the smaller child', (i, child), f'{a[i]} at index {i}: next move?',
                   choices, f'Swap with {a[child]}')
            a[i], a[child] = a[child], a[i]
            i = child
        record(f'Pop complete · returned {removed}')
        expected = sorted(initial)[1:]
    assert valid(a)
    assert sorted(a) == sorted(expected)
    return frames


cases = [dict(name='Push 2', frames=trace([3, 8, 5, 12, 10, 7], 2)),
         dict(name='Pop minimum', frames=trace([3, 8, 5, 12, 10, 7])),
         dict(name='Push duplicate 3', frames=trace([3, 8, 5, 12, 10, 7], 3))]
rng = random.Random(11)
for _ in range(400):
    a = [rng.randint(-15, 15) for _ in range(rng.randint(2, 30))]
    heapq.heapify(a)
    trace(a, rng.randint(-15, 15))
    trace(a)
for a, value in [([], 2), ([2], 2), ([-4], -7)]:
    trace(a, value)
Path(__file__).with_name('trace.json').write_text(json.dumps(cases))
print('Verified 803 generated operations and 3 teaching traces.')
