# Evil Cube Solver Report

Date: 2026-06-23

Target model: https://www.printables.com/model/1339793-evil-cube

## Summary

This project produced a working exact-cover solver for the regular Evil Cube
and found a valid 4x4x4 packing. It also added two counters:

- a fast labelled Algorithm X / DLX-style counter
- a slower raw counter that treats identical pieces as indistinguishable

The important counting result so far is not a final total. The long run was
stopped by request before completion. The last saved checkpoint was:

```text
heartbeat labelled_solutions=20172 nodes=16601797 depth=8 active_columns=26 elapsed_seconds=2940.0
```

That is 20,172 labelled completions after 2,940 solver seconds, not 20,172
physical Evil Cube solutions.

## Valid Solution Found

One valid solution was written to `evil_cube_solution.txt`.

```text
z=0
S4 B3 B3 B1
S4 B3 B2 B2
L1 S3 B2 B2
L1 L1 B2 R1

z=1
B3 B3 B3 B1
S4 S4 B1 B1
S4 S3 S3 B2
L1 S3 S2 R1

z=2
A2 A2 A2 B1
A1 A2 S1 B1
A1 S2 S3 Z1
L1 S2 S2 R1

z=3
A2 A2 S1 S1
A1 S1 S1 Z1
A1 A1 Z1 Z1
A1 S2 Z1 R1
```

The piece inventory is:

```text
Z1       one Z brick
S1-S4    four S bricks
R1       one R brick
L1       one L brick
A1-A2    two A bricks
B1-B3    three B bricks
```

## Shape Definitions

The solver uses normalized unit-cube coordinates embedded in
`solve_evil_cube.py`.

Volumes:

```text
A = 6
B = 6
L = 5
R = 4
S = 5
Z = 5
```

Inventory volume:

```text
1*Z + 4*S + 1*R + 1*L + 2*A + 3*B
= 5 + 20 + 4 + 5 + 12 + 18
= 64
```

That exactly matches a 4x4x4 cube.

## Counting Conventions

The regular Evil Cube has repeated pieces:

```text
S appears 4 times
A appears 2 times
B appears 3 times
```

The labelled DLX counter treats those repeated pieces as separate instances.
The duplicate labelling factor is:

```text
4! * 2! * 3! = 288
```

Therefore, labelled counts are much larger than physical puzzle counts. A
completed labelled count can be divided by 288 to get the fixed-cube physical
count, assuming the whole labelled traversal has completed.

Partial labelled counts should not be divided by 288. A stopped traversal can
end midway through a group of duplicate-labelled versions of the same physical
solution.

## Ten-Minute DLX Run

Command:

```powershell
python .\count_evil_cube_dlx.py --progress-every 1000 --heartbeat-seconds 30 --progress-file evil_cube_dlx_10min_progress.txt
```

At the 600-second checkpoint:

```text
heartbeat labelled_solutions=3876 nodes=3546104 depth=9 active_columns=19 elapsed_seconds=600.0
```

The process was stopped after the next polling interval, so the final saved
line in that file was:

```text
heartbeat labelled_solutions=4080 nodes=3710452 depth=8 active_columns=26 elapsed_seconds=630.0
```

Interpretation:

- `4080` is a partial labelled completion count.
- It is not a physical solution count.
- It is not directly comparable with a designer-published count such as 120.

## Stopped Longer Run

The requested one-hour run was started with:

```powershell
python .\count_evil_cube_dlx.py --progress-every 1000 --heartbeat-seconds 60 --progress-file evil_cube_dlx_1hour_progress.txt
```

The user then requested that the run be ended before a full hour had elapsed.
The last saved progress line was:

```text
heartbeat labelled_solutions=20172 nodes=16601797 depth=8 active_columns=26 elapsed_seconds=2940.0
```

This means:

- elapsed solver time: 2,940 seconds, or 49 minutes
- labelled completions found so far: 20,172
- search nodes visited: 16,601,797
- the search was still incomplete

The process was stopped cleanly after this checkpoint.

## Why The Big Labelled Counts Do Not Contradict 120

The designer's published number, reported as 120, is almost certainly using a
different counting convention than the partial labelled DLX counter.

The DLX count is inflated because identical pieces are labelled:

```text
S1, S2, S3, S4
A1, A2
B1, B2, B3
```

Many of those labelled completions describe the same physical assembly after
renaming identical pieces. A complete labelled count needs to be divided by 288
to collapse those labels. A partial labelled count cannot safely be converted
that way.

There is also the issue of cube rotations. A fixed-cube count treats rotated
copies as different unless they are explicitly divided out. A unique-up-to-cube
rotation count usually divides by 24 after a complete fixed-cube count.

So these are different layers:

```text
labelled completions
fixed-cube physical completions
unique completions up to cube rotation
published/designer presentation convention
```

The scripts now make those distinctions explicit.

## Current Confidence

High confidence:

- the embedded piece volumes sum to 64
- the exact-cover solver finds a valid complete packing
- the progress reporting survives stopped/timeout runs
- the DLX count is labelled, not physical

Lower confidence until a full count completes:

- the total number of fixed-cube physical solutions
- the total number of unique solutions up to cube rotation
- whether the designer's 120 maps exactly to fixed-cube, rotationally unique,
  or another convention

## Recommended Next Work

The next useful step is not just running longer. It is improving the counter so
that partial runs report physical solution families.

Good next changes:

1. Add canonicalization to the DLX counter so it can report unique physical
   solutions progressively.
2. Add symmetry breaking so whole-cube rotations are removed during search
   rather than after the fact.
3. Add resumable checkpoints for multi-hour counts.
4. Add a validation mode that replays each reported solution and confirms every
   cell is covered exactly once.
5. Compare a completed unique count with the designer's 120.

## Files

Source files:

```text
solve_evil_cube.py
count_evil_cube_dlx.py
count_evil_cube_solutions.py
```

Result files:

```text
evil_cube_solution.txt
evil_cube_dlx_10min_progress.txt
evil_cube_dlx_1hour_progress.txt
```

Only the source, README, report, and one compact solution text file need to live
in Git. The progress logs are useful locally but should generally remain
ignored unless a specific run needs to be archived.
