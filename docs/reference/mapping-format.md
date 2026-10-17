# Project and export format

Both contracts use JSON Schema draft 2020-12 and `schema_version: 1`, independent of application releases. Authoritative packaged schemas are in `src/atlasweave/schemas/`; regenerate them from `scripts/generate_schemas.py`. Unknown properties and unsupported versions are rejected. No migrations are implemented; an incompatible engine version requires rediscovery.

## Local project

`project-v1.json` requires engine version, discovery fingerprint, strategy configuration, left/right source metadata, column profiles, and candidates. Source paths are relative to the project file's directory. Keep that relationship when moving files. Metadata includes SHA-256, parsing options, row count, warnings, and complete-scan status. Records and sample values are not saved.

Candidate IDs combine positional field IDs. The source hash binds those positions to exact file contents. A candidate has component scores, join evidence, full/sample scope, pending/approved/rejected status, and join rules only when approved. `review --status pending` resets a decision. There is no review-history ledger yet.

Version 0.2 adds an optional `manual_pairs` array of `{left_field, right_field}` selections to project-v1. These pairs bypass ranking cutoffs only; they still require full evidence, overlap, and valid join rules. They are included in the discovery fingerprint and evidence recomputation. Adding a pair preserves existing decisions after revalidation; rediscovery resets the list and decisions. The exported mapping-v1 shape is unchanged. Older engines cannot load projects containing this new optional field, and engine-version changes require rediscovery.

The discovery fingerprint covers engine/configuration, source metadata, profiles, and evidence, excluding review status/rules. It detects accidental changes; it is not a signature or a malicious-editor trust boundary. Review/export re-read source hashes and recompute evidence. Changing even unused bytes in a workbook invalidates review. Modifying options, names, or normalization requires rediscovery.

## Agent handoff

`mapping-v1.json` includes only approved relationships, source filenames/hashes/options, profiles, normalization rules, and unresolved candidate IDs. Local directory paths and raw rows are omitted. A source filename or header can still contain private information. Only full-scan approved mappings are allowed.

Multiple approved relationships remain independent joins. They are not automatically a composite key or an ordered plan. The brief instructs the receiving agent to clarify composition and source locations, verify hashes, honor null/duplicate/unmatched rules, and obtain authorization before production writes.

The Markdown brief is a deterministic rendering of this same contract. No remote model participates. Imported names and metadata are quoted inside an indented JSON data block and explicitly labeled untrusted. This reduces ambiguity but cannot guarantee how an external agent follows instructions.
