---
name: grill-with-docs
description: "Grill a plan and record decisions as ADRs and terms."
license: MIT
---

# Grill With Docs

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.

The pinned [upstream entry](upstream/PROTOCOL.md) is a router: it asks a host to call
a `grilling` skill and a `domain-modeling` skill. Autowork hosts have no such skill
call, so this adapter states the composition directly. Run the interview with
[Grilling](../grilling/SKILL.md), then record what it settles with the repository's
own documentation owners.

## Compose the two jobs

1. Run [Grilling](../grilling/SKILL.md) on the plan or design. Do not write documents
   during the rounds; the decisions are not settled yet.
2. After the owner confirms the shared understanding, record each durable decision:
   - a decision with alternatives, a chosen option and a reason becomes an ADR in the
     repository's ADR folder, following its existing numbering and template;
   - a named domain concept or a resolved ambiguity becomes one glossary entry with the
     term, its meaning and the words to avoid.
3. Follow [Docs Sync](../../skills/docs-sync/SKILL.md) for the write rules: source-backed
   claims, the existing owners, and its validation and report contract. Create a missing
   glossary or ADR folder once, lazily, and say you did.
4. Skip a record when it would be ephemeral ("not worth it now") or self-evident. Never
   reverse an accepted ADR silently; surface the conflict and let the owner decide.

One message per settled decision group, not a document per question. Keep the ADR and
glossary vocabulary out of code identifiers unless the repository already uses it.

**Receipt:** decisions recorded with their paths; terms added; decisions left open;
validation run; anything intentionally unrecorded and why.

[Source and hashes](UPSTREAM.json) · [MIT license](upstream/LICENSE).
