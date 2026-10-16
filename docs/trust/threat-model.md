# Initial threat model

Assets: private source records, source locations, review intent, accurate join evidence, and an agent's downstream authority.

Trust boundaries: imported CSV/XLSX → local parser; saved project → revalidation; mapping/brief → an external agent. A saved project is not a signed document and must not be accepted as proof of someone else's approval.

| Threat | Current control | Remaining limitation |
| --- | --- | --- |
| Malformed or oversized files | File/archive/column/row bounds, strict CSV widths, defusedxml | No worker-process CPU/memory timeout; parser dependencies still carry risk |
| Wrong or stale mappings | Explicit review, full scan required, hashes, recomputation, strict schemas | Heuristic similarity and observed overlap do not establish semantic correctness |
| Unexpected row expansion | Duplicate/null evidence and projected join counts, unique right key by default | Explicit overrides can authorize expansion; output execution is external |
| Data leakage through export | No records, sample values, or directory paths | Metadata and hashes can still be sensitive |
| Prompt injection | No evaluation, quoted metadata, untrusted-data instructions | External agents may mishandle instructions; no absolute prevention claim |
| Accidental output overwrite | Exclusive create for discovery/exports; atomic replacement for review | No multi-process editing locks or review-history ledger |

Future remote connectors require credential isolation, network policy, read-only query behavior, cancellation, and adapter-specific validation before shipping. A web interface will introduce separate local-service/browser security decisions.
