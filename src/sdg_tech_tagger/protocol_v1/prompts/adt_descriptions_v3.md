# ADT descriptions, version 3 (proposed, not confirmed)

One block per advanced digital technology of `detections.ADT_LABEL_CODES`
(six, big data analytics inside AI), the single source of each ADT's display
name and short definition. Read at run time by ADT pass 1, which shows all
six, and by ADT pass 2, which shows the pair's ADT. Nothing is generated from
this file and nothing copies it.

Each block: the display name on its first line, one blank line, then the
short definition. A block under a heading that is not one of the six codes is
an error, not an unused text.

Registry convention: the pass 1 descriptions id is `adtdesc-` then the first
12 hex characters of the sha256 of the six block texts, in `ADT_LABEL_CODES`
order, joined by a single `\n`. Only the fenced blocks count.

This file is revision 3. It starts from `prompts/adt_descriptions_v2.md`,
which is kept unchanged as the record of what was piloted. Five of the six
blocks are character for character those of revision 2. One sentence of the
AI definition is changed, because rule R1 of `docs/classifier-prompts-v3.md`
(big data analytics counts when presented as the method of analysis) made it
contradict the AI boundary: "This includes the analysis of large datasets
when such methods are applied." became "This includes big data analytics and
data mining presented as the method of analysis." What revision 2 changed
against `prompts/adt_descriptions.md` is in `docs/adt-passes-v2.md`.
Proposed by an implementation session, not confirmed by Kevin, not run. Not
frozen: an edit is a new prompt id.

## AI

```text
Artificial intelligence and big data analytics

Systems that infer from their input how to produce outputs such as predictions, content, recommendations or decisions: machine learning and deep learning of every kind, and logic- and knowledge-based approaches such as expert systems. This includes big data analytics and data mining presented as the method of analysis.
```

## IOT

```text
Internet of Things

Physical devices and objects that sense or act and are connected to a network, with the services that collect, exchange and process their data.
```

## COMPUTING_INFRASTRUCTURE

```text
Computing infrastructure

Shared or specialised computing and network resources: cloud, edge and fog computing, data centres, high-performance and quantum computing, accelerator hardware, big data platforms, and mobile networks such as 5G. Ordinary computers and generic software are not meant.
```

## BLOCKCHAIN

```text
Blockchain

A ledger shared across a network of computers, in which records are grouped into blocks linked by cryptographic hashes and validated by a consensus mechanism, and the applications built on it, cryptocurrencies included.
```

## ROBOTICS

```text
Robotics

Programmed physical machines that sense and act on their environment with a degree of autonomy, to move, manipulate or position: industrial, service, medical and mobile robots, drones and other unmanned or self-driving vehicles. Software with no physical body, such as a chatbot, is not a robot.
```

## ADDITIVE_MANUFACTURING

```text
Additive manufacturing

A computer-controlled production technology that creates three-dimensional objects by joining materials layer by layer.
```
