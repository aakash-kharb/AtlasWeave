# First mapping

Run the example in the root README. Put the table whose unmatched records you want to retain on the **left** (orders); put the lookup table on the **right** (customers).

`inspect` displays saved evidence. Use `--search cust` to search field names and candidate IDs, or `--json` to inspect the whole project. Inspect does not read source files or certify freshness; review and export do.

Candidate IDs such as `left.f1--right.f1` refer to positional field IDs in a specific source snapshot. Names, order, parsing settings, or file bytes changing requires rediscovery.

```bash
# Reject a suggestion or undo an earlier decision.
atlasweave review outputs/first-project.json left.f1--right.f1 --status rejected
atlasweave review outputs/first-project.json left.f1--right.f1 --status pending

# Keep only matching order rows.
atlasweave review outputs/first-project.json left.f1--right.f1 \
  --status approved --join inner
```

Approval defaults to unique, non-null right keys. Inspect projected row counts before deliberately relaxing requirements with `--allow-duplicate-right` or `--allow-null-right`. Nulls never match, even when they are allowed in the right source. A candidate with no shared keys cannot be approved as a join in this release.

To use normalization or aliases, copy `examples/strategy-config.json`, edit it, and pass `--config path/to/config.json` during discovery. Settings changes require a new discovery and review; do not edit saved evidence. An input that hits the row cap is sampled. Increase `--max-rows` (up to 100000) and rediscover to obtain full evidence.

Export creates `mapping.json` and `agent-brief.md` in a new output location. Review the metadata before pasting the brief into an AI agent. The agent must obtain your source locations, verify hashes, and honor approved rules. AtlasWeave does not perform the join or call the agent.
