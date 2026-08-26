# Resume this build

If a session ran out of tokens, timed out, or was interrupted:

```bash
cd ai-hedge-fund && cat BUILD_STATE.md
```

`BUILD_STATE.md` is the checkpoint. It lists every stage with a tick box, the
invariants that must never be violated, and the decisions already settled.
Continue at the **first unchecked box**. Everything above it is done and
committed — do not rebuild it.

The full requirement is in `docs/SPEC.md`.

**Prompt to paste into a fresh session:**

> Read `ai-hedge-fund/BUILD_STATE.md` and `ai-hedge-fund/docs/SPEC.md`, then continue
> the build from the first unchecked stage. Commit each stage to
> `claude/system-preference-ui-tcbs5o` and tick its box in the same commit.
