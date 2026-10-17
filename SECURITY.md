# Security policy

The current development branch is the only supported version during the alpha. No production-hardening or long-term-support guarantee is made.

Private vulnerability reporting is enabled. Report vulnerabilities through [GitHub's vulnerability reporting page](https://github.com/aakash-kharb/AtlasWeave/security/advisories/new). If the option is unavailable, use a private contact listed on [the maintainer profile](https://github.com/aakash-kharb), or open an issue asking for a private contact without disclosing the vulnerability. Do not attach confidential files to public issues.

Include the affected revision, a minimal synthetic reproduction, expected impact, and relevant environment details. Parser attacks, unexpected network access, accidental record disclosure, unsafe exported instructions, and approval validation bypasses are in scope. No response-time commitment is established yet.

The engine does not make external network calls, evaluate formulas, invoke an AI agent, or execute joins. Browser mode uses an authenticated loopback-only server and temporary upload copies. Do not expose it through a public tunnel. File/archive bounds and HTTP access controls reduce exposure but do not make arbitrary hostile documents or an internet-facing deployment safe. See the [threat model](docs/trust/threat-model.md).
