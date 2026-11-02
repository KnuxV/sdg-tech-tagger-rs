# The files in this directory

The simplified technology query, as written for the Web of Science `TS=`
field, six groups. The terms are matched as written: no plural, hyphen or
decimal rule is added. Do not edit the files: a change to a term is a change
of the query. All terms, group by group, are in `docs/technology-queries.md`.

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
| `patterns.json` | the six compiled files as patterns, read by `translate` |

The two reference files end, after a blank line, with the result count the
Web of Science page showed. Only the six per-group files are compiled.
`SHA256SUMS` gives the checksum of every file.
