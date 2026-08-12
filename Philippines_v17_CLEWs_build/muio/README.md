# Portable Philippines v17 MUIO case

`Philippines_v17_v17.0.0_MUIO.zip` contains the complete editable MUIO
parameter JSON, required view files, and local documentation for Philippines
v17. It carries v16 forward and adds the source-traced national land account,
annual land equality, and existing-mode idle/fallow route. Forest `VC=-10` is
unchanged.

Extract the `Philippines_v17` directory into
`MUIOGO/WebAPP/DataStorage/`, start MUIOGO, and regenerate the solver input
through the application before solving. Generated solver inputs and runtime
results are excluded from the archive.

Current archive:

- size: 19,780,576 bytes
- SHA-256: `25e18c248bde3f6567e0511412f8ee9e53e8a2c111ea4e2050165968b8b11120`

The v16 and v15 archives are retained as predecessor evidence; the v17 package
does not depend on either archive to interpret its complete source ledger.

Verify the archive before use:

```bash
sha256sum -c SHA256SUMS
```

The authoritative source ledger and validation evidence are in the parent
build package.
