# ADR 0001: Build a Python engine and CLI first

Status: accepted for the initial implementation, 2026-10-16.

The immediate milestone needs trustworthy parsing, mapping evidence, review state, and reproducible agent exports. Visualization and branding are explicitly deferred.

Use Python 3.11+, the standard CSV reader, openpyxl for XLSX, defusedxml for XML hardening, and jsonschema for persisted contracts. Keep components as modules in one installable package. The CLI exercises the full workflow without selecting a web framework or requiring a model API.

Consequences: contributors can reproduce behavior locally with small fixtures; a future browser UI will need a service/bridge or a compatible engine implementation. This does not establish the final UI technology or an offline-browser promise. Revisit when the interaction milestone starts.
