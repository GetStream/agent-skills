# Operations and what changes

Language-independent. Read this with the language's symbol reference: this file says what an operation *becomes* and whether behavior changes, the symbol reference says what it is *called*.

The classification here is the input to M3 in [`../migrate.md`](../migrate.md). Anything not listed is not automatically safe: it is unclassified, which means it needs a decision.

---

## Transformation patterns

These recur across the whole surface. They are how the generated SDKs are shaped, not per-operation trivia.

| Pattern | Legacy | Generated |
|---|---|---|
| Sub-clients | Everything on one root client | Grouped: chat, moderation, video, feeds |
| Requests | Loose positional arguments | One typed request object per operation |
| Optional fields | Zero values, or functional options | Explicitly optional, often nullable or pointer-wrapped |
| Custom data | An extra-data bag | A `custom` map |
| Options | Functional options or option structs | Fields on the request object |
| Responses | Payload read straight off the result | Wrapped, so the payload sits one level down |
| Members | Plain user id strings | Member objects |

The response wrapping matters more than it looks: moving a read down one level is mechanical, but some payload fields also changed shape, most commonly a single object becoming a keyed collection. Check the field, not just the nesting.

---

## Behavior changes

Every one of these produces working code that behaves differently. They belong in the behavior-changed bucket, and every one goes in the final report.

### Environment variables renamed

Constructing a client from the environment reads different variable names than the legacy SDK did. The code compiles, the deployment does not authenticate until its environment is updated. This is the easiest one to miss because nothing in the source looks wrong.

### Delete became asynchronous

Deleting a user, and deleting channels in bulk, are now batch operations that return a task identifier and complete in the background. Legacy code that assumed the work was finished when the call returned needs to poll the task instead. Anything reading state straight after a delete is suspect.

### Flagging moved from v1 to v2 moderation

The legacy flag calls wrote the v1 chat flags store. The generated SDKs expose v2 moderation. Content flagged through v2 may not be visible to a v1 flag query, so swapping one call in isolation can leave a workflow writing to one store and reading from another. Migrate flagging, querying and review together, or leave the whole workflow on the old path until you can.

### Single-item calls became batch

Several operations that took one id now take a collection. Partial failure becomes possible where it was not before: one bad entry can change the outcome for the rest.

### Typed constants became plain strings

Push provider constants, and similar enumerations, are plain strings now. Mechanical, but a value the legacy SDK would have rejected at compile time is now only rejected by the API.

---

## Needs a decision

These have no single right answer, so the code has to be read.

### Token expiry

Token creation moved from an absolute expiry time to a duration-based option. The value has to be recomputed, and code that derived the timestamp from something else needs rethinking rather than translating.

### Types that split in two

The legacy SDKs used one type for both directions: the same user type went out on a create and came back on a read. The generated SDKs split these into request and response types. Decide per use:

- Built as a literal and passed into a call: the request type.
- Assigned from a call result, or read from a response: the response type.
- A function parameter or field: follow the callers. If a helper is used in both directions, split the helper rather than forcing one type on both paths.

### Queries and filters

Filters, sorting and pagination moved into structured request payloads, and the field names changed. Straightforward when the query is a literal; when it is assembled at runtime, the assembly code has to move too, which is a small refactor rather than a substitution.

### Review workflows

The v1 flag-report workflow was replaced by a review queue with a different model: query the queue, read an item, submit an action against it. There is no one-to-one mapping, so this is a redesign of the moderation workflow, not a rename.

---

## Not migrated

Operations with no documented equivalent, or that cannot be verified against the SDK source, are left alone and reported. In practice this is the long tail of the legacy Chat surface: uploads, unread counts, threads, drafts, polls, reminders, commands, permissions and roles, import and export, and translation.

Leaving them is correct. The legacy SDK keeps working, so a partial migration is safe as long as the customer knows which parts are still on the old path.
