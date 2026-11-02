# SDG pass 2, version 3: the goal text of SDG 8, Decent Work and Economic Growth (proposed, not confirmed, not run)

This file is the source of what the model is told about this goal in SDG pass
2. The wording common to every goal is in `prompts/sdg_pass2_v3.md`, which
also states the registry convention. `scripts/run_sdg_pass2.py --print-prompt
SDG-08` prints the assembled prompt. Only the two fenced blocks count towards
this goal's id, prefix `sdggoal-08`. Neither block may hold a brace.

`GOAL_SCOPE`, first line: the official title of the goal, copied from the
`title` field of the UN Statistics Division SDG API,
`https://unstats.un.org/sdgapi/v1/sdg/Goal/List`, downloaded on 2026-10-08 by
the session that wrote this file (review finding S1). The original prompt
showed the short name only.

**The second paragraph of `GOAL_SCOPE` is PROPOSED AND NOT CONFIRMED.** It is
new in revision 3 (rule S6 of `docs/classifier-prompts-v3.md`). The sentence
is from section 7 of the annotation protocol of `divergence-validation`,
confirmed by Kevin on 2026-09-18 for that protocol, which was written for
another use, the grading of claims, and not for this pass. To run without it,
delete that paragraph and the blank line before it: the goal's id moves back
to that of revision 2 and no other id moves.

`GOAL_TARGETS`: the 12 targets of the goal, one per line, as the target id,
two spaces, and the `title` field of
`https://unstats.un.org/sdgapi/v1/sdg/Target/List?includechildren=true`,
downloaded on 2026-10-08 by the same session, with runs of whitespace
collapsed to one space. The original prompt took these lines from the Aurora
query files (`query/aurora_sdg_queries/`), which are kept unchanged. Lines
that differ from the Aurora text: 8.4 (wording); 8.a (wording). Each is listed
with both texts in `docs/sdg-pass2-v2.md`.

## GOAL_SCOPE

```text
Official title: Promote sustained, inclusive and sustainable economic growth, full and productive employment and decent work for all

Productivity, performance or competitiveness gains of firms, employment and working conditions, and financial inclusion are within this goal.
```

## GOAL_TARGETS

```text
8.1  Sustain per capita economic growth in accordance with national circumstances and, in particular, at least 7 per cent gross domestic product growth per annum in the least developed countries
8.2  Achieve higher levels of economic productivity through diversification, technological upgrading and innovation, including through a focus on high-value added and labour-intensive sectors
8.3  Promote development-oriented policies that support productive activities, decent job creation, entrepreneurship, creativity and innovation, and encourage the formalization and growth of micro-, small- and medium-sized enterprises, including through access to financial services
8.4  Improve progressively, through 2030, global resource efficiency in consumption and production and endeavour to decouple economic growth from environmental degradation, in accordance with the 10-Year Framework of Programmes on Sustainable Consumption and Production, with developed countries taking the lead
8.5  By 2030, achieve full and productive employment and decent work for all women and men, including for young people and persons with disabilities, and equal pay for work of equal value
8.6  By 2020, substantially reduce the proportion of youth not in employment, education or training
8.7  Take immediate and effective measures to eradicate forced labour, end modern slavery and human trafficking and secure the prohibition and elimination of the worst forms of child labour, including recruitment and use of child soldiers, and by 2025 end child labour in all its forms
8.8  Protect labour rights and promote safe and secure working environments for all workers, including migrant workers, in particular women migrants, and those in precarious employment
8.9  By 2030, devise and implement policies to promote sustainable tourism that creates jobs and promotes local culture and products
8.10  Strengthen the capacity of domestic financial institutions to encourage and expand access to banking, insurance and financial services for all
8.a  Increase Aid for Trade support for developing countries, in particular least developed countries, including through the Enhanced Integrated Framework for Trade-related Technical Assistance to Least Developed Countries
8.b  By 2020, develop and operationalize a global strategy for youth employment and implement the Global Jobs Pact of the International Labour Organization
```
