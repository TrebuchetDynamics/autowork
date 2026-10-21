+++
schema = 1
id = "TOOLSET-321-57"
title = "Requalify documentation coverage without rewriting unproven historical pins"
short = "Requalify documentation source pins"
status = "done"
goal = "DOCS-PROVENANCE"
section = "Next"
rank = 17000
depends_on = []
touches = ["docs/roles.json", "docs/", "README.md"]
resources = []
kind = "inspection"
ownership = "coordinator"
scope = "Review current covered source closures for the role manifest after the tasks/ migration. Historical verified_at pins are currently reported as non-ancestors; retain them as historical, unproven evidence rather than replacing them just to silence stale warnings. Record genuinely current source-bound verification separately through a supported manifest/history representation only after completing each review; correct source-backed documentation drift without claiming runtime qualification."
acceptance = ["Each currently unverifiable role has either completed current-source verification with an auditable retained historical pin, or an explicit source-evidence gap. Existing historical identifiers remain recoverable and no ancestry or passing check is invented. All local document links and role mappings pass docs.py check. Current and historical proof are distinguished; independent task ranks, active contracts and frozen archives are unchanged."]
checks = ["python3 skills/docs-sync/scripts/docs.py check .", "python3 skills/docs-sync/scripts/docs.py stale .", "autowork tasks validate --worktree ."]
exclusions = ["No source-pin rewrite merely to hide drift; no frozen archive edits, task-format conversion, profile/service/job changes, model qualification or publication."]
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-321-57.toml"
+++

- Sources: docs/project.md#checkable-core-document-completeness
