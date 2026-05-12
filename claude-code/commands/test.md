---
description: Write or extend tests for the current change, focused on what's worth testing
argument-hint: "[optional: file or function name to focus on]"
---

Write tests for the current change or for the file/function specified by `$ARGUMENTS`.

Steps:
1. Identify the test framework already in use (look at `package.json` test scripts, `pyproject.toml`, `Cargo.toml`, existing test files). Match its style — don't introduce a new framework.
2. Find existing tests for the target module and match their conventions (file naming, describe/it structure, fixture patterns).
3. Read the code under test end-to-end. Identify:
   - The happy path
   - Each explicit error branch
   - Boundary values (0, 1, max, empty, null/undefined)
   - Any bug being fixed (write a failing test that locks in correct behavior)
4. Use Arrange / Act / Assert structure.
5. Test names describe the behavior, not the function: `'rejects orders below minimum amount'` — not `'validateOrder'`.
6. Don't over-mock. If you mock the function under test, the test is meaningless. Prefer fakes/in-memory implementations over call-recording mocks.
7. After writing, output the run command (`npm test`, `pytest path/to/test`, etc.) so the user can verify.

If the user asked to test a bug fix, write the failing test BEFORE the fix and confirm it fails for the right reason, then propose the fix.
