# SDG pass 2, version 3: the goal text of SDG 10, Reduced Inequalities (proposed, not confirmed, not run)

This file is the source of what the model is told about this goal in SDG pass
2. The wording common to every goal is in `prompts/sdg_pass2_v3.md`, which
also states the registry convention. `scripts/run_sdg_pass2.py --print-prompt
SDG-10` prints the assembled prompt. Only the two fenced blocks count towards
this goal's id, prefix `sdggoal-10`. Neither block may hold a brace.

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
query files (`query/aurora_sdg_queries/`), which are kept unchanged. All of
them are character for character the Aurora text.
Revision 3: both blocks are character for character those of
`prompts/sdg_pass2_v2/SDG-10.md`, so this goal's id is the same.

## GOAL_SCOPE

```text
Official title: Reduce inequality within and among countries
```

## GOAL_TARGETS

```text
10.1  By 2030, progressively achieve and sustain income growth of the bottom 40 per cent of the population at a rate higher than the national average
10.2  By 2030, empower and promote the social, economic and political inclusion of all, irrespective of age, sex, disability, race, ethnicity, origin, religion or economic or other status
10.3  Ensure equal opportunity and reduce inequalities of outcome, including by eliminating discriminatory laws, policies and practices and promoting appropriate legislation, policies and action in this regard
10.4  Adopt policies, especially fiscal, wage and social protection policies, and progressively achieve greater equality
10.5  Improve the regulation and monitoring of global financial markets and institutions and strengthen the implementation of such regulations
10.6  Ensure enhanced representation and voice for developing countries in decision-making in global international economic and financial institutions in order to deliver more effective, credible, accountable and legitimate institutions
10.7  Facilitate orderly, safe, regular and responsible migration and mobility of people, including through the implementation of planned and well-managed migration policies
10.a  Implement the principle of special and differential treatment for developing countries, in particular least developed countries, in accordance with World Trade Organization agreements
10.b  Encourage official development assistance and financial flows, including foreign direct investment, to States where the need is greatest, in particular least developed countries, African countries, small island developing States and landlocked developing countries, in accordance with their national plans and programmes
10.c  By 2030, reduce to less than 3 per cent the transaction costs of migrant remittances and eliminate remittance corridors with costs higher than 5 per cent
```
