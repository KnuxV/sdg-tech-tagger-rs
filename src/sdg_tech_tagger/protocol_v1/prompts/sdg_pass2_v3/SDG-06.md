# SDG pass 2, version 3: the goal text of SDG 6, Clean Water and Sanitation (proposed, not confirmed, not run)

This file is the source of what the model is told about this goal in SDG pass
2. The wording common to every goal is in `prompts/sdg_pass2_v3.md`, which
also states the registry convention. `scripts/run_sdg_pass2.py --print-prompt
SDG-06` prints the assembled prompt. Only the two fenced blocks count towards
this goal's id, prefix `sdggoal-06`. Neither block may hold a brace.

`GOAL_SCOPE`, first line: the official title of the goal, copied from the
`title` field of the UN Statistics Division SDG API,
`https://unstats.un.org/sdgapi/v1/sdg/Goal/List`, downloaded on 2026-10-08 by
the session that wrote this file (review finding S1). The original prompt
showed the short name only.

This goal has no guidance of its own: `GOAL_SCOPE` holds the official title
and nothing else.

`GOAL_TARGETS`: the 8 targets of the goal, one per line, as the target id, two
spaces, and the `title` field of
`https://unstats.un.org/sdgapi/v1/sdg/Target/List?includechildren=true`,
downloaded on 2026-10-08 by the same session, with runs of whitespace
collapsed to one space. The original prompt took these lines from the Aurora
query files (`query/aurora_sdg_queries/`), which are kept unchanged. All of
them are character for character the Aurora text.
Revision 3: both blocks are character for character those of
`prompts/sdg_pass2_v2/SDG-06.md`, so this goal's id is the same.

## GOAL_SCOPE

```text
Official title: Ensure availability and sustainable management of water and sanitation for all
```

## GOAL_TARGETS

```text
6.1  By 2030, achieve universal and equitable access to safe and affordable drinking water for all
6.2  By 2030, achieve access to adequate and equitable sanitation and hygiene for all and end open defecation, paying special attention to the needs of women and girls and those in vulnerable situations
6.3  By 2030, improve water quality by reducing pollution, eliminating dumping and minimizing release of hazardous chemicals and materials, halving the proportion of untreated wastewater and substantially increasing recycling and safe reuse globally
6.4  By 2030, substantially increase water-use efficiency across all sectors and ensure sustainable withdrawals and supply of freshwater to address water scarcity and substantially reduce the number of people suffering from water scarcity
6.5  By 2030, implement integrated water resources management at all levels, including through transboundary cooperation as appropriate
6.6  By 2020, protect and restore water-related ecosystems, including mountains, forests, wetlands, rivers, aquifers and lakes
6.a  By 2030, expand international cooperation and capacity-building support to developing countries in water- and sanitation-related activities and programmes, including water harvesting, desalination, water efficiency, wastewater treatment, recycling and reuse technologies
6.b  Support and strengthen the participation of local communities in improving water and sanitation management
```
