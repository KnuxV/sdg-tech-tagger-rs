# The files in this directory

The technology query of the Nature Communications paper, as written for the
Web of Science `TS=` field, six groups. They are the files the paper ran,
unchanged. Do not edit them: a change to a term is a research decision.

| file | role |
|---|---|
| `AI.txt` | compiled, code `AI` (artificial intelligence, with big data) |
| `IOT.txt` | compiled, code `IOT` |
| `Computing_infrastructure.txt` | compiled, code `CI` |
| `Blockchain.txt` | compiled, code `BL` |
| `Robotics.txt` | compiled, code `ROB` |
| `Additive_Manufacturing.txt` | compiled, code `AM` |
| `combined_raw_query` | reference: the single query as recorded, 281 terms |
| `executed_raw_query` | reference: the query as the Web of Science ran it, seven terms rewritten by a "Did you mean?" |
| `adt_patterns_v1.json` | the six compiled files as patterns, read by `translate` |

The two reference files end, after a blank line, with the result count the
Web of Science page showed. Only the six per-group files are compiled.
`SHA256SUMS` gives the checksum of every file.
