# SDG pass 2, version 3: the goal text of SDG 9, Industry, Innovation and Infrastructure (proposed, not confirmed, not run)

This file is the source of what the model is told about this goal in SDG pass
2. The wording common to every goal is in `prompts/sdg_pass2_v3.md`, which
also states the registry convention. `scripts/run_sdg_pass2.py --print-prompt
SDG-09` prints the assembled prompt. Only the two fenced blocks count towards
this goal's id, prefix `sdggoal-09`. Neither block may hold a brace.

`GOAL_SCOPE`, first line: the official title of the goal, copied from the
`title` field of the UN Statistics Division SDG API,
`https://unstats.un.org/sdgapi/v1/sdg/Goal/List`, downloaded on 2026-10-08 by
the session that wrote this file (review finding S1). The original prompt
showed the short name only.

**The second paragraph of `GOAL_SCOPE` is PROPOSED AND NOT CONFIRMED.** It
embodies a research choice that is Kevin's: what SDG 9 means in a pool where
every work is about, or mentions, a digital technology. Revision 3 replaces
the narrow reading of revision 2 by a middle reading (rule S4 of
`docs/classifier-prompts-v3.md`): a work whose subject or application area is
industry, public infrastructure, enterprise finance, innovation or access to
ICT is within the goal, and a work on computing or network technology for its
own sake is not. Its first sentence is a fact of the pool (D021,
`docs/gate-v2.md` section 1); the rest is the choice. The narrow reading and
the alternatives are in `docs/sdg-pass2-v2.md`, question K1, and in review
finding M2 of `docs/reports/2026-10-08-sdg-pass2-v2-review.md`. To run
without it, delete that paragraph and the blank line before it: the goal's id
moves and no other.

`GOAL_TARGETS`: the 8 targets of the goal, one per line, as the target id, two
spaces, and the `title` field of
`https://unstats.un.org/sdgapi/v1/sdg/Target/List?includechildren=true`,
downloaded on 2026-10-08 by the same session, with runs of whitespace
collapsed to one space. The original prompt took these lines from the Aurora
query files (`query/aurora_sdg_queries/`), which are kept unchanged. Lines
that differ from the Aurora text: 9.1 (wording); 9.2 (typographic quote marks
or spacing only). Each is listed with both texts in `docs/sdg-pass2-v2.md`.

## GOAL_SCOPE

```text
Official title: Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation

Every work you will see is about, or mentions, a digital technology. Developing, improving or applying a technology is not by itself relevant to this goal. Answer Y when the work's subject or application area is industry or industrial production, infrastructure that serves the public (transport, energy, water, communications), the access of enterprises to finance and markets, research and innovation capacity or policy, or people's access to information and communications technology. A work on computing or network technology for its own sake, such as a faster algorithm, a cloud scheduler or a protocol, is N.
```

## GOAL_TARGETS

```text
9.1  Develop quality, reliable, sustainable and resilient infrastructure, including regional and trans-border infrastructure, to support economic development and human well-being, with a focus on affordable and equitable access for all
9.2  Promote inclusive and sustainable industrialization and, by 2030, significantly raise industry's share of employment and gross domestic product, in line with national circumstances, and double its share in least developed countries
9.3  Increase the access of small-scale industrial and other enterprises, in particular in developing countries, to financial services, including affordable credit, and their integration into value chains and markets
9.4  By 2030, upgrade infrastructure and retrofit industries to make them sustainable, with increased resource-use efficiency and greater adoption of clean and environmentally sound technologies and industrial processes, with all countries taking action in accordance with their respective capabilities
9.5  Enhance scientific research, upgrade the technological capabilities of industrial sectors in all countries, in particular developing countries, including, by 2030, encouraging innovation and substantially increasing the number of research and development workers per 1 million people and public and private research and development spending
9.a  Facilitate sustainable and resilient infrastructure development in developing countries through enhanced financial, technological and technical support to African countries, least developed countries, landlocked developing countries and small island developing States
9.b  Support domestic technology development, research and innovation in developing countries, including by ensuring a conducive policy environment for, inter alia, industrial diversification and value addition to commodities
9.c  Significantly increase access to information and communications technology and strive to provide universal and affordable access to the Internet in least developed countries by 2020
```
