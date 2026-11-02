# Contracts

The contracts the package was built and tested against, copied as they were
written during development:

- `contract.md`: `detect` and the command, for the four SDG systems.
- `wos-sdg-contract.md`: how the four systems are written as Web of Science
  queries (`wos_sdg`, `wos_queries/`).
- `adt-wos-form-contract.md`: how the extended technology query is written
  as Web of Science queries (`adt.wos_form`, `adt/extended_wos/`).
- `technology-queries.md`: every term of the two technology queries,
  simplified and extended, group by group, with the sources of the
  extended query's terms. Written by `scripts/write_technology_queries.py`.

They are given as they were written during development, with references
to the development record removed. The tests in `tests/` are written from
these contracts.
