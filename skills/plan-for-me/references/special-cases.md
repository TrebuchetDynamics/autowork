# Plan For Me: special cases

Load the section that matches the request. [SKILL.md](../SKILL.md) and the
[planning craft](../../shared/PLANNING-CRAFT.md) still apply.

## Game animation, environments and level expansion

For broad animation, environment or level-expansion requests, first inventory the
currently exposed states, authoritative geometry, presentation drivers and camera
limits. Scope “all” to that supported inventory unless the user explicitly expands
it; do not turn animation polish into implementing unbuilt gameplay systems.
Distinguish procedural presentation from random level generation. Choose the smallest
supported authored/procedural route, and state whether terrain differences affect
appearance only or gameplay rules; visual variety does not authorize hidden changes
to traction, collision, speed or ability eligibility.

Separate the user's outcomes from reversible prototype targets. Derive any size
baseline from the actual layout, name the measured quantity, and label coordinate
measurements separately from traversal time or player experience. Require a legal
input trace through the enlarged route and camera visibility at its extremes;
moving a goal, enlarging bounds or recoloring existing geometry is not proof of a
larger playable level. Keep presentation changes downstream of authoritative state,
and require animation-enabled/disabled equivalence where visuals must not affect
physics or command timing.

Extend the existing queue without re-scoping earlier planned tasks: add bounded
successors after the user's current priorities, preserve prior contracts, and add
only real implementation or composed-verification dependencies. Keep independent
layout work independent of unrelated visual polish, then join them in one composed
presentation/artifact check. Preserve historical layouts and their regression
identity when introducing a new playable variant, so old-course passes cannot be
misreported as new-course reachability.

## Validation-performance planning

For validation-performance planning, reconcile the newest full-gate inventory and
source binding before saying a passing baseline is missing. If correctness now
passes, plan repeated successful measurements under matched source, tools, test
identities and setup before choosing an optimization. A focused pass or one full-gate
pass establishes neither a repeatable baseline nor a speedup; do not rerun obsolete
fixture investigations or transfer a receipt to a different candidate.
