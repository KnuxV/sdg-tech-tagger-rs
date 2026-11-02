# SDG pass 2, version 3: the goal text of SDG 3, Good Health and Well-being (proposed, not confirmed, not run)

This file is the source of what the model is told about this goal in SDG pass
2. The wording common to every goal is in `prompts/sdg_pass2_v3.md`, which
also states the registry convention. `scripts/run_sdg_pass2.py --print-prompt
SDG-03` prints the assembled prompt. Only the two fenced blocks count towards
this goal's id, prefix `sdggoal-03`. Neither block may hold a brace.

`GOAL_SCOPE`, first line: the official title of the goal, copied from the
`title` field of the UN Statistics Division SDG API,
`https://unstats.un.org/sdgapi/v1/sdg/Goal/List`, downloaded on 2026-10-08 by
the session that wrote this file (review finding S1). The original prompt
showed the short name only.

This goal has no guidance of its own: `GOAL_SCOPE` holds the official title
and nothing else.

`GOAL_TARGETS`: the 13 targets of the goal, one per line, as the target id,
two spaces, and the `title` field of
`https://unstats.un.org/sdgapi/v1/sdg/Target/List?includechildren=true`,
downloaded on 2026-10-08 by the same session, with runs of whitespace
collapsed to one space. The original prompt took these lines from the Aurora
query files (`query/aurora_sdg_queries/`), which are kept unchanged. All of
them are character for character the Aurora text.
Revision 3: both blocks are character for character those of
`prompts/sdg_pass2_v2/SDG-03.md`, so this goal's id is the same.

## GOAL_SCOPE

```text
Official title: Ensure healthy lives and promote well-being for all at all ages
```

## GOAL_TARGETS

```text
3.1  By 2030, reduce the global maternal mortality ratio to less than 70 per 100,000 live births
3.2  By 2030, end preventable deaths of newborns and children under 5 years of age, with all countries aiming to reduce neonatal mortality to at least as low as 12 per 1,000 live births and under-5 mortality to at least as low as 25 per 1,000 live births
3.3  By 2030, end the epidemics of AIDS, tuberculosis, malaria and neglected tropical diseases and combat hepatitis, water-borne diseases and other communicable diseases
3.4  By 2030, reduce by one third premature mortality from non-communicable diseases through prevention and treatment and promote mental health and well-being
3.5  Strengthen the prevention and treatment of substance abuse, including narcotic drug abuse and harmful use of alcohol
3.6  By 2020, halve the number of global deaths and injuries from road traffic accidents
3.7  By 2030, ensure universal access to sexual and reproductive health-care services, including for family planning, information and education, and the integration of reproductive health into national strategies and programmes
3.8  Achieve universal health coverage, including financial risk protection, access to quality essential health-care services and access to safe, effective, quality and affordable essential medicines and vaccines for all
3.9  By 2030, substantially reduce the number of deaths and illnesses from hazardous chemicals and air, water and soil pollution and contamination
3.a  Strengthen the implementation of the World Health Organization Framework Convention on Tobacco Control in all countries, as appropriate
3.b  Support the research and development of vaccines and medicines for the communicable and non-communicable diseases that primarily affect developing countries, provide access to affordable essential medicines and vaccines, in accordance with the Doha Declaration on the TRIPS Agreement and Public Health, which affirms the right of developing countries to use to the full the provisions in the Agreement on Trade-Related Aspects of Intellectual Property Rights regarding flexibilities to protect public health, and, in particular, provide access to medicines for all
3.c  Substantially increase health financing and the recruitment, development, training and retention of the health workforce in developing countries, especially in least developed countries and small island developing States
3.d  Strengthen the capacity of all countries, in particular developing countries, for early warning, risk reduction and management of national and global health risks
```
