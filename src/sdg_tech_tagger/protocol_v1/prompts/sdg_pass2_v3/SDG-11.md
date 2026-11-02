# SDG pass 2, version 3: the goal text of SDG 11, Sustainable Cities and Communities (proposed, not confirmed, not run)

This file is the source of what the model is told about this goal in SDG pass
2. The wording common to every goal is in `prompts/sdg_pass2_v3.md`, which
also states the registry convention. `scripts/run_sdg_pass2.py --print-prompt
SDG-11` prints the assembled prompt. Only the two fenced blocks count towards
this goal's id, prefix `sdggoal-11`. Neither block may hold a brace.

`GOAL_SCOPE`, first line: the official title of the goal, copied from the
`title` field of the UN Statistics Division SDG API,
`https://unstats.un.org/sdgapi/v1/sdg/Goal/List`, downloaded on 2026-10-08 by
the session that wrote this file (review finding S1). The original prompt
showed the short name only.

This goal has no guidance of its own: `GOAL_SCOPE` holds the official title
and nothing else.

`GOAL_TARGETS`: the 10 targets of the goal, one per line, as the target id,
two spaces, and the `title` field of
`https://unstats.un.org/sdgapi/v1/sdg/Target/List?includechildren=true`,
downloaded on 2026-10-08 by the same session, with runs of whitespace
collapsed to one space. The original prompt took these lines from the Aurora
query files (`query/aurora_sdg_queries/`), which are kept unchanged. Lines
that differ from the Aurora text: 11.4 (typographic quote marks or spacing
only); 11.a (wording). Each is listed with both texts in
`docs/sdg-pass2-v2.md`.
Revision 3: both blocks are character for character those of
`prompts/sdg_pass2_v2/SDG-11.md`, so this goal's id is the same.

## GOAL_SCOPE

```text
Official title: Make cities and human settlements inclusive, safe, resilient and sustainable
```

## GOAL_TARGETS

```text
11.1  By 2030, ensure access for all to adequate, safe and affordable housing and basic services and upgrade slums
11.2  By 2030, provide access to safe, affordable, accessible and sustainable transport systems for all, improving road safety, notably by expanding public transport, with special attention to the needs of those in vulnerable situations, women, children, persons with disabilities and older persons
11.3  By 2030, enhance inclusive and sustainable urbanization and capacity for participatory, integrated and sustainable human settlement planning and management in all countries
11.4  Strengthen efforts to protect and safeguard the world's cultural and natural heritage
11.5  By 2030, significantly reduce the number of deaths and the number of people affected and substantially decrease the direct economic losses relative to global gross domestic product caused by disasters, including water-related disasters, with a focus on protecting the poor and people in vulnerable situations
11.6  By 2030, reduce the adverse per capita environmental impact of cities, including by paying special attention to air quality and municipal and other waste management
11.7  By 2030, provide universal access to safe, inclusive and accessible, green and public spaces, in particular for women and children, older persons and persons with disabilities
11.a  Support positive economic, social and environmental links between urban, peri-urban and rural areas by strengthening national and regional development planning
11.b  By 2020, substantially increase the number of cities and human settlements adopting and implementing integrated policies and plans towards inclusion, resource efficiency, mitigation and adaptation to climate change, resilience to disasters, and develop and implement, in line with the Sendai Framework for Disaster Risk Reduction 2015-2030, holistic disaster risk management at all levels
11.c  Support least developed countries, including through financial and technical assistance, in building sustainable and resilient buildings utilizing local materials
```
