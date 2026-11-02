# SDG pass 2, version 3: the goal text of SDG 16, Peace, Justice and Strong Institutions (proposed, not confirmed, not run)

This file is the source of what the model is told about this goal in SDG pass
2. The wording common to every goal is in `prompts/sdg_pass2_v3.md`, which
also states the registry convention. `scripts/run_sdg_pass2.py --print-prompt
SDG-16` prints the assembled prompt. Only the two fenced blocks count towards
this goal's id, prefix `sdggoal-16`. Neither block may hold a brace.

`GOAL_SCOPE`, first line: the official title of the goal, copied from the
`title` field of the UN Statistics Division SDG API,
`https://unstats.un.org/sdgapi/v1/sdg/Goal/List`, downloaded on 2026-10-08 by
the session that wrote this file (review finding S1). The original prompt
showed the short name only.

This goal has no guidance of its own: `GOAL_SCOPE` holds the official title
and nothing else.

`GOAL_TARGETS`: the 12 targets of the goal, one per line, as the target id,
two spaces, and the `title` field of
`https://unstats.un.org/sdgapi/v1/sdg/Target/List?includechildren=true`,
downloaded on 2026-10-08 by the same session, with runs of whitespace
collapsed to one space. The original prompt took these lines from the Aurora
query files (`query/aurora_sdg_queries/`), which are kept unchanged. All of
them are character for character the Aurora text.
Revision 3: both blocks are character for character those of
`prompts/sdg_pass2_v2/SDG-16.md`, so this goal's id is the same.

## GOAL_SCOPE

```text
Official title: Promote peaceful and inclusive societies for sustainable development, provide access to justice for all and build effective, accountable and inclusive institutions at all levels
```

## GOAL_TARGETS

```text
16.1  Significantly reduce all forms of violence and related death rates everywhere
16.2  End abuse, exploitation, trafficking and all forms of violence against and torture of children
16.3  Promote the rule of law at the national and international levels and ensure equal access to justice for all
16.4  By 2030, significantly reduce illicit financial and arms flows, strengthen the recovery and return of stolen assets and combat all forms of organized crime
16.5  Substantially reduce corruption and bribery in all their forms
16.6  Develop effective, accountable and transparent institutions at all levels
16.7  Ensure responsive, inclusive, participatory and representative decision-making at all levels
16.8  Broaden and strengthen the participation of developing countries in the institutions of global governance
16.9  By 2030, provide legal identity for all, including birth registration
16.10  Ensure public access to information and protect fundamental freedoms, in accordance with national legislation and international agreements
16.a  Strengthen relevant national institutions, including through international cooperation, for building capacity at all levels, in particular in developing countries, to prevent violence and combat terrorism and crime
16.b  Promote and enforce non-discriminatory laws and policies for sustainable development
```
