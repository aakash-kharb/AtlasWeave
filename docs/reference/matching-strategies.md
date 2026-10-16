# Strategies and evidence

The configurable weighted average ranks candidates from 0 to 1. The default minimum is 0.55. Scores are deterministic heuristic rankings, not calibrated probabilities. Rounding is for storage/display; filtering uses the unrounded score.

| Strategy | Weight | Measurement | Common misleading case |
| --- | --- | --- | --- |
| Name/alias | 0.4 | Sequence similarity of ASCII alphanumeric lowercase names after one-step aliases | `order_id` and `customer_id` name unrelated identifiers |
| Type | 0.1 | Equal nonempty, nonmixed inferred kinds | Unrelated text columns share a type |
| Overlap | 0.4 | Shared distinct non-null values / left distinct values | Different entities reuse small numeric codes |
| Uniqueness | 0.1 | Right distinct non-null values / right non-null rows | Almost any random string field may be unique |

The default alias maps `cust_id` to `Customer ID`. Configured aliases replace the default alias dictionary and must resolve directly to canonical names; chains/cycles are rejected. Name normalization currently discards non-ASCII characters. Value normalization preserves Unicode and applies only configured trim/casefold operations. No fuzzy value matching, numeric coercion, leading-zero removal, or arbitrary executable transform is supported.

Kinds are `number`, `boolean`, `text`, `mixed`, or `empty`. This is a coarse profile, not a conversion instruction. A numeric-looking string with leading zeros remains text. Date-format similarity and dedicated pattern strategies are future work.

For each pair, evidence records shared distinct keys, null counts, duplicate excess rows, unmatched rows on each side, observed cardinality, and projected inner/left join row counts. Duplicate count is non-null rows minus distinct non-null keys, not the number of duplicate groups. Cardinality is based on duplicates across the scanned columns. It can be conservative when duplicates occur only in unmatched keys.

Inner-join rows sum `left_count(key) * right_count(key)` over shared keys. Left-join rows add all unmatched left rows, including null keys. No null-to-null match is counted. All evidence uses the same normalization as the export. Warnings and `scope` distinguish sampled results from full selected-table scans.

Runtime: profiling is linear in selected cells; pair comparison visits distinct keys for every field pair. Candidate pruning, large-data indexes, calibrated evaluation, and benchmarks remain future work.
