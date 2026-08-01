# The migration workflow

One workflow, every server-side language. Read it start to finish before touching code.

Two things shape it. First, the customer's codebase is the subject: the migration is a reading of how *they* use the SDK, not a find-and-replace. Second, **a human reviews the result** - say so at the start, and structure the work so reviewing it is actually possible.

Reference material, read alongside this:
- [`references/operations.md`](references/operations.md) - what each operation becomes, and which ones change runtime behavior. Language-independent.
- The language's symbol reference from the table in [`SKILL.md`](SKILL.md).

---

## M1: Set expectations, once, at the start

Before any analysis, tell the user plainly what this is:

> I will migrate what can be migrated safely, flag what changes behavior even though it compiles, and leave anything I cannot verify for you to decide. You should review the diff before shipping it, and run your test suite against it. Some of this is a judgment about intent, and I would rather ask than guess.

Do not skip this because it sounds like boilerplate. A customer who expects a push-button migration will misread the result.

## M2: Inventory every call site

This is the step that makes the migration complete, and it is what stops call sites being missed in files nobody opened. Enumerate first, then work the list.

Find the legacy dependency, then every reference to it:

```bash
# the dependency, in whichever manifest the language uses
cat go.mod pyproject.toml requirements.txt Gemfile composer.json pom.xml build.gradle *.csproj 2>/dev/null

# every file importing the legacy SDK, then every call site
grep -rn "<legacy package>" --include=<source glob> .
```

Record, for each call site: file, line, the symbol called, and how the result is used. **This list is both the work-list and the done-check.** At the end, nothing on it should be unaccounted for.

Also note the **import alias** the codebase uses, since every reference has to move, not just the import line.

## M3: Classify every call site

Put each one in exactly one bucket, using [`references/operations.md`](references/operations.md) and the language's symbol reference. Confirm each mapping against the SDK source or the official docs; the reference files are a strong starting point, not an oracle.

| Bucket | Meaning |
|---|---|
| **Safe** | Mechanical. Same behavior, different spelling. |
| **Behavior changed** | The new call works, and something about runtime behavior differs. Compiles clean, still needs the customer to act. |
| **Needs a decision** | The mapping depends on intent, and the code does not settle it. |
| **Not migrated** | No equivalent, or it cannot be verified. Left alone. |

Two rules hold this together:

- **Unclassified is not safe.** If you have not established what an operation does after migration, it is not in the safe bucket. Default to "needs a decision".
- **Never drop a field.** If a call sets something with no home in the new request, that is a decision, not a detail to quietly discard. Silently losing a field is worse than reporting it.

## M4: Agree the plan

Show the four buckets with counts, and the behavior-changed and needs-a-decision entries in full. Ask before applying. This is the customer's chance to say "leave the flagging code alone" or "we do not use that path any more", which is cheaper to hear now than after the edit.

## M5: Apply in reviewable slices

Work the inventory in groups that make sense to a reviewer, usually one area at a time: setup and auth, then users, then channels, then messages, then moderation, then devices.

For each slice:

1. Apply the mapping. Follow the transformation patterns in [`references/operations.md`](references/operations.md).
2. Rewrite **type references too**, not only calls. A client held in a struct field, a function parameter, a variable declaration: if the value keeps its legacy type, the migrated calls on it are not valid. This is a common cause of a migration that looks done and does not build.
3. Adjust **reads off responses**. The generated SDKs wrap results, so a field read directly from a legacy response usually moves one level down, and sometimes the field itself changed shape.
4. Re-run the search from M2 for the symbols in this slice, and confirm none survive except ones you deliberately left.
5. Verify (M6) before starting the next slice. A failure is much easier to place when the last change was small.

Do not refactor beyond the migration. It is a like-for-like port, and a reviewer has to be able to tell migration from improvement.

## M6: Verify

Run the language's own checks. What is available differs, and so does how much it proves:

| Language | Check | What it catches |
|---|---|---|
| Go | `go build ./... && go vet ./...` | Wrong types, wrong arity, wrong field names |
| Java | `mvn -q compile` or `./gradlew compileJava` | The same |
| .NET | `dotnet build` | The same |
| PHP | `composer install && vendor/bin/phpstan analyse` if configured, else `php -l` per file | Static analysis catches a lot; `php -l` is syntax only |
| Python | `mypy` if configured, else import the modules | Only as good as the type coverage |
| Ruby | the test suite; `ruby -c` is syntax only | Very little without tests |

**Say which of these you had.** On Go, Java and .NET a clean build is real evidence. On Ruby and Python, a clean run mostly proves the files parse, so **the customer's test suite is the only meaningful backstop** and the migration is correspondingly less certain. State that rather than presenting the same confidence everywhere.

Then run the customer's tests if they have them. If they do not, say so in the report: it is the single biggest gap in confidence.

## M7: Report

Give the four buckets, not a wall of diff:

- Dependency moved, with the old and new package and version.
- How many call sites were migrated safely. A count is enough.
- **Every behavior change, in full.** These compile and still change how the application runs, so they are the part that matters. Environment variable renames, operations that became asynchronous, anything whose storage or semantics moved.
- What you resolved from the needs-a-decision bucket, and what you left, with the reason.
- What was not migrated and why.
- What verification you ran, what it proves, and what it does not.

Close by naming the review the customer still owes: read the diff, run the tests, and check the behavior-changed list against the deployment environment.
