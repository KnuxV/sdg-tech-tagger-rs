# SDG pass 2, version 3: the goal text of SDG 5, Gender Equality (proposed, not confirmed, not run)

This file is the source of what the model is told about this goal in SDG pass
2. The wording common to every goal is in `prompts/sdg_pass2_v3.md`, which
also states the registry convention. `scripts/run_sdg_pass2.py --print-prompt
SDG-05` prints the assembled prompt. Only the two fenced blocks count towards
this goal's id, prefix `sdggoal-05`. Neither block may hold a brace.

`GOAL_SCOPE`, first line: the official title of the goal, copied from the
`title` field of the UN Statistics Division SDG API,
`https://unstats.un.org/sdgapi/v1/sdg/Goal/List`, downloaded on 2026-10-08 by
the session that wrote this file (review finding S1). The original prompt
showed the short name only.

This goal has no guidance of its own: `GOAL_SCOPE` holds the official title
and nothing else.

`GOAL_TARGETS`: the 9 targets of the goal, one per line, as the target id, two
spaces, and the `title` field of
`https://unstats.un.org/sdgapi/v1/sdg/Target/List?includechildren=true`,
downloaded on 2026-10-08 by the same session, with runs of whitespace
collapsed to one space. The original prompt took these lines from the Aurora
query files (`query/aurora_sdg_queries/`), which are kept unchanged. Lines
that differ from the Aurora text: 5.5 (typographic quote marks or spacing
only). Each is listed with both texts in `docs/sdg-pass2-v2.md`.
Revision 3: both blocks are character for character those of
`prompts/sdg_pass2_v2/SDG-05.md`, so this goal's id is the same.

## GOAL_SCOPE

```text
Official title: Achieve gender equality and empower all women and girls
```

## GOAL_TARGETS

```text
5.1  End all forms of discrimination against all women and girls everywhere
5.2  Eliminate all forms of violence against all women and girls in the public and private spheres, including trafficking and sexual and other types of exploitation
5.3  Eliminate all harmful practices, such as child, early and forced marriage and female genital mutilation
5.4  Recognize and value unpaid care and domestic work through the provision of public services, infrastructure and social protection policies and the promotion of shared responsibility within the household and the family as nationally appropriate
5.5  Ensure women's full and effective participation and equal opportunities for leadership at all levels of decision-making in political, economic and public life
5.6  Ensure universal access to sexual and reproductive health and reproductive rights as agreed in accordance with the Programme of Action of the International Conference on Population and Development and the Beijing Platform for Action and the outcome documents of their review conferences
5.a  Undertake reforms to give women equal rights to economic resources, as well as access to ownership and control over land and other forms of property, financial services, inheritance and natural resources, in accordance with national laws
5.b  Enhance the use of enabling technology, in particular information and communications technology, to promote the empowerment of women
5.c  Adopt and strengthen sound policies and enforceable legislation for the promotion of gender equality and the empowerment of all women and girls at all levels
```
