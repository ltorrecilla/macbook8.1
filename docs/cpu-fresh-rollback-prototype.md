> **Cleanup status (2026-10-23):** The unintegrated prototype shell script and its dedicated fixture tests were removed from the active tree because the path/race safety review blocked production use. Their full source remains in Git history (PR #30). No production CPU installer depends on them.

# CPU fresh-install rollback prototype

This is an **unintegrated test prototype**, not a production rollback command. It is intentionally not sourced by `install-cpu-limit.sh`, not called by a service and not documented as a command for the MacBook. Its tests use temporary paths only.

Checks covered: exact checksum of owned fixture, changed content, symlinks, paths outside the test allowlist and malformed manifest. These are incomplete safeguards: path canonicalization, races, systemd enablement, ownership and permissions, directory rollback and interrupted transactions remain unreviewed.

**No real installation rollback is available yet.** Do not invoke this helper against system paths. Later implementation must be reviewed separately and require full tests before integration. The existing CPU cap stays unchanged.
