# Optional native ARM7 payload integration candidate

The option requires a freshly executed, independently approved physical ARM7
producer. It accepts no prebuilt payload directory or detached success report.
The [approval template](arm7-native-approval.pending.json) is deliberately
pending and rejects. Root must supply reviewed producer/source/native-tool pins
after the native baseline and ELF snapshot fix pass acceptance.

The existing verifier arguments remain. To enable the candidate add:

```sh
--arm7-native-manifest "$APPROVED_REPO_LOCAL_MANIFEST" \
--arm7-native-producer "$PINNED_PHYSICAL_PRODUCER"
```

Both arguments are required together. The approval declares schema version 1,
status `approved`, producer SHA256, reviewed 40-digit source commit/tree,
nonempty repository-relative `source_artifacts` hash map, and repository-relative
layout/native-pins files with SHA256. These durable artifacts record independent
source-origin acceptance; an adjacent unbuilt Rust checkout is not needed.
The native-pins sidecar supplies absolute clang/lld paths, exact hashes and
versions. Production ARM9 tool pins are unchanged.

One `arm7_native_baselines` stage runs before freshness, bringing an enabled
source pipeline to 20 stages while leaving the default 19 unchanged. The helper
captures the actual executable/cwd/argv/stdout/stderr/exit and requires exactly
parent plus `ChildRom/JSS2Child.srl` in reviewed layout order. Artifacts are new,
contained, nonsymlinked and exhaustively digest-checked against the directly
captured receipt. Native commands, link inputs, map, physical segment metadata
and zero-credit scope must match their declarations. Input/tool snapshots are
rechecked before consumption. Compiler/tool symlinks are pinned by their actual
bytes; artifact symlinks are rejected.

The helper returns a live operation with an immutable private copy of that
actual execution. Its `report` property yields a separate JSON audit copy.
Canonical verification passes the live operation separately through packing;
the audit report must exactly equal its captured record. Deserialized or
rewritten reports cannot supply that operation. Standalone `rom_roundtrip.py
--build-report` rejects ARM7 reports and requires rerunning the verifier.
Rechecks also compare receipt to captured stdout and rebuild the complete
expected input-pin inventory from the unchanged approved manifest/native pins.

The approved builder owns ELF validation and reconstruction. Its accepted
implementation must bind the validated ELF byte-buffer hash through publication;
the wrapper does not implement a second ELF parser. The packer hashes and uses
the exact read image buffer, writes parent ARM7 at its checked header offset,
and writes child ARM7 at the original exact FNT/FAT child interval plus that
child's header offset. Both appear as explicit native write records despite
equal images. No BSS bytes are inserted. Existing original-header, whole-child
and whole-ROM equality checks remain required.

Public invented-ROM tests execute a real fixture producer to prove orchestration
and failure handling, not native ELF correctness. The candidate does not grant
source bytes or functions. ARM9 17-module/87,493-relocation/304-byte source
contracts and global unknown scope remain separate. Actual optional full-ROM
acceptance awaits the final reviewed Rust producer and root proof.
