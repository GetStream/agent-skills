# stream-migrate

Rewrites a Go server integration from the legacy `stream-chat-go` SDK to the generated `getstream-go` SDK, and reports what it could not do.

```bash
go run github.com/GetStream/agent-skills/tools/stream-migrate@latest ./path      # preview to stdout
go run github.com/GetStream/agent-skills/tools/stream-migrate@latest -w ./path   # apply in place
```

The `stream-backend` skill runs this and handles what the report leaves behind. It is also useful on its own.

## What it does

- Detects legacy calls with `go/types`, so it matches on what a call resolves to rather than on how it is spelled.
- Rewrites call sites from a fixed mapping table (sub-clients, request structs, pointer fields, functional options folded into fields).
- Rewrites legacy type references such as a client held in a struct field, because rewriting calls alone leaves the value they are called on with the wrong type.
- Moves reads off a response under `Data`, since the generated calls return an envelope.
- Classifies every call site and prints a report.

## The report

Four buckets, because "it compiles" and "it behaves the same" are different questions:

| Bucket | Meaning |
|---|---|
| APPLIED, SAFE | Mechanical rewrite, no behavior change. Accept in bulk. |
| APPLIED, BEHAVIOR CHANGED | Rewritten and compiles, but runtime behavior differs. Read each one. |
| NEEDS A DECISION | Not rewritten. The mapping needs a judgment the tool will not make. |
| NOT MIGRATED | No mapping. Left untouched. |

A rule with no explicit behavior classification is never reported as safe by accident: rules carry the note with them, and anything the table does not cover is reported rather than guessed at. The environment-variable rename and the sync-to-async delete are the clearest reasons the second bucket exists, since both compile cleanly and both break production if missed.

## Limits

- The mapping table is hand-written and covers what the migration guide documents. Generating it from the OpenAPI spec is the intended next step, so coverage tracks the SDK instead of being maintained by hand.
- Response *payload* field renames are not rewritten. `Data` is inserted, but where the field itself changed shape, for example a single `User` becoming a `Users` map, the compiler points at the read and a human fixes it. The report says how many reads were moved so this is not a silent gap.
- Only literal arguments are reshaped. A call built from variables degrades to "needs a decision" instead of being rewritten wrongly.

Always finish with `go build ./... && go vet ./...`. The tool is deliberately conservative, and the compiler is the backstop.

## Testing against a realistic integration

`testdata/chatmod` is a representative Chat + Moderation integration written against the legacy SDK: several files, responses actually consumed, and a spread of operations rather than a happy path. Copy it somewhere, run the tool over it, and build the result.
