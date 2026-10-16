# Security policy

The current development branch is the only supported version during the alpha. No production-hardening or long-term-support guarantee is made.

Report vulnerabilities privately through [GitHub's vulnerability reporting page](https://github.com/aakash-kharb/AtlasWeave/security/advisories/new) when private vulnerability reporting is enabled. If the option is unavailable, use a private contact listed on [the maintainer profile](https://github.com/aakash-kharb), or open an issue asking for a private contact without disclosing the vulnerability. Do not attach confidential files to public issues.

Include the affected revision, a minimal synthetic reproduction, expected impact, and relevant environment details. Parser attacks, unexpected network access, accidental record disclosure, unsafe exported instructions, and approval validation bypasses are in scope. No response-time commitment is established yet.

The CLI does not make network calls, evaluate formulas, invoke an AI agent, or execute joins. File and archive limits reduce exposure but do not make arbitrary hostile documents safe. See the [threat model](docs/trust/threat-model.md). Maintainer setup still needs private vulnerability reporting enabled on GitHub.
