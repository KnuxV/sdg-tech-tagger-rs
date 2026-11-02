# Gate v2 as Web of Science queries

The technology gate, gate v2, written as queries in Web of Science syntax.
Decision D032; contract `docs/adt-wos-form-contract.md`. Read-only, with
`SHA256SUMS`.

## What the files are

One query per group, a plain disjunction of quoted terms under `TS =`, and
`ALL.txt`, one query for the whole gate, the umbrella terms included.

| file | terms of gate v2 | terms written here |
|---|---|---|
| `AI.txt` | 378 | 1,042 |
| `IOT.txt` | 92 | 285 |
| `CI.txt` | 161 | 455 |
| `BL.txt` | 47 | 94 |
| `ROB.txt` | 79 | 146 |
| `AM.txt` | 85 | 239 |
| `UMBRELLA.txt` | 26 | 55 |
| `ALL.txt` | 868 | 2,313 |

`ALL.txt` is 59,167 characters. The seven group files hold 2,316 terms;
three are in two groups.

## How they differ from `adt/gate_v2/*.txt`

The files of `adt/gate_v2/` are the terms of the gate. The gate also
matches the regular plural of a term and the closed spelling of a term
written with a hyphen, and those two rules are in its compiled patterns
only. Here every spelling is a term of its own:

- `random forest` is `"random forest"`, `"random forests"` and
  `"random forestes"`; `digital economy` adds `"digital economies"`. The
  endings are those of the pattern (`s`, `es`, or `ies` for a `y` after a
  consonant), which is why forms that are not English are written too.
- `meta-learning` adds `"metalearning"`, each with its plurals;
  `data-center*` adds `"datacenter*"`.
- `ai` takes no plural, as in the gate. A truncated term and a term ending
  in a digit take none either.

They are generated, never edited:

```python
import json
from importlib.resources import files
from sdg_tech_tagger.adt import wos_form

gate = json.loads((files("sdg_tech_tagger") / "adt/gate_v2/gate_patterns_v2.json").read_text())
texts = wos_form.render_gate(gate)   # {"AI.txt": "TS = (...", ..., "ALL.txt": ...}
```

## What is shown, and what is not

Shown, by `tests/unit/adt/test_wos_form.py`: read by this package's
matcher with every option off, as the Web of Science query of `adt/wos/`
is read, the terms of each file match exactly what the group's terms match
with the plural and closed-spelling rules on and the decimal rule off.

Run on the Web of Science on 2026-10-11, after these files were written
(`probes/wos_run_probe`): each of the eight files is accepted as one
query, `ALL.txt` included, which returned 6,560,253 records. The term
`"unmanned surface ve*"` is accepted. A "Did you mean?" suggestion is
shown for five of the group files and was not followed. That the query
runs says nothing of whether its records are the ones the gate flags.

## Where the files are not the gate

- **Decimals.** The gate keeps a decimal whole: "0.5g per day" is not the
  term `5g`. A Web of Science term cannot say that, so these files match
  it. They also match "industry 4 0" for `industry 4.0`, which the gate
  does not.
- **Fields.** The gate reads title and abstract. `TS` on the Web of
  Science also reads the author keywords and Keywords Plus.

On the 5,000 reference documents, one text each, with the package's
matcher: the gate flags 4,782, these files 4,786. The four more are in
group CI, and no document is flagged by the gate and not by the files.
Those documents were selected by a technology query, so the figure says
nothing of other corpora.
