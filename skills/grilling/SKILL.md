---
name: grilling
description: "Stress-test a plan or idea in rounds."
license: MIT
---

# Grilling

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.

Read the pinned [grilling reference](upstream/PROTOCOL.md). It owns the mechanism:
a **design tree**, a **frontier** of decisions whose prerequisites are settled, one
numbered round per frontier, a recommended answer for each question, and a done
condition of an empty frontier. This skill owns which facts to find and what may
follow the interview.

## Run the interview

1. Name the subject and the decisions it branches into. Restate the subject in one
   sentence, then ask the first frontier.
2. Ask one round: number each question, give your recommended answer, and word each
   question so "yes" accepts that recommendation.
3. Wait for the answers. A question that depends on another open question belongs to
   the next round, not this one.
4. Recompute the frontier after each round. Repeat until it is empty.

Find facts yourself: read the repository, run a read-only command, or delegate one
bounded search with the host's own sub-agent tool. Ask the owner only for decisions
and preferences, never for something you can look up. A running search blocks only the
questions that depend on it; ask the rest now.

Stop when the frontier is empty. Report the decisions, the facts behind them and any
question the owner left open. Do not start implementation, edits, commits or delivery
until the owner confirms the shared understanding. Honor read-only requests and scope
limits through every round.

**Receipt:** subject; rounds asked; decisions settled with the answer source; facts
gathered and their evidence; open questions; confirmation state; next action.


## Boundaries

- Not implementation or delivery.
- Not durable records; use `/grill-with-docs` when decisions must be written down.
- For the plan-specific branches use `/grill-me`.

**Done when:** the frontier is empty and the owner confirms the shared understanding.
[Source and hashes](UPSTREAM.json) · [MIT license](upstream/LICENSE).