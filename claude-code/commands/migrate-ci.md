---
description: Translate a CI/CD pipeline from one platform to another (Jenkins/CircleCI/Drone ↔ GitHub Actions). Outputs translation table + migrated config + verification checklist.
argument-hint: "<source-platform> <target-platform> — e.g. 'jenkins github-actions' or 'circleci github-actions'"
---

Translate a CI/CD pipeline between platforms while preserving intent — not just syntax.

**Args:** `$ARGUMENTS` should be `<source> <target>`. Supported: `jenkins`, `circleci`, `drone`, `github-actions`. If empty or invalid, ask the user.

Steps:
1. **Locate the source config.** If the source is `jenkins`, look for `Jenkinsfile`. `circleci` → `.circleci/config.yml`. `drone` → `.drone.yml`. `github-actions` → `.github/workflows/*.yml`. If multiple workflow files exist for GHA, ask which one.
2. **Read the source end to end** before translating anything. Some constructs only make sense in the context of the full file.
3. **Identify non-1:1 constructs** (Jenkins shared libraries, CircleCI orbs, Drone plugins, Groovy `script {}` blocks). For these, ask the user what they do — don't invent behavior.
4. **Apply universal CI/CD principles** during translation: pin third-party actions to SHA, least-privilege permissions, OIDC over static creds, explicit timeouts, header comment with purpose / runtime / required secrets / `verified-on:` date.
5. **Produce a verification checklist** of things the user must wire up on the target side that the YAML alone can't capture (secrets, OIDC trust policies, branch protection, environment configs, status check names).

Output:

```
## Migration summary
[2–3 sentences: source → target, headline gotcha.]

## Constructs that don't map 1:1
[Translation table for the specific constructs in this pipeline. Skip clean mappings.]

## Translated pipeline
[Single fenced code block with the new config. Standard header comment.]

## Verification checklist
[Concrete things the user must do on the new side. Names of secrets to create, OIDC roles, environments, branch protection.]

## Things I'm unsure about
[Anything marked `# CHECK:` in the YAML, with the reason. Custom plugins, shared libraries, unclear semantics.]
```

Don't:
- Translate syntax without translating semantics. `agent any` → `runs-on: any` is wrong (that's invalid).
- Carry forward unpinned dependencies. Pin during the migration; mention this as an upgrade.
- Invent credential names. Use the user's existing names or ask. Add the recreation step to the verification checklist.
- Hide stage parallelism behind sequential steps. Preserve concurrency.

For a fresh pipeline (not a translation), use `/pipeline-review` style review on the existing source first, then write from scratch with `cicd-config-author`.
