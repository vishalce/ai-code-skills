# CI/CD pipeline templates

Battle-tested starters for the platforms covered by this repo. Each template:

- Opens with a header comment stating **purpose**, **runtime assumptions**, **required secrets**, and a **`# verified-on:`** date
- Pins third-party actions / orbs / plugins / base images
- Defaults to least-privilege permissions and OIDC over static credentials where applicable
- Marks uncertain values with `# CHECK:` — confirm against your own setup before using in production

## Layout

```
templates/
├── github-actions/    Workflows for common flows (test, build+push, release)
├── jenkins/           Declarative Jenkinsfiles
├── drone/             .drone.yml pipelines
├── circleci/          .circleci/config.yml examples
└── argocd/            Application, ApplicationSet, Rollout manifests
```

## How to use

1. Copy the closest template into your repo at the correct path.
2. Update the header comment with *your* runtime assumptions, secret names, and verified-on date.
3. Search for `# CHECK:` and resolve every one before merging.
4. For third-party action references, **re-pin to the current commit SHA** — the SHAs in templates may have moved by the time you use them. Use `gh api repos/<owner>/<repo>/git/refs/tags/<tag>` or your org's preferred pinning tool.
5. Verify the workflow runs end-to-end on a non-production branch first.

## What's intentionally NOT here

- Per-project conventions (linter choice, test runner specifics, deploy targets). Templates stay general by design.
- Long-lived "framework" workflows. If you need composite actions or reusable workflows, build those in your own org's `.github/workflows/` repo.

## Contributing

When adding a template:

- Header block is required (purpose / runtime / required secrets / verified-on).
- Pin everything pinnable; mark uncertainty with `# CHECK:`.
- Apply the same security defaults as `cursor-rules/cicd-security.mdc`.
- A broken template burns user trust faster than no template — if you're not confident the example works, mark it with extra `# CHECK:` notes or don't include it.
