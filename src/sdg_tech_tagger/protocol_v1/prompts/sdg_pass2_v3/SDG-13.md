# SDG pass 2, version 3: the goal text of SDG 13, Climate Action (proposed, not confirmed, not run)

This file is the source of what the model is told about this goal in SDG pass
2. The wording common to every goal is in `prompts/sdg_pass2_v3.md`, which
also states the registry convention. `scripts/run_sdg_pass2.py --print-prompt
SDG-13` prints the assembled prompt. Only the two fenced blocks count towards
this goal's id, prefix `sdggoal-13`. Neither block may hold a brace.

`GOAL_SCOPE`, first line: the official title of the goal, copied from the
`title` field of the UN Statistics Division SDG API,
`https://unstats.un.org/sdgapi/v1/sdg/Goal/List`, downloaded on 2026-10-08 by
the session that wrote this file (review finding S1). The original prompt
showed the short name only.

**The second paragraph of `GOAL_SCOPE` is PROPOSED AND NOT CONFIRMED.** It
embodies a research choice that is Kevin's: whether research on the mitigation
of climate change is within SDG 13 although none of the five targets names
emission reduction. The text is the sentence review finding M4 drafts,
shortened. Revision 3 adds its last two sentences (rule S5 of
`docs/classifier-prompts-v3.md`, from rule N1 and section 7 of the annotation
protocol of `divergence-validation`): emission reduction is within the goal
without the word climate, energy saving alone is not. The alternatives are in
`docs/sdg-pass2-v2.md`, question K2. To run
without it, delete that paragraph and the blank line before it: the goal's id
moves and no other.

`GOAL_TARGETS`: the 5 targets of the goal, one per line, as the target id, two
spaces, and the `title` field of
`https://unstats.un.org/sdgapi/v1/sdg/Target/List?includechildren=true`,
downloaded on 2026-10-08 by the same session, with runs of whitespace
collapsed to one space. The original prompt took these lines from the Aurora
query files (`query/aurora_sdg_queries/`), which are kept unchanged. Lines
that differ from the Aurora text: 13.a (wording); 13.b (wording). Each is
listed with both texts in `docs/sdg-pass2-v2.md`. Aurora's `13.0`, a catch-all
query for climate research with no target text, is not a UN target and is not
shown, as in the original.

## GOAL_SCOPE

```text
Official title: Take urgent action to combat climate change and its impacts

A work on the mitigation of climate change, including the reduction of greenhouse gas emissions, or on adaptation to climate change, is within this goal even where no target below names it. Reducing greenhouse gas or carbon emissions is within this goal whether or not the text names climate. Saving energy with no statement about emissions or climate is not.
```

## GOAL_TARGETS

```text
13.1  Strengthen resilience and adaptive capacity to climate-related hazards and natural disasters in all countries
13.2  Integrate climate change measures into national policies, strategies and planning
13.3  Improve education, awareness-raising and human and institutional capacity on climate change mitigation, adaptation, impact reduction and early warning
13.a  Implement the commitment undertaken by developed-country parties to the United Nations Framework Convention on Climate Change to a goal of mobilizing jointly $100 billion annually by 2020 from all sources to address the needs of developing countries in the context of meaningful mitigation actions and transparency on implementation and fully operationalize the Green Climate Fund through its capitalization as soon as possible
13.b  Promote mechanisms for raising capacity for effective climate change-related planning and management in least developed countries and small island developing States, including focusing on women, youth and local and marginalized communities
```
