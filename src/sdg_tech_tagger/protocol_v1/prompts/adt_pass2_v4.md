# ADT pass 2 prompt, version 4 (frozen, D034)

Version 4 is version 3 with the changes of `docs/reports/2026-10-08-adt-ai-extras.md`, chosen by Kevin on 2026-10-08 and frozen with the other prompts of `docs/protocol-freeze-v1.md`.

This file is the template of ADT pass 2: one call per (work, ADT) pair that
ADT pass 1 scored at or above the threshold, one token of answer from five
letters, `N` not this technology, `M` mention, `T` tool, `A` artefact, `E`
external. Relevance is derived as `T`, `A` or `E`. See
`docs/adt-passes-v2.md`, and `docs/adt-pass2-contract.md`, "ADT pass 2", for
the stage itself.

Registry convention, the prompt id:

- The template id is `adtp2-` then the first 12 hex characters of the sha256
  of the block texts, SYSTEM_ADT_PASS2, ROLE_RULES then USER_ADT_PASS2,
  joined by a single `\n`, encoded as UTF-8. Only the fenced blocks count.
- A row's `prompt_id` is `<template id>+<description id>+<boundary id>`: the
  pair's block of the descriptions file with prefix `adtdesc-<slug>`, and
  its block of the boundaries file with prefix `adtbound-<slug>`, each
  hashed alone, `slug` being the code lower cased with underscores turned
  into hyphens. Editing this file moves every pass 2 id; editing one ADT's
  definition or boundaries moves that ADT's ids only. The ids are computed
  by code (`load_prompts`), never by hand.

Template placeholders:

- SYSTEM_ADT_PASS2 takes exactly `{role_rules}`, filled once per run with the
  ROLE_RULES block, so the rules sit in the prefix every call shares.
- ROLE_RULES is not formatted and takes no placeholder: a brace in it is
  written single and reaches the model as it stands.
- USER_ADT_PASS2 takes exactly `{title}`, `{abstract}`, `{technology}`,
  `{definition}` and `{boundaries}`, filled in one `str.format` per call.
  `{technology}` and `{definition}` are the pair's name and definition from
  the descriptions file, `{boundaries}` its block of the boundaries file.

A literal brace in SYSTEM_ADT_PASS2 or USER_ADT_PASS2 is doubled, because
those two blocks are filled with `str.format`.

This file is revision 3 of the template. It starts from
`prompts/adt_pass2_v2.md`, which is kept unchanged as the record of what was
piloted, and applies rules R7 to R12 of `docs/classifier-prompts-v3.md`,
which lists the old and the new text of each: the title as the text when the
abstract is empty (R7), one rule for a named platform (R8), presence by
description (R9), the broad labels named in full (R10), a comparison of
algorithms against a test of a deployed product (R11), and planned work
(R12). The rules come from the review
`docs/reports/2026-10-08-adt-passes-v2-review.md` (findings F1 to F4) and
from divergence-validation protocol v1.0 section 6.1. What revision 2
changed against `prompts/adt_pass2.md` is in `docs/adt-passes-v2.md`.
Proposed by an implementation session, not confirmed by Kevin, not run. Not
frozen: an edit is a new prompt id.

## SYSTEM_ADT_PASS2

```text
You decide how a scholarly work, read through its title and abstract, relates to one advanced digital technology.

First decide whether the technology, as its definition and boundary rules describe it, is in the text at all. Then, if it is, decide the relation between the authors and the technology.

Answer with exactly one letter:

E  External. The technology as it exists in the world is what the work studies: its adoption, effects, costs, risks, performance, perception or governance, where the instance belongs to others.
A  Artefact. The authors build, propose, design or adapt the technology, or a system made from it, and offer it as their contribution.
T  Tool. The authors use the technology to obtain a result about something else.
M  Mention. The technology is in the text, but the authors do nothing with it and it is not what the work studies.
N  The technology is not in the text. It is neither named nor described, or the word means something else, or the text names only a broad label and no instance of the technology.

Rules that apply to every technology:

- Judge only from the title and the abstract as written. The abstract may be empty or may hold other text, such as a table of contents: judge what is there. A technology the text describes in its own terms without its usual name is in the text. A technology the text neither names nor describes is not, however likely: a statistical analysis was run on some computer, a survey was hosted on some website, and neither is evidence of anything.
- A broad label is not a technology. Industry 4.0 or 5.0, the fourth industrial revolution, Society 5.0, digital transformation, digitalisation, digital technologies, digital twin, smart manufacturing, intelligent manufacturing, digital manufacturing, smart city, smart farming, precision agriculture and metaverse are not evidence by themselves; judge the named technologies the text describes under them.
- A word or abbreviation used in another sense is not the technology, and the answer is N.
- A text can involve several technologies. Judge only the one you are asked about.

{role_rules}

Answer with a single letter: E, A, T, M or N. Output nothing else.
```

## ROLE_RULES

```text
How to choose between E, A, T and M once the technology is in the text:

- E applies when what the work says is about the technology as it exists in the world, deployed, adopted, sold, regulated or anticipated by others. A study of the effect of AI adoption on emissions, a survey of farmers' drone use, a test of an off-the-shelf chatbot and a policy framework for blockchain are E. If the authors built the instance, it is A, however thoroughly they evaluate it.
- A is what is offered. If the text presents the model, system, method or device as what the authors propose, develop or introduce, it is A, even when they also apply it to a domain problem. A system the authors plan or propose to build, in a protocol or project description, is also A. If they used an existing technology and the contribution is the finding about the domain, it is T. A system built for an environment ("a routing method designed for sensor networks") is A for the technology built, M for the environment.
- A built and then tested remains A, whether tested in a trial, a deployment or a simulation.
- T needs a signal. The text must show the authors doing something with the technology to get a result, in any voice: "we applied a random forest", "images were classified using a neural network", "processed in Google Earth Engine". Tuning a model, or comparing existing algorithms that the authors train or fit themselves for a result about the domain, is still T; testing a product or system deployed by others is E. A technology in the text without such a signal is M.
- M covers the rest: a fact about the technology, a comparison with it, the setting ("in the age of AI"), an intended application the authors name without building or using it ("a material for soft robotics", "suitable for 5G"), a platform or hardware named only as where something is hosted, stored or ran ("hosted on AWS", "trained on a GPU"), or future work named in passing.
- When the abstract is empty, the title is the text and is signal enough: a title presenting the technology as built, used or studied is A, T or E; it is M only when it names the technology as a setting or an intended application. A title that names neither the technology nor one of its methods is N, however likely the technology is behind its topic.
- Reviews of the literature: answer for the technology's role in the work reviewed. A review of models or methods that use the technology is T, or A when it surveys proposed architectures or techniques; a review of the technology's adoption, effects, costs or governance is E.
```

## USER_ADT_PASS2

```text
Title: {title}

Abstract: {abstract}

The technology is {technology}.

Definition: {definition}

Boundary rules for {technology}:
{boundaries}

How does this text relate to {technology}? E, A, T, M or N:
```
