# SDG pass 2, version 3: the goal text of SDG 2, Zero Hunger (proposed, not confirmed, not run)

This file is the source of what the model is told about this goal in SDG pass
2. The wording common to every goal is in `prompts/sdg_pass2_v3.md`, which
also states the registry convention. `scripts/run_sdg_pass2.py --print-prompt
SDG-02` prints the assembled prompt. Only the two fenced blocks count towards
this goal's id, prefix `sdggoal-02`. Neither block may hold a brace.

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
`prompts/sdg_pass2_v2/SDG-02.md`, so this goal's id is the same.

## GOAL_SCOPE

```text
Official title: End hunger, achieve food security and improved nutrition and promote sustainable agriculture
```

## GOAL_TARGETS

```text
2.1  By 2030, end hunger and ensure access by all people, in particular the poor and people in vulnerable situations, including infants, to safe, nutritious and sufficient food all year round
2.2  By 2030, end all forms of malnutrition, including achieving, by 2025, the internationally agreed targets on stunting and wasting in children under 5 years of age, and address the nutritional needs of adolescent girls, pregnant and lactating women and older persons
2.3  By 2030, double the agricultural productivity and incomes of small-scale food producers, in particular women, indigenous peoples, family farmers, pastoralists and fishers, including through secure and equal access to land, other productive resources and inputs, knowledge, financial services, markets and opportunities for value addition and non-farm employment
2.4  By 2030, ensure sustainable food production systems and implement resilient agricultural practices that increase productivity and production, that help maintain ecosystems, that strengthen capacity for adaptation to climate change, extreme weather, drought, flooding and other disasters and that progressively improve land and soil quality
2.5  By 2020, maintain the genetic diversity of seeds, cultivated plants and farmed and domesticated animals and their related wild species, including through soundly managed and diversified seed and plant banks at the national, regional and international levels, and promote access to and fair and equitable sharing of benefits arising from the utilization of genetic resources and associated traditional knowledge, as internationally agreed
2.a  Increase investment, including through enhanced international cooperation, in rural infrastructure, agricultural research and extension services, technology development and plant and livestock gene banks in order to enhance agricultural productive capacity in developing countries, in particular least developed countries
2.b  Correct and prevent trade restrictions and distortions in world agricultural markets, including through the parallel elimination of all forms of agricultural export subsidies and all export measures with equivalent effect, in accordance with the mandate of the Doha Development Round
2.c  Adopt measures to ensure the proper functioning of food commodity markets and their derivatives and facilitate timely access to market information, including on food reserves, in order to help limit extreme food price volatility
```
