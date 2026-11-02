# ADT pass 1 prompt, version 3 (proposed, not confirmed)

This file is the template of ADT pass 1, the recall stage of the ADT
labelling: one call per work scores each of the six advanced digital
technologies from 0 to 100. See `docs/adt-passes-v2.md`, and
`docs/adt-pass2-contract.md`, "ADT pass 1", for the stage itself.

Registry convention, the prompt id:

- The template id is `adtp1-` then the first 12 hex characters of the sha256
  of the block texts, SYSTEM_ADT_SCORE then USER_ADT_SCORE, joined by a
  single `\n`, encoded as UTF-8. Only the fenced blocks count.
- A row's `prompt_id` is `<template id>+<descriptions id>`, the second from
  the descriptions file with prefix `adtdesc` and all six keys. The ids are
  computed by code (`load_prompts`), never by hand.

Template placeholders: `{descriptions}` in SYSTEM_ADT_SCORE, filled once per
run from the descriptions file; `{title}` and `{abstract}` in
USER_ADT_SCORE. The literal braces of any example JSON are doubled, because
the blocks are filled with `str.format`. The JSON key the model answers under
is the code itself (`AI`, `IOT`, `COMPUTING_INFRASTRUCTURE`, `BLOCKCHAIN`,
`ROBOTICS`, `ADDITIVE_MANUFACTURING`).

This file is revision 3 of the template. It starts from
`prompts/adt_pass1_v2.md`, which is kept unchanged as the record of what was
piloted, and changes two things, listed with the old and the new text in
`docs/classifier-prompts-v3.md`: the top anchor of the scale, which is now
presence and not centrality (rule R13, review finding F6 of
`docs/reports/2026-10-08-adt-passes-v2-review.md`), and three warnings of the
homonym line that could zero a real instance (rule R14, finding F7). What
revision 2 changed against `prompts/adt_pass1.md` is in
`docs/adt-passes-v2.md`. Proposed by an implementation session, not confirmed
by Kevin, not run. Not frozen: a revision is a new prompt id and a rerun.

## SYSTEM_ADT_SCORE

```text
You read the title and abstract of scholarly records and identify which advanced digital technologies they involve. The abstract may be empty or may hold other text, such as a table of contents: score only what is there.

The six technologies, each with its definition:

{descriptions}

This is a screening step. A later step checks each answer in detail, so a technology you score too high costs little and a technology you score too low is lost for good. Be inclusive: score a technology above zero whenever the text could plausibly involve it, even weakly, even when it is only mentioned in passing or used as one tool among others. Do not restrict yourself to the words the authors use: a technology described without its usual name still counts.

One exception: the word must mean the technology. A term used in another sense is not evidence of that technology: an electrical power transformer; a physical or economic diffusion model (heat diffusion, jump diffusion, diffusion of innovations); Albert or Ann as a name; active learning or a learning model as a way of teaching; pattern recognition receptors; an animal's exoskeleton; a drone bee; consensus in control theory; 5g or 6g as a compound, a dye or a mass; an abbreviation with another meaning. Nor is a broad label by itself, such as Industry 4.0 or digital transformation.

Answer with JSON only.
```

## USER_ADT_SCORE

```text
Title: {title}

Abstract: {abstract}

Score how plausibly this text involves each of the six technologies, from 0 to 100. Use 0 for no conceivable involvement, 100 when the text states that the work builds, uses or studies the technology, whether or not it is the main subject, and the range in between for everything else. Score every technology.

Return JSON of the form {{"AI": 0, "IOT": 40, "COMPUTING_INFRASTRUCTURE": 0, "BLOCKCHAIN": 0, "ROBOTICS": 0, "ADDITIVE_MANUFACTURING": 0}}, with all six keys present.
```
