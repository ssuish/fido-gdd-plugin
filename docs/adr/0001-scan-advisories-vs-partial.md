# Scan advisories do not qualify partial scans

**Status**: accepted

Fido reports recognizable input footguns through a separate **Scan advisory**
channel. An advisory is guidance, not an omission of authoritative input. It
must not enter `warnings`, change `state` to `PARTIAL`, or set
`summary.coverage_qualified` to `true`.

This slice uses advisory code `EMPTY_MARKER_NAME` when an Entity marker matches
but has no tracked name after it. The line is not tracked. Users must write the
prefix-only form `[entity: type] Name`; heading-suffix markers are not parsed as
tracked entities.

Partial scan remains reserved for unreadable or unsupported inputs that can
make authoritative findings incomplete. Advisories may coexist with valid
tracked entities and do not change orphan policy.
