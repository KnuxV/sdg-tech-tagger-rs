# SDG pass 2, version 3: the goal text of SDG 7, Affordable and Clean Energy (proposed, not confirmed, not run)

This file is the source of what the model is told about this goal in SDG pass
2. The wording common to every goal is in `prompts/sdg_pass2_v3.md`, which
also states the registry convention. `scripts/run_sdg_pass2.py --print-prompt
SDG-07` prints the assembled prompt. Only the two fenced blocks count towards
this goal's id, prefix `sdggoal-07`. Neither block may hold a brace.

`GOAL_SCOPE`, first line: the official title of the goal, copied from the
`title` field of the UN Statistics Division SDG API,
`https://unstats.un.org/sdgapi/v1/sdg/Goal/List`, downloaded on 2026-10-08 by
the session that wrote this file (review finding S1). The original prompt
showed the short name only.

**The second paragraph of `GOAL_SCOPE` is PROPOSED AND NOT CONFIRMED.** It is
new in revision 3 (rule S7 of `docs/classifier-prompts-v3.md`). The sentence
is from section 7 of the annotation protocol of `divergence-validation`,
"Energy saved in any sector counts, not only in the energy sector", which was
written for another use, the grading of claims, and not for this pass. To run
without it, delete that paragraph and the blank line before it: the goal's id
moves back to that of revision 2 and no other id moves.

`GOAL_TARGETS`: the 5 targets of the goal, one per line, as the target id, two
spaces, and the `title` field of
`https://unstats.un.org/sdgapi/v1/sdg/Target/List?includechildren=true`,
downloaded on 2026-10-08 by the same session, with runs of whitespace
collapsed to one space. The original prompt took these lines from the Aurora
query files (`query/aurora_sdg_queries/`), which are kept unchanged. Lines
that differ from the Aurora text: 7.b (wording). Each is listed with both
texts in `docs/sdg-pass2-v2.md`.

## GOAL_SCOPE

```text
Official title: Ensure access to affordable, reliable, sustainable and modern energy for all

Energy saved in any sector is within this goal, not only in the energy sector.
```

## GOAL_TARGETS

```text
7.1  By 2030, ensure universal access to affordable, reliable and modern energy services
7.2  By 2030, increase substantially the share of renewable energy in the global energy mix
7.3  By 2030, double the global rate of improvement in energy efficiency
7.a  By 2030, enhance international cooperation to facilitate access to clean energy research and technology, including renewable energy, energy efficiency and advanced and cleaner fossil-fuel technology, and promote investment in energy infrastructure and clean energy technology
7.b  By 2030, expand infrastructure and upgrade technology for supplying modern and sustainable energy services for all in developing countries, in particular least developed countries, small island developing States and landlocked developing countries, in accordance with their respective programmes of support
```
