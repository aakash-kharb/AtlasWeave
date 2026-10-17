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
| Malicious website accessing the local workspace | Exact loopback Host and same-Origin checks, random session token on every API request, no CORS | Other software running as the same OS user is outside this boundary |
| Saved project requesting private local paths | Reopened projects must reference the registered uploads; static asset allowlist | Imported metadata is still untrusted |
| Stale tabs overwriting decisions | Workspace revision checked for every mutation; serialized operations | One workspace per server; no multi-user collaboration |
| Upload copies remaining on disk | Private temporary directory, explicit clear, graceful shutdown cleanup | A hard crash/kill may leave temporary files behind |

Future remote connectors require credential isolation, network policy, read-only query behavior, cancellation, and adapter-specific validation before shipping. The current browser interface is a single-user local tool, not a production HTTP service.
