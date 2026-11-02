# SDG pass 2, version 3: the goal text of SDG 17, Partnerships for the Goals (proposed, not confirmed, not run)

This file is the source of what the model is told about this goal in SDG pass
2. The wording common to every goal is in `prompts/sdg_pass2_v3.md`, which
also states the registry convention. `scripts/run_sdg_pass2.py --print-prompt
SDG-17` prints the assembled prompt. Only the two fenced blocks count towards
this goal's id, prefix `sdggoal-17`. Neither block may hold a brace.

`GOAL_SCOPE`, first line: the official title of the goal, copied from the
`title` field of the UN Statistics Division SDG API,
`https://unstats.un.org/sdgapi/v1/sdg/Goal/List`, downloaded on 2026-10-08 by
the session that wrote this file (review finding S1). The original prompt
showed the short name only.

This goal has no guidance of its own: `GOAL_SCOPE` holds the official title
and nothing else.

`GOAL_TARGETS`: the 19 targets of the goal, one per line, as the target id,
two spaces, and the `title` field of
`https://unstats.un.org/sdgapi/v1/sdg/Target/List?includechildren=true`,
downloaded on 2026-10-08 by the same session, with runs of whitespace
collapsed to one space. The original prompt took these lines from the Aurora
query files (`query/aurora_sdg_queries/`), which are kept unchanged. Lines
that differ from the Aurora text: 17.2 (wording); 17.6 (wording); 17.9
(wording); 17.11 (typographic quote marks or spacing only); 17.15 (typographic
quote marks or spacing only); 17.16 (wording). Each is listed with both texts
in `docs/sdg-pass2-v2.md`.
Revision 3: both blocks are character for character those of
`prompts/sdg_pass2_v2/SDG-17.md`, so this goal's id is the same.

## GOAL_SCOPE

```text
Official title: Strengthen the means of implementation and revitalize the Global Partnership for Sustainable Development
```

## GOAL_TARGETS

```text
17.1  Strengthen domestic resource mobilization, including through international support to developing countries, to improve domestic capacity for tax and other revenue collection
17.2  Developed countries to implement fully their official development assistance commitments, including the commitment by many developed countries to achieve the target of 0.7 per cent of gross national income for official development assistance (ODA/GNI) to developing countries and 0.15 to 0.20 per cent of ODA/GNI to least developed countries; ODA providers are encouraged to consider setting a target to provide at least 0.20 per cent of ODA/GNI to least developed countries
17.3  Mobilize additional financial resources for developing countries from multiple sources
17.4  Assist developing countries in attaining long-term debt sustainability through coordinated policies aimed at fostering debt financing, debt relief and debt restructuring, as appropriate, and address the external debt of highly indebted poor countries to reduce debt distress
17.5  Adopt and implement investment promotion regimes for least developed countries
17.6  Enhance North-South, South-South and triangular regional and international cooperation on and access to science, technology and innovation and enhance knowledge-sharing on mutually agreed terms, including through improved coordination among existing mechanisms, in particular at the United Nations level, and through a global technology facilitation mechanism
17.7  Promote the development, transfer, dissemination and diffusion of environmentally sound technologies to developing countries on favourable terms, including on concessional and preferential terms, as mutually agreed
17.8  Fully operationalize the technology bank and science, technology and innovation capacity-building mechanism for least developed countries by 2017 and enhance the use of enabling technology, in particular information and communications technology
17.9  Enhance international support for implementing effective and targeted capacity-building in developing countries to support national plans to implement all the Sustainable Development Goals, including through North-South, South-South and triangular cooperation
17.10  Promote a universal, rules-based, open, non-discriminatory and equitable multilateral trading system under the World Trade Organization, including through the conclusion of negotiations under its Doha Development Agenda
17.11  Significantly increase the exports of developing countries, in particular with a view to doubling the least developed countries' share of global exports by 2020
17.12  Realize timely implementation of duty-free and quota-free market access on a lasting basis for all least developed countries, consistent with World Trade Organization decisions, including by ensuring that preferential rules of origin applicable to imports from least developed countries are transparent and simple, and contribute to facilitating market access
17.13  Enhance global macroeconomic stability, including through policy coordination and policy coherence
17.14  Enhance policy coherence for sustainable development
17.15  Respect each country's policy space and leadership to establish and implement policies for poverty eradication and sustainable development
17.16  Enhance the Global Partnership for Sustainable Development, complemented by multi-stakeholder partnerships that mobilize and share knowledge, expertise, technology and financial resources, to support the achievement of the Sustainable Development Goals in all countries, in particular developing countries
17.17  Encourage and promote effective public, public-private and civil society partnerships, building on the experience and resourcing strategies of partnerships
17.18  By 2020, enhance capacity-building support to developing countries, including for least developed countries and small island developing States, to increase significantly the availability of high-quality, timely and reliable data disaggregated by income, gender, age, race, ethnicity, migratory status, disability, geographic location and other characteristics relevant in national contexts
17.19  By 2030, build on existing initiatives to develop measurements of progress on sustainable development that complement gross domestic product, and support statistical capacity-building in developing countries
```
