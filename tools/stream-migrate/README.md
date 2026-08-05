# stream-migrate

**Internal tool. Not shipped to customers and not referenced by the skill.**

A type-aware Go codemod that rewrites a `stream-chat-go` integration to `getstream-go`. It exists to *validate* the Go mappings the `stream-backend` skill relies on: if the tool can apply a mapping and the result compiles against the real SDK, the mapping in `skills/stream-backend/references/go.md` is correct.

It deliberately stays internal. Customers get one migration workflow across all six server-side SDKs, and shipping a tool that makes Go better than the rest would either invite "when do the other five get one" or quietly set the expectation that we owe five more codemods. We do not.

```bash
go run . ./path      # preview to stdout
go run . -w ./path   # apply in place
```

Requires Go 1.23 or newer.

## Why it is useful internally

- **It proves the mappings.** A mapping table nobody executes is a document with opinions in it. Running this over `testdata/chatmod` and building the result is evidence that the Go reference is accurate.
- **It catches silent field loss.** Rules decline whenever a call carries a field they do not map, rather than dropping it. That behavior is what caught a bug where channel members vanished when built from a variable.
- **It measures coverage.** The four-bucket report gives a real number for how much of a realistic integration is mechanical, which is hard to estimate by reading.

## Keeping it honest

`rules_test.go` and `rewrite_test.go` run without network or the real SDK. They cover the rewrites, the safety property that an unexpected call shape is declined rather than guessed, and that the reference documentation has not drifted from the implemented mappings.

`testdata/chatmod` is a representative Chat + Moderation integration written against the legacy SDK: several files, responses consumed, a spread of operations rather than a happy path. Copy it somewhere, run the tool over it, and build the result against `getstream-go`. Every remaining compile error should be one the report named.

## Limits

The mapping table is hand-written and reflects what has been verified against the SDK. Response payload field renames are not rewritten: `Data` is inserted, but where the field itself changed shape the compiler points at the read. Only literal arguments are reshaped; anything assembled at runtime is reported instead.
