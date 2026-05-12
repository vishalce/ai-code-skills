---
name: test-debug
description: Writes tests, reproduces bugs, traces failures, and debugs unexpected behavior. Use whenever the user says "write tests", "add tests", "test coverage", "this is broken", "doesn't work", "I'm getting an error", "help me debug", "reproduce", "flaky test", asks why something fails, pastes a stack trace, or shares failing test output. Covers unit, integration, and end-to-end tests across common frameworks (Jest, Vitest, Pytest, Go test, JUnit, RSpec). Also covers root-causing — not just patching symptoms.
---

# Test & Debug

Two related jobs in one skill: **writing tests** for code that has none, and **debugging** code that's misbehaving. They share a discipline — both are about understanding what the code actually does versus what you think it does.

## When to use

Trigger when the user:
- Says "write tests", "add coverage", "test this"
- Pastes a stack trace, error message, or failing test output
- Says "it's broken", "doesn't work", "weird bug", "intermittent", "flaky"
- Asks "why does X return Y?"
- Asks to reproduce a bug in a minimal example

## Writing tests

### Before writing anything

1. **Find existing tests** for the module — match their style, framework, and naming. Don't introduce Vitest into a Jest codebase because you prefer it.
2. **Identify what's worth testing.** Logic with branches. Edge cases. Error paths. Public API contracts. Don't test trivial getters, framework internals, or implementations that will change next week.
3. **Decide the level.** Unit (pure logic), integration (touches DB/queue/HTTP, with real dependencies or test doubles), end-to-end (full stack). Pick the *lowest* level that meaningfully validates the behavior.

### Structure each test as Arrange / Act / Assert

```ts
test('rejects orders below minimum amount', () => {
  // Arrange
  const order = buildOrder({ amount: 50 });
  
  // Act
  const result = validateOrder(order, { minimum: 100 });
  
  // Assert
  expect(result.ok).toBe(false);
  expect(result.reason).toBe('BELOW_MINIMUM');
});
```

### Good test names describe the behavior

- ✗ `test('validateOrder')` — what about it?
- ✗ `test('returns false')` — for what input?
- ✓ `test('rejects orders below minimum amount')` — input + expected behavior

### Coverage targets to aim for, in order

1. The happy path (one test)
2. Each error case the function explicitly handles
3. Boundary values (0, 1, max, max+1, empty, null)
4. The bug that motivated this test — if there is one, write a test that fails without your fix

### Don't over-mock

If a test mocks the function under test, it's not testing anything. If a test mocks so many dependencies that it only verifies the mocks are called in order, it's tautological — it will pass even when the code is broken. Prefer real implementations where possible; use fakes (in-memory implementations) over mocks (call-recorders) where you can't.

## Debugging

### The discipline

The bug is in the *gap* between what you believe the code does and what it actually does. Your job is to close that gap, one verified fact at a time. Don't guess and patch — diagnose, then fix.

### Step 1: Reproduce

A bug you can't reproduce is a bug you can't fix. Get to a minimal, reliable repro before doing anything else.

- If the user describes the bug but you don't have a repro, ask for: exact inputs, expected output, actual output, environment.
- If they share a stack trace, treat it as a lead, not the answer. The line where it throws is rarely the line where the bug is.
- For intermittent bugs, ask: when does it happen? when doesn't it? Look for state, timing, concurrency, or external dependency variance.

### Step 2: Form a hypothesis, then verify it

State the hypothesis explicitly: "I think this fails because `userId` is undefined when the cache miss path runs." Then prove or disprove it with one of:

- A test that fails the way the bug fails
- A log line that confirms the state at the moment of failure
- A debugger breakpoint at the suspected location

Don't change code to "see if that fixes it" before you've verified the hypothesis. That path leads to fixes that paper over the real bug.

### Step 3: Fix at the right level

Three places to fix any bug — pick deliberately:

1. **At the symptom** — e.g., null-check before the crash. Sometimes correct (defensive at a trust boundary), often a band-aid.
2. **At the cause** — fix where the bad value originated.
3. **At the design** — the cause is structural; the fix is to make the bad state unrepresentable (types, invariants, validation at the boundary).

Default to #2. Choose #3 if the bug class will recur. Choose #1 only with a written reason.

### Step 4: Add a regression test

Every bug fix gets a test that would have caught it. No exceptions for "trivial" bugs — those are exactly the ones that come back.

## Flaky tests

A flaky test is a test that passes sometimes and fails sometimes on the same code. Causes, in order of frequency:

1. **Timing** — `setTimeout`, polling, real clocks. Fix: fake timers, deterministic waits.
2. **Order dependence** — tests share state. Fix: reset state in `beforeEach` or use isolated fixtures.
3. **Concurrency** — parallel tests touch the same resource. Fix: per-test resources (DB schemas, temp dirs) or run serially.
4. **External dependencies** — real network, real DB. Fix: stub the boundary or move to integration tier.

Don't `retry: 3` your way out of a flaky test. That's hiding signal.

## Examples

**Example — Writing a test for a bug:**
> User: "The discount code `SUMMER25` should give 25% off but it gives 5%. Can you fix it?"
> Response: "Before I fix it, let me write a failing test that locks in the expected behavior — that way we'll know it's fixed and won't regress."
> ```ts
> test('SUMMER25 applies 25% discount, not 5%', () => {
>   const total = applyDiscount({ subtotal: 100, code: 'SUMMER25' });
>   expect(total).toBe(75); // currently returns 95
> });
> ```
> "Now let me find the bug..."

**Example — Debugging output:**
> ## What I know
> - The API returns 500 on POST /orders with payload X
> - Stack trace points to `OrderService.create:142`
> - Line 142 does `order.items.map(...)` 
>
> ## Hypothesis
> `order.items` is undefined for this payload. The DTO schema marks `items` as optional but the service assumes it's an array.
>
> ## Verification
> Logged the payload at the controller entry — `items` is indeed absent. Confirmed.
>
> ## Fix options
> 1. Default `items` to `[]` in the service (symptom — accepts empty orders silently)
> 2. Reject the request at the controller if `items` is missing (cause — invalid input rejected at the boundary)
>
> I'd go with #2 unless empty orders are a valid case. Which is it?
