# contains-duplicate

Link: https://leetcode.com/problems/contains-duplicate/ · Pattern: arrays-hashing · Difficulty: easy · First logged: 2026-11-05

## Plan card

Problem:
Pattern + cue:         (which words in the problem pointed here)
State (one sentence):
Invariant:             (true every time the loop condition is checked)
  diagram:
Relies on:             (the datum or property that makes it work: sorted, all positive, a monotone predicate)
Breaks if:             (the change that breaks it, and what you'd use instead)
Initialization:        (slide the boundaries back: what makes the invariant true at the start?)
Loop guard:            (slide them forward: when is the unknown part empty?)
Body:                  (one step of progress that restores the invariant)
Termination measure:   (a number that shrinks every step)
Complexity:            (one-line argument)
Edge cases:            empty · one element · duplicates · negatives · no answer
Hand trace:            (one row per iteration, only the variables that change)

## Stage notes

### 2026-11-17 (9242c862de7772f26ae18019a9a07f0b)

- **1. Understand:** The problem is searching the element in remaining list, and scanning is o(n) so we will use hash set here
- **2. Find an approach:** Brute force on the grid:
  If element occurs more than once we have a True case, we will check an element against every other element of the list
  
  Count:
  Outermost line will run n times and inner will run n-i times where i is the position of element against which we are checking ...
  
  So, other number of iterations will be : (n-i) from i 1 to n where n is lengtt of list
- **3. Build it:** class Solution:
      def containsDuplicate(self, nums: list[int]) -> bool:
          unique_nums=set(nums)
          return  not len(nums)==len(unique_nums)
- **4. Check and finish:** Why it works, in one sentence: 
  
  Time and space complexity, and why: 
  
  One more question:

## Lessons

(One line per attempt. Attempts themselves are logged in learner/attempts.jsonl.)
- 2026-11-05 (a0002, practice, solved): prior: solved once before the coach, after reading a solution (self-reported)
- 2026-11-17 (a0018, review, partial): parked: stage 4 left (why it works + complexity); set-length compare written
