# Stable local detector boundary

**Status**: accepted

The first detector slice exposes one typed in-process API:
`scan(project_root: Path, config: ScanConfig) -> ScanResult`. Its CLI adapter,
`python -m gdd_drift_detector --project-root <path> --json`, delegates directly
to the same engine and serializes the result.

`ScanConfig` requires explicit GDD and GDScript paths in this slice. Successful
scans write `drift_report.md` and versioned `drift.json` to the supplied project
root. This project-root location is the canonical artifact convention; a future
configurable output directory must preserve it as the default.

Invalid project roots and unreadable or unsupported configured inputs are typed
`ScanFailure` values. The CLI serializes them as structured JSON to stderr and
uses a non-zero exit status. Invalid input writes no artifacts, keeping the
detector local and read-only except for successful canonical artifacts.
