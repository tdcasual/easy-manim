# Collaboration Governance Alignment

Date: 2026-04-03

## Objective

Align the older workflow-collaboration ACL direction with the now-default thread-native video runtime so future collaboration features do not split into two unrelated permission systems.

## Current Surfaces

### Workflow Participants

Current implementation:

- stored as workflow-scoped participants on the root task lineage
- capability-based access is enforced through [workflow_collaboration_service.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/workflow_collaboration_service.py)
- reviewer/verifier collaborators can read shared workflow resources and submit review decisions when granted `review_decision:write`
- owner-only mutation still gates participant upsert/remove and workflow-memory mutation

What this surface is good at:

- policy and authorization
- review bundle access
- controlled decision submission on supervised workflows

### Thread Participants

Current implementation:

- stored as thread-native participants on the video thread
- surfaced through [video_thread_service.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/video_thread_service.py) and the owner-facing `video_thread_surface`
- continuity flows through `addressed_participant_id`, `addressed_agent_id`, `participant_runtime`, and `composer.target`
- owner-only mutation currently gates participant upsert/remove for thread rosters

What this surface is good at:

- continuity and addressing
- owner-facing discussion identity
- durable participant presence around a single video artifact

## What Is Shared

- Both surfaces model named non-owner agents as explicit collaborators rather than implicit role labels.
- Both surfaces already preserve owner-only mutation boundaries for participant roster changes.
- Both surfaces need deterministic read/write policy for HTTP and MCP transports.
- Both surfaces are now part of one product story: supervised, multi-agent iteration around a durable video thread.

## What Must Remain Distinct

- Workflow participants remain the authority for review-bundle permissions, review-decision authorization, and task-root collaboration capabilities.
- Thread participants remain the authority for discussion continuity, addressed follow-up routing, display identity, and “who am I talking to under this video?”
- Workflow participants are lineage-scoped and policy-oriented.
- Thread participants are artifact/thread-scoped and continuity-oriented.

## Owner-Only Mutation Boundaries

Owner-only mutation should stay in these places for the next wave:

- workflow participant roster changes
- workflow memory pin/unpin operations
- thread participant roster changes
- any cross-surface grant that changes collaborator capabilities or visibility scope

Non-owner collaborators may continue to:

- read only explicitly shared workflow resources
- submit only the review decisions they are explicitly authorized to submit
- participate in thread continuity only through addressed turns and projected runtime continuity, not by mutating rosters themselves

## Recommendation For The Next ACL Wave

Recommendation: unified governance layer first.

Why:

1. The codebase already has two real collaboration surfaces, not one future surface and one placeholder.
2. Workflow ACLs without thread alignment would keep policy vocabulary task-centric while the product default is now thread-native.
3. Thread participant permissions without workflow alignment would duplicate capability semantics in a second place.
4. A thin shared governance layer can define common concepts first:
   - owner
   - collaborator
   - roster mutation authority
   - read scopes
   - decision-write scopes
   - continuity-only participants

Recommended shape:

- keep storage separate for now
- introduce shared policy vocabulary and resolution rules before broad endpoint changes
- let workflow and thread services consult the same governance rules while preserving their distinct data models

## Practical Sequencing

1. Define shared governance concepts and policy resolution order.
2. Map workflow capabilities onto that shared vocabulary.
3. Map thread participant continuity roles onto the same vocabulary without forcing capability parity where it does not belong.
4. Only then implement the next concrete authorization wave in HTTP and MCP routes.

## Implication For The Old Roadmap

The older P1 roadmap should no longer describe collaboration as workflow-only. It should describe collaboration governance across:

- workflow participants
- thread participants
- reviewer/verifier decision rights
- owner-only roster mutation
- future shared governance rules
