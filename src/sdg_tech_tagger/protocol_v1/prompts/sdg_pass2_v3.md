# SDG pass 2 prompt, version 3 (proposed, not confirmed, not run)

This file is the template of SDG pass 2: one call per (work, goal) pair that
SDG pass 1 scored at or above the threshold, one token of answer, `Y` or `N`.
It holds the wording that is the same for every goal. What the model is told
about one goal (its official title, any guidance for that goal, its targets)
is in that goal's file, `prompts/sdg_pass2_v3/SDG-01.md` to `SDG-17.md`.

**Which file is the source of what.** Each piece of wording has one source and
no copy:

- the system block and the frame of the user block: this file;
- the goal's text: the goal's file.

Nothing is generated from either. `scripts/run_sdg_pass2.py` assembles the
two at run time, and `scripts/run_sdg_pass2.py --print-prompt SDG-09` prints
exactly what the model receives for that goal.

**Status.** Proposed by an implementation session, not confirmed by Kevin,
not run. This is revision 3. It starts from `prompts/sdg_pass2_v2.md`, which
is kept unchanged with the seventeen files of `prompts/sdg_pass2_v2/` as the
record of what was piloted, and applies rules S1 to S3 of
`docs/classifier-prompts-v3.md`, which lists the old and the new text of
each. The rules come from the review
`docs/reports/2026-10-08-sdg-pass2-v2-review.md` (findings M1 and M3) and
from the annotation protocol of `divergence-validation`. What revision 2
changed against `prompts/sdg_pass2.md` is in `docs/sdg-pass2-v2.md`.

The construct is not changed, and is now stated once in `SYSTEM_PASS2`:
relevant means that what the work studies falls within what the goal covers,
as its official title and targets state it; `Y` or `N`; nothing about
contribution and nothing about direction (benefit or harm), which the block
now says in words (S3). The overlap of goals is no longer a reason for `N`
(S1): a pair is judged on its own goal. The paragraph on the screening step
is the original's apart from its last sentence (S2). `USER_PASS2` is
character for character that of revision 2. Kevin reads `SYSTEM_PASS2`
before any run.

Registry convention, the prompt id:

- The template id is `sdgp2-` then the first 12 hex characters of the sha256
  of the two block texts, `SYSTEM_PASS2` then `USER_PASS2`, joined by a
  single `\n`, encoded as UTF-8 (`load_prompts` with `PASS2_PROMPT_KEYS`).
  Only the fenced blocks count.
- A row's `prompt_id` is `<template id>+<goal id>`, the goal id being
  computed the same way from the goal's file with the prefix
  `sdggoal-<two digits>`. Editing this file moves all seventeen ids; editing
  one goal's file moves that goal's id only.
- The ids are computed by code, never by hand. Unlike the original, the id
  covers the target texts, because they are written in the goal files.

Template placeholders. `SYSTEM_PASS2` is sent as it stands and takes none.
`USER_PASS2` takes exactly `{title}`, `{abstract}`, `{goal}`, `{scope}` and
`{targets}`:

- `{goal}` is the short name pass 1 uses, `SDG 13, Climate Action`
  (`sdg_pass2.goal_name`);
- `{scope}` is the goal file's `GOAL_SCOPE` block;
- `{targets}` is the goal file's `GOAL_TARGETS` block;
- `{title}` and `{abstract}` are the work's, filled per call.

A literal brace in `USER_PASS2` is doubled. A goal file's blocks hold no
brace at all; the runner refuses one.

Decision numbers. The original file cites D022 with no repository named, and
the copied modules and contract cite D018, D021 and D022. Those are entries
of the earlier repository,
`scientific-publication-retrieval-2023-2025`, not of this one.

## SYSTEM_PASS2

```text
You decide whether a scholarly work, read through its title and abstract, is relevant to one United Nations Sustainable Development Goal.

A screening step has already proposed this goal, and that step was told to be inclusive: it names a goal whenever the connection is merely plausible. Your job is to check that proposal against the goal's own text, without leaning either way.

Relevant means that what the work studies falls within what the goal covers, as its official title and targets state it. It does not matter whether the work helps the goal, harms it or only measures it, and it does not matter whether the authors mention the goals.

Answer Y when the work is relevant in that sense; it does not have to address a target in full or be framed as sustainability research.

Answer N when the connection is only a passing mention, a keyword that happens to match in an unrelated technical sense, a generic claim of societal or economic benefit, or a topic that this goal, as stated below, does not cover. A work can be relevant to several goals: judge this goal on its own, whatever other goals the work may also fit.

Judge only from the title and the abstract as written, not what the work might one day enable. The abstract may hold other text, such as a table of contents: judge what is there.

Answer with a single letter: Y or N. Output nothing else.
```

## USER_PASS2

```text
Title: {title}

Abstract: {abstract}

The goal is {goal}.
{scope}

These are its targets:

{targets}

Is this work relevant to {goal}? Y or N:
```
