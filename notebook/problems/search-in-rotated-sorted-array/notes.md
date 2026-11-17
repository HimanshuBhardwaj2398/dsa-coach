# search-in-rotated-sorted-array

Link: https://leetcode.com/problems/search-in-rotated-sorted-array/ · Pattern: binary-search · Difficulty: medium · First logged: 2026-11-17

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

### 2026-11-17 (7b14e65e1f4ac39577195804000a1e4e)

- **1. Understand:** Returns the index of target, or -1 if not found. Rotation count is not a parameter; only known to be between 1 and n. Array was originally sorted; all values distinct (coach pointed this out). Rotating n times gives the sorted array back ([1,3,5], target 3 -> 1). Target O(log n); the trivial scan is O(n).
- **2. Find an approach:** Baseline: linear scan, O(n). A rotated sorted array has exactly one drop (none if rotated n times); the halves nums[lo..mid] and nums[mid..hi] share only mid, so the drop sits in at most one half and the other is sorted (unlocked by rung 1: how was the input built?). Which half is sorted: nums[lo] <= nums[mid] -> left (<= because lo == mid in [3,1]); checking nums[mid] vs nums[mid+1] can't decide. Keep left if nums[lo] <= target < nums[mid] (first tried only nums[mid] > target; target=0 broke it); keep right if nums[mid] < target <= nums[hi]. Plan: check nums[mid]==target, find the sorted half, keep the half that can hold target, repeat. Invariant: target, if present, is in nums[lo..hi]; stop when lo > hi, return -1.
- **3. Build it:** class Solution:
      def search(self, nums, target):
          low, high = 0, len(nums) - 1
          while low <= high:
              mid = (low + high) // 2
              if nums[mid] == target:
                  return mid
              if nums[low] <= nums[mid]:              # left half sorted
                  if nums[low] <= target < nums[mid]:
                      high = mid - 1
                  else:
                      low = mid + 1
              else:                                   # right half sorted
                  if nums[mid] < target <= nums[high]:
                      low = mid + 1
                  else:
                      high = mid - 1
          return -1

## Lessons

(One line per attempt. Attempts themselves are logged in learner/attempts.jsonl.)
- 2026-11-17 (a0019, practice, solved): (coach-written) nums[lo] <= nums[mid] means the left half is sorted; keep the half whose range holds target. Relies on distinct values (duplicates: LC 81).
