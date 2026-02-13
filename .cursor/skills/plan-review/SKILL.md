---
name: plan-review
description: Perform exhaustive plan review when user says "review". Scans plans for flaws, improvements, innovations, and gaps. Use when user types "review", "review the plan", or asks for a comprehensive plan audit with maximum scrutiny.
---

# Plan Review (Maximum Scrutiny Mode)

When the user invokes the **review** keyword (e.g., "review", "review the plan", "run a review"), enter the highest level of alertness and perform a comprehensive plan audit.

## Trigger

- User says "review" or "review the plan" in context of a plan document
- User asks for a thorough audit, scrutiny, or critical analysis of a plan

## Review Protocol

### 1. Full Read

- Read the **entire** plan file from start to finish
- Load any referenced files (configs, scripts, docs) that the plan depends on
- Re-read sections that reference external systems, APIs, or integrations

### 2. Flaw Detection

Scan for:

- **Logical gaps**: Missing steps, circular dependencies, undefined terms
- **Contradictions**: Conflicting statements, incompatible assumptions
- **Underspecified links**: Handoffs between components that lack clear interfaces (e.g., "calls OpenClaw" without specifying how output is captured)
- **Unstated assumptions**: Requirements implied but not written
- **Overlooked edge cases**: Failure modes, timeout scenarios, partial success
- **Platform/OS blind spots**: Windows vs Unix paths, shell differences, env differences

### 3. Improvement Opportunities

Identify:

- **Clarity**: Ambiguous phrasing, unclear ownership, vague success criteria
- **Completeness**: Missing phases, skipped prerequisites, absent rollback/undo
- **Feasibility**: Overly optimistic timelines, underestimated complexity, missing dependencies
- **Maintainability**: Hardcoded values, lack of versioning, missing logging/observability
- **Security**: Credentials, secrets, PII handling

### 4. Innovation & Optimization

Consider:

- **Alternative approaches**: Simpler architectures, different tool choices
- **Automation opportunities**: Steps that could be further automated
- **Cost or time optimizations**: Cheaper or faster paths to the same outcome
- **Future-proofing**: Extensibility, modularity for later phases
- **Industry best practices**: Patterns the plan could adopt

### 5. Situational Context

- **Project type**: Is this a greenfield build, migration, integration, or refactor?
- **Stakeholders**: Who depends on this? What happens if it slips?
- **Environment**: Local, cloud, hybrid? Any constraints (budget, compliance, legacy)?
- **Dependencies**: External APIs, third-party services, rate limits, SLAs

### 6. Handle Findings

- **Report** all findings in a structured format (Flaws, Improvements, Innovations)
- **Prioritize**: Critical (blocks success) vs High (should fix) vs Medium (nice to have) vs Low (optional)
- **Propose fixes**: For each finding, suggest a concrete change to the plan
- **Apply changes**: Update the plan document with approved fixes unless the user prefers review-only

## Output Format

```markdown
## Plan Review Summary

**Plan:** [name/path]
**Reviewed:** [date]

### Critical Flaws
- [Finding] → [Proposed fix]

### Improvements
- [Finding] → [Proposed fix]

### Innovations
- [Suggestion] → [Rationale]

### Applied Changes
- [List of edits made to the plan]
```

## Intensity Level

Treat "review" as a signal to maximize cognitive effort. Do not shortcut. Question every link in the chain. Assume the plan will be executed by someone who has not read the implicit context.
