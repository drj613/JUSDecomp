# ARM7 analysis port phases

Architect:
- [x] Ground (two explorers traced parser and module callers; factual synthesis pending)
- [x] Sketch (complete: shared-policy versus separate bounded analyzer)
- [x] Agree (bounded observer selected; no human checkpoint requested)
- [ ] Implement (active: test-first bounded chosen contract)
- [ ] Scrap (only if concrete repeated implementation friction warrants redesign)

Arena:
- [x] Frame
- [x] Fan out
- [x] Cross-judge (gpt-6-sol; B15/A12)
- [x] Pick (B)
- [x] Graft (immutable reporting and hard-span invariants)
- [ ] Verify

Scope: explicit per-function/module ISA and branch policy for checked ARM7 inputs,
without guessed function bounds, original symbols, relocations, source or baseline credit.
Current tool base: bee60e2ee89308616933a391c387928e2dfb5c07.
Available runtime models replace the stale pi-specific harness roster.
