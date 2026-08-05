# Fixtures

**Internal. Not shipped to customers.**

Representative legacy integrations used to exercise the `stream-backend` migration workflow before pointing it at anyone's real code. They are written to look like customer code rather than a happy path: split across modules, responses actually read, and a spread of operations including the ones that change behavior.

| Fixture | Language | Used by |
|---|---|---|
| `chatmod-python/` | Python, `stream-chat` | The skill workflow, run end to end |
| `../stream-migrate/testdata/chatmod/` | Go, `stream-chat-go` | The Go codemod's tests, and the skill workflow |

The Go fixture lives with the tool because its tests consume it. The Python one has no tool, which is the point: Python is where the workflow has to stand on its own.

## Running the workflow against a fixture

Copy it somewhere outside the repo first, so a failed run does not dirty the working tree, then drive the skill against the copy. Judge the result on three things:

1. **Did it find every call site?** Compare against a grep for the legacy import. Anything missed is the failure mode the inventory step exists to prevent.
2. **Did it flag the behavior changes?** The environment variable rename, the asynchronous delete, and the v1-to-v2 flag move are all present in both fixtures on purpose.
3. **Did it decline what it could not verify, rather than guessing?**

For Python, remember there is no compiler. A clean run proves the files parse, nothing more, which is exactly the confidence gap the workflow is supposed to be honest about.

## Verifying a fixture is itself valid

The Go fixture builds against the real SDK. The Python one cannot be checked that way, so its calls were verified by parsing the legacy SDK source and confirming every method exists with a compatible signature. That check caught one call passing a keyword argument to a method with no catch-all, which would only have failed at runtime. Re-run something equivalent after editing it.
