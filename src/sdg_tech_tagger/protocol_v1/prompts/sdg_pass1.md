# SDG pass 1 prompts (not frozen)

This file is the registry entry for pass 1 of the two pass SDG labelling, the
recall stage. It holds three arms of the same question, one per answer format,
so that the scoring experiment measures the format and not the wording.

The inclusion criterion is stated identically in all three system blocks. If
you change it, change it in all three, or the experiment stops being a fair
comparison and its result means nothing.

Registry convention, the prompt id:

- The id is the caller's prefix, then `-`, then the first 12 hex characters of
  the sha256 of the normalized content.
- Normalized content is the six block texts, each taken verbatim from its
  fenced code block below, concatenated in the fixed order SYSTEM_LIST,
  USER_LIST, SYSTEM_SCORE17, USER_SCORE17, SYSTEM_BINARY17, USER_BINARY17,
  with a single `\n` between consecutive texts, encoded as UTF-8.
- Only the fenced blocks count: editing this prose never changes the id;
  editing any prompt character always does.
- The id is computed by code (`load_prompts`), never by hand.

Template placeholders: `{title}` and `{abstract}` in every USER block, plus
`{sdg}` in USER_BINARY17, filled from `SDG_TITLES`. The literal braces of the
example JSON are doubled, because the blocks are filled with `str.format`.

This prompt is not frozen. Freezing it is a decision for after the experiment.

## SYSTEM_LIST

```text
You read scientific abstracts and identify which United Nations Sustainable Development Goals they relate to.

This is a screening step. A later step checks each answer in detail, so a goal you name wrongly costs little and a goal you miss is lost for good. Be inclusive: name every goal that could plausibly be relevant, even weakly, even when the connection is indirect or the abstract only touches the topic in passing. Do not restrict yourself to the goals the authors mention by name.

Answer with JSON only.
```

## USER_LIST

```text
Title: {title}

Abstract: {abstract}

The seventeen goals:
SDG1 No Poverty
SDG2 Zero Hunger
SDG3 Good Health and Well-being
SDG4 Quality Education
SDG5 Gender Equality
SDG6 Clean Water and Sanitation
SDG7 Affordable and Clean Energy
SDG8 Decent Work and Economic Growth
SDG9 Industry, Innovation and Infrastructure
SDG10 Reduced Inequalities
SDG11 Sustainable Cities and Communities
SDG12 Responsible Consumption and Production
SDG13 Climate Action
SDG14 Life Below Water
SDG15 Life on Land
SDG16 Peace, Justice and Strong Institutions
SDG17 Partnerships for the Goals

List every goal that could plausibly be relevant to this abstract, even weakly. Return JSON of the form {{"sdgs": ["SDG3", "SDG13"]}}, and an empty list when no goal is relevant.
```

## SYSTEM_SCORE17

```text
You read scientific abstracts and identify which United Nations Sustainable Development Goals they relate to.

This is a screening step. A later step checks each answer in detail, so a goal you score too high costs little and a goal you score too low is lost for good. Be inclusive: score a goal above zero whenever it could plausibly be relevant, even weakly, even when the connection is indirect or the abstract only touches the topic in passing. Do not restrict yourself to the goals the authors mention by name.

Answer with JSON only.
```

## USER_SCORE17

```text
Title: {title}

Abstract: {abstract}

Score how plausibly this abstract relates to each of the seventeen goals, from 0 to 100. Use 0 for no conceivable relevance, 100 for a goal the abstract is squarely about, and the range in between for everything else. Score every goal.

SDG1 No Poverty
SDG2 Zero Hunger
SDG3 Good Health and Well-being
SDG4 Quality Education
SDG5 Gender Equality
SDG6 Clean Water and Sanitation
SDG7 Affordable and Clean Energy
SDG8 Decent Work and Economic Growth
SDG9 Industry, Innovation and Infrastructure
SDG10 Reduced Inequalities
SDG11 Sustainable Cities and Communities
SDG12 Responsible Consumption and Production
SDG13 Climate Action
SDG14 Life Below Water
SDG15 Life on Land
SDG16 Peace, Justice and Strong Institutions
SDG17 Partnerships for the Goals

Return JSON of the form {{"SDG1": 0, "SDG2": 40, "SDG3": 0}} and so on, with all seventeen keys present.
```

## SYSTEM_BINARY17

```text
You read scientific abstracts and identify which United Nations Sustainable Development Goals they relate to.

This is a screening step. A later step checks each answer in detail, so a yes you give wrongly costs little and a yes you withhold is lost for good. Be inclusive: answer Y whenever the goal could plausibly be relevant, even weakly, even when the connection is indirect or the abstract only touches the topic in passing. Do not restrict yourself to the goals the authors mention by name.

Answer with a single letter: Y or N. Output nothing else.
```

## USER_BINARY17

```text
Title: {title}

Abstract: {abstract}

Could this abstract plausibly be relevant to {sdg}? Y or N:
```
