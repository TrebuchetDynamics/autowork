---
name: improve-codebase-architecture
description: "Find deepening opportunities and report them visually."
license: MIT
---

# Improve Codebase Architecture

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.

Read the pinned [architecture review reference](upstream/PROTOCOL.md) and its
[HTML report format](upstream/HTML-REPORT.md). They own the scan questions, the report
cards and the visual guidance. This adapter sets the vocabulary the review uses and the
host limits it must respect.

## Vocabulary

Use these terms and no substitutes: **module**, **interface**, **depth**, **seam**,
**adapter**, **leverage**, **locality**. A shallow module's interface is nearly as
complex as its implementation; a deep one hides that complexity behind a small
interface. Test a suspected shallow module with the **deletion test**: would deleting it
concentrate complexity, or only move it? One adapter is a hypothetical seam, two make it
real. The interface is the test surface. Read the repository's domain glossary and ADRs
before naming anything; a decision an ADR records is not yours to re-open silently.

## Process

1. **Scope first.** Take the area the owner named. Otherwise follow recent history to
   the hot spots. Read the glossary and the ADRs for those areas.
2. **Scan read-only.** Walk the code where understanding one concept means bouncing
   between many small modules, where seams leak, and where behavior is hard to test
   through the current interface. Delegate one bounded exploration with the host's own
   sub-agent tool when the codebase is large; otherwise read directly. Change no file.
3. **Report.** Write one self-contained HTML file into the OS temp directory, never into
   the repository: `<tmpdir>/architecture-review-<timestamp>.html`. Give each candidate
   files, problem, solution, benefits stated as locality and leverage, a before/after
   visual, and a `Strong`, `Worth exploring` or `Speculative` badge, then one top
   recommendation. Report the absolute path. Open it only when a display and opener
   exist; otherwise leave it for the owner to open.
4. **Stop and ask.** Propose no interfaces yet. Ask which candidate to explore.
5. **Interview the chosen candidate.** Use [Grilling](../grilling/SKILL.md) for
   constraints, dependencies, the deepened shape, what sits behind the seam and which
   tests survive. Record settled decisions per
   [Grill With Docs](../grill-with-docs/SKILL.md) when the owner wants them durable.

A review is advice, not authorization: implementation, commits and delivery need their
own accepted scope, through [Autowork](../autowork/SKILL.md). Report CDN use in the
report file, since the visuals load from the network when opened.

**Receipt:** scope and why; files and areas inspected; candidates with badge and
deletion-test evidence; report path; ADR conflicts surfaced; chosen candidate; checks
run; what stays unverified.

[Source and hashes](UPSTREAM.json) · [MIT license](upstream/LICENSE).
