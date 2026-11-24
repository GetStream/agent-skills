---
name: stream-security-audit
description: "Security audit of an SDK, client library or package, on any platform and for any product: Stream's SDKs or any other (iOS/Swift, Android/Kotlin, web/JS/TS, React Native, Flutter, Unity, Electron, .NET, or server SDKs in Go/Python/Ruby/Node/Java/PHP/Rust). Walks a catalog of 148 explicit checks - secrets in code, samples, git history and packages; non-expiring tokens; tokens in logs, URLs and errors; weak transport; untrusted content from other users or from LLM output; unsafe links; data left after logout; remote crashes; vendored native code; CI and supply chain - verifies each finding, separates what is proven from what depends on the server or integration, and writes a calibrated report with a coverage ledger. Use when asked to audit, pentest, threat-model, harden or find vulnerabilities or security issues in an SDK, library, framework or package, or to re-check an existing SDK security report. For a single diff or PR, use a diff-focused review instead."
license: See LICENSE in repository root
compatibility: "Read-only on the audited repository. Needs bash, git and perl for the recon script, which is written from recon.md into a scratch directory, run, then deleted. Network is used only for advisory checks of public dependencies, and for runtime proofs the user's toolchain supports (simulators, local harnesses). Never sends exploit traffic to live services."
metadata:
  author: GetStream
---

# SDK security audit

An SDK is code that runs inside other people's apps, with those apps' privileges, data and users. One flaw ships to every integrator, and integrators rarely read SDK internals, so they inherit its defaults. Audit with that in mind: the question is always "what can an attacker do to an app, or its users, because it embeds this SDK?"

The output is a calibrated report of **security vulnerabilities**: things an attacker can do to the app, its users or their data because the app embeds this SDK. Performance, compliance, code quality and product choices with no attacker are not findings; drop them, or give them one line under "Reviewed and rejected". Every finding is traced from an attacker-controlled source to a sink in code that actually ships. Every finding states separately what was proven and what still depends on the backend, the integration or the platform. A short list of real issues is worth far more than a long list of grep hits. Overclaims cost the team's trust in the whole report, and so do false positives.

## Ground rules

- **Read-only by default.** Don't modify the repo, push, open issues or PRs, or comment publicly. Vulnerability details in a public tracker before a fix are a disclosure. Fixes are a separate step the user asks for.
- **No live attacks.** Don't send exploit traffic to production services or third parties. Verify with code reading, unit tests, local harnesses, a local mock server, or a development backend the owner points you to.
- **Protect the audit's own evidence.**
  - Work with `umask 077`, in a scratch directory outside the repository.
  - Put the report outside the repo (or in a gitignored path) and tell the user where it is.
  - Recon output masks secret values by default. Never copy a real token, key or password into notes, the report or a sub-agent prompt. Refer to it by type, location and fingerprint.
  - At the end, decide what to keep: a private evidence folder next to the report, or nothing. Delete dependency checkouts, build products and derived data you no longer need.
  - If the repo has a `SECURITY.md`, note its disclosure channel in the report.
- **Stay inside the agreed scope.** Dependencies count when the SDK relies on them. First-party dependencies (the vendor's own core, networking or UI libraries) often hold the riskiest code: transport, auth, decoding, logging. Check them out at the exact resolved revision from the lock file into scratch; local package caches are often several versions stale.
- **Other private repositories need the user's say-so.** Server source can turn a conditional finding into a confirmed one without touching production, but reading a separate private repository (the backend, internal tools) widens the audit. Read it only when the user has put it in scope, or after asking. Record its commit for every claim that relies on it.

## Workflow

### 1. Scope: record exactly what is audited

From the repo and the user's request, record the following. They go into the report's scope section verbatim.
- **Revision**: the full commit SHA, branch, dirty or untracked state, submodules and LFS objects. If the worktree isn't clean, either audit `HEAD` and say local changes are excluded, or audit the worktree and list the uncommitted files. Never describe one and search the other.
- **Shipped code**: which products, packages or targets ship to integrators. Distinguish base SDK, optional modules and add-ons, test-support products, samples, tooling.
- **Platforms**: supported platforms and minimum OS versions, and which ones you will actually run things on.
- **Dependencies**: resolution files used, and first-party and security-relevant dependencies at their resolved revisions.
- **Exclusions**: excluded modules and why. If server source is used, its repository and commit.

Demo and sample apps are in scope as *guidance integrators copy*, at lower severity than shipped code. If scope is genuinely ambiguous (a monorepo with many products), ask. Otherwise state your assumptions and proceed.

### 2. Recon

The recon script is kept as text in recon.md; the plugin doesn't ship it as code. Write it to a scratch directory outside the audited repository, run it from there, and delete it when the audit ends. Don't commit it, and don't write it into the skill directory or the audited repository. To copy it exactly, extract the fenced block from recon.md (use the path you read recon.md from):

```bash
umask 077
awk '/^````bash$/{f=1;next} /^````$/{f=0} f' <path-to>/recon.md > <scratch>/recon.sh
bash <scratch>/recon.sh <repo> [--untracked] [--history] > <scratch>/recon-output.md
```

It prints the scope facts above, then inventories:
- languages and manifests;
- likely vendored code and native code;
- submodules, symlinks, executables and binaries;
- build plugins and install scripts;
- CI files, and committed sensitive files.

It then lists:
- pattern leads, each labelled with the catalog IDs it serves (`[LOG-01]`, `[AUTH-05]`...);
- a table of every JWT in the repository, with its algorithm, claim names, expiry and lifetime, but never the signature. It shows non-expiring tokens in samples and fixtures (AUTH-01);
- the dependency-advisory commands to run for the ecosystems it detects.

Secret values are masked unless you pass `--show-secret-values`. Tests and mocks are left out of leads by default, but test-support products in manifests are listed, because some packages publish them. `--history` also searches git history for high-confidence secrets. Every hit is a lead to triage, never a finding by itself. Its vendored-code detection is heuristic: confirm vendored directories from documentation, update scripts and license files.

Then read the platform notes for each language present: `references/platforms/apple.md`, `android.md`, `web-js.md`, `cross-platform.md` (React Native, Flutter, Unity/Unreal, Electron, C/C++/Rust) and `server.md` (backend SDKs). Also read the public API surface: the entry points integrators call, and their defaults, matter as much as internals.

### 3. Distribution: audit what ships, not just what is tracked

The source tree and the published artifact differ more often than expected:
- files excluded or added by the package manifest;
- prebuilt bundles and generated code;
- source maps;
- test helpers published as products.

Before hunting:
1. Enumerate the products and targets per distribution channel (SwiftPM, CocoaPods, XCFramework; Maven/AAR; npm; PyPI; RubyGems; crates.io; NuGet; pub.dev...) and per platform variant.
2. Build or dry-run each artifact and list its contents. The commands are in the platform notes, e.g. `swift package describe`, `pod ipc spec`, `./gradlew assembleRelease` + `unzip -l`, `npm pack --dry-run`, `python -m build` + `unzip -l`, `gem build` + `tar -tf`, `cargo package --list`, `dotnet pack`.
3. Compare the contents with your scope. Look for resources, native libraries, generated code, source maps, scripts and test helpers: anything that ships code or secrets the source review didn't cover.
4. For each first-party and security-relevant dependency, record the resolved revision, then audit or explicitly exclude it. Run the ecosystem's advisory check and record the tool and the advisory-database date. A version match is a lead; the finding is whether the vulnerable code is compiled in and reachable.
5. Give each vendored library a disposition: version, provenance, update path, local patches, and known advisories with their applicability.

### 4. Threat model

Write a short threat model before hunting; it tells you which leads matter. Keep it to a table or two.

- **Assets**:
  - credentials: tokens, keys, cookies;
  - user content and personal data;
  - files and media;
  - device capabilities the host app has been granted: camera, location, contacts;
  - the host app's own deep links and session;
  - the integrity of what users see.
- **Entry points**:
  - network responses and real-time events;
  - content authored by other users;
  - push payloads;
  - deep links and IPC;
  - files from other apps;
  - integrator configuration;
  - LLM output and tool calls;
  - local storage read back at launch.
- **Content provenance**: for each field you rely on, who writes it: the backend itself, another user (peer), a model, the integrator, or the device. Don't assume every decoded field is peer-controlled. Server-generated fields, fields the server normalizes, and fields only an admin can set change the attacker position.
- **Attackers**, in rough order of importance for most SDKs:
  1. *remote peer*: another user who can send content; cheap, and scales to many victims;
  2. *model output*: steerable by prompt injection;
  3. *malicious or compromised backend, CDN or third-party host*;
  4. *network attacker*: only where transport protection can be weakened;
  5. *local app or process*;
  6. *person with the device after logout*: shared devices;
  7. *integrator misuse* of insecure defaults.

The catalog references/checklist.md lists every check, each with an ID (`SECRET-01`, `AUTH-01`, `LOG-01`...). Read it all once; the threat model tells you where to go deep, not what to skip.

### 5. Hunt: walk the whole catalog

Go through **every item** in `references/checklist.md`, and record its result in the coverage ledger as you go (format at the end of the catalog). Start a ledger row for each ID up front, so gaps stay visible. Items that can't apply get N/A with a reason (an iOS SDK has no exported Android components); they don't disappear. Coverage matters because the expensive misses are mundane ones: nobody decoded the sample token to see it never expires, or read what the error path logs.

Order the work by the threat model. These items most often turn into real SDK findings, so do them first and deeply:

1. **Secrets and token hygiene** (SECRET-01 to SECRET-08, AUTH-01, AUTH-05, AUTH-07, AUTH-08, LOG-01, LOG-05):
   - server secrets or provider keys shipped in code, resources, samples, history or packages;
   - non-expiring tokens in samples and docs, or as the easy API path;
   - tokens in URLs, in logs at default levels, in error descriptions, in `description`/`toString`, in backups;
   - decode every JWT recon finds.
2. **Credentials sent to the wrong host** (AUTH-06, TLS-04): a shared HTTP client attaching auth headers to URLs taken from content (attachments, images, previews, redirects).
3. **Remote crash** (INPUT-01 to INPUT-05, INPUT-13): a peer-controlled field reaching a force unwrap, a trapping numeric conversion, unbounded recursion or an unchecked index. In collaborative products this can crash every recipient, sometimes on every launch.
4. **Files and paths from content** (STORE-03, STORE-04): names from payloads becoming file paths.
5. **Cross-user data after logout or user switch** (SESSION-01 to SESSION-05): database, file caches, queued requests, push registration.
6. **Untrusted content rendered with too much power** (RENDER-01 to RENDER-06): web views with JavaScript or file access, auto-loading remote resources, spoofable UI.
7. **AI features** (AI-01 to AI-10): model output triggering tool calls or URL loads without user confirmation; exfiltration through computed or auto-loaded URLs; resource limits in model-written programs.
8. **Transport, storage and defaults** (TLS, STORE, API): weakened TLS, plain-text tokens, insecure defaults integrators won't change.
9. **Links and schemes** (LINK-01 to LINK-03): content opening the host app's own deep links or other apps.
10. **Supply chain and CI** (SUPPLY, DIST):
    - unpinned actions in workflows that hold signing secrets;
    - unverified tool downloads;
    - injection from event fields;
    - vendored code with known advisories.

Then finish the rest of the catalog. A "Clean" result needs evidence: the code you read or the test you ran, in one line. "No grep hits" isn't evidence on its own, because grep finds names, not data flow.

For each candidate, name the **security invariant** it breaks, in one sentence. For example: "peer metadata must not choose a path outside the downloads folder", or "a URL computed from a password field must never be fetched". If you can't name an attacker, an invariant the SDK promises or clearly should promise, and a concrete security impact (confidentiality, integrity, availability, or control of the user's account or device), it isn't a vulnerability. At most it is a hardening line (step 7).

**Splitting a large audit.** When the codebase is too big to read closely alone (roughly >50k lines, or several independent modules), split it by *trust boundary or concern*, not by directory. For example: auth+transport+session, storage+files, untrusted-payload parsing, UI rendering+links, AI features, supply chain.
- Give each sub-agent:
  - the threat model;
  - its catalog IDs: every ID must belong to exactly one reviewer, yourself included;
  - the platform notes;
  - exact paths, including dependency checkouts;
  - the output contract below, and the evidence rules from step 6.
- Tell it to stay read-only, and never paste secrets into its prompt.
- Keep one concern for yourself, so you understand the codebase firsthand.
- Ask sub-agents to write small reproductions in scratch, and to pass on leads outside their area instead of dropping them.
- Two reviewers finding the same bug from different directions is useful corroboration, not waste.

Output contract for each candidate (yours or a sub-agent's):
- title; `file:line` references; the invariant broken; the attacker position and the capability it needs;
- the source -> sink trace as a concrete call chain, with the provenance of the source field;
- exposure: base default, optional-module default, opt-in, sample only, or build & release; and the exact configuration needed;
- the evidence dimensions from step 6, each with its value;
- impact, suggested class, severity and fix;
- the catalog IDs it covers.

Each reviewer also returns a ledger row for every catalog ID it was given: Clean with evidence, N/A with a reason, or Not checked with a reason. Missing rows mean the area wasn't covered.

### 6. Verify: establish each part of the claim separately

Sub-agent reports, grep hits and outside reviews come back in the same confident tone whether they are right or wrong. Before anything goes in the report, open the code and walk the chain. Record each of these separately; together they decide the status and the severity:

| Dimension | Values |
|---|---|
| **Weakness** (client code) | Confirmed in source / Reproduced with target code / Not confirmed |
| **Reachability** (can the attacker deliver it?) | Confirmed end-to-end / Conditional on *named fact* / Not established |
| **Exposure** (who has it enabled?) | Base default / Optional-module default / Opt-in / Sample only / Build & release |
| **Runtime impact** | Reproduced on target (platform named) / Proxy harness only / Inferred |
| **Persistence** (when claimed) | Confirmed / Conditional / One-shot / N/A |

A finding is **Verified** only when everything its severity relies on is established. Otherwise it is **Conditional**, and the report says exactly which fact would promote it (or demote it). A client weakness can be certain while the remote attack is still conditional. Say both.

Walk each hop:
- **Source.** Is the input really attacker-controlled, from the position claimed? Who authors the field? Does the server accept, normalize or reject it? A value the integrator sets is not a remote attack.
- **Path.** Does data actually flow there in shipped code, with the stated configuration? Check call sites, not just the function. Check whether the feature is in the base SDK or in an optional module, and what its default is.
- **Mitigations.** Look for:
  - validation upstream and sanitization downstream;
  - caps already in place: bytes, pixels, depth, counts, timeouts;
  - server-side checks the SDK can rely on;
  - platform protections (e.g. the OS refusing a scheme);
  - user-gesture gates;
  - existing tests that pin the safe behavior.

  Read the limits before writing "unbounded".
- **Sink.** Does the dangerous operation behave the way the finding assumes? When cheap, prove it, preferring the *real module* on the *real target* (a unit test, or a test target in a scratch package that depends on a snapshot of the audited commit) over a copy of the code. A copied parser on a desktop OS is a proxy: it shows the algorithm is wrong, not that the shipped app crashes. Label it that way. Stack sizes, memory limits and OS behavior differ between platforms, simulators and devices.
- **Novelty.** Is it already documented as intended behavior, tracked in an issue, or guarded by a comment explaining the trade-off? Still report it if it's a risk, but say so.

Keep every runtime proof reproducible, in the evidence folder:
- the exact source and dependency revisions;
- platform, OS, architecture, device or simulator;
- compiler and build configuration;
- the exact command and the input generator;
- the observed result (exit status or signal, top crash frames, timing, peak memory);
- whether the target code was imported or copied;
- a sketch of the regression test the fix should add.

Downgrade or drop what doesn't survive. Keep a short "reviewed and rejected" list; it shows the reader what was considered and saves the next auditor time.

Common false positives and overclaims to avoid:
- Public identifiers flagged as secrets: publishable API keys, app IDs, client IDs, auth-type headers, tenant IDs. The question is whether a *secret* ships or leaks.
- Dev-only token helpers that are clearly named and documented, and that the server rejects in production.
- Test fixtures, mocks, sample data, comments and documentation URLs.
- Force unwraps on constants, SDK-generated values, or already-validated data.
- "Uses HTTP" when it's a comment, a namespace URI, or a localhost test server.
- Bounded resource handling described as unbounded (a per-request cap exists, but nothing limits concurrency or the total: report that narrower point).
- Ordinary semantics described as flaws: Markdown link text differing from its destination, or an action behind a deliberate, labelled user tap described as running "without consent".
- Platform protections re-flagged without a concrete bypass (e.g. sandboxed OS previewers).
- Server-side authorization issues blamed on the client: if the server enforces it, hidden UI is fine.

### 7. Classify and rate

Classify each item before rating it (details in `references/reporting.md`):
- **Vulnerability**: an attacker crosses a trust boundary the SDK promises or clearly should, with concrete security impact. This is a finding.
- **Conditional vulnerability**: the client weakness is established, but reachability or impact depends on a named external fact. This is a finding.
- **Hardening**: a security-relevant gap without a demonstrated attack path. It gets one line in the hardening appendix, with no severity.
- **Everything else** (an action the user deliberately chose, standard platform or Markdown semantics, compliance and declarations, performance with no attacker, code quality): not reported. Add a one-line "Reviewed and rejected" entry when a reader might expect it.

Remote crashes and freezes that an attacker can trigger *are* vulnerabilities (availability), and so are resource exhaustion and denial of service from content.

Rate severity with the rubric in `references/reporting.md`. Weigh:
- **attacker position**: remote peer or model output > malicious host > network > local > physical;
- **exposure**: base default for every integrator > optional-module default > opt-in > sample;
- **impact**: credential theft, code execution and cross-user data exposure first; then persistent remote crash and phishing via trusted UI; then leaks of personal data or metadata;
- **scale**: one victim, or every member of a channel.

Rate what is established. When a missing fact would change the rating, write it as two parts: "Medium; High if the backend accepts and re-delivers the payload". When a default applies only inside an optional module, say "High for apps that use <module>". Never let it read as every integrator.

Wording rules that keep reports honest:
- Don't write "any member" or "any user" until membership permissions, field acceptance, persistence and delivery are all established.
- Don't write "persistent" until the bad value is shown to survive and be reprocessed after relaunch.
- Don't write "crashes on iOS" (or any platform) from a proxy harness: say where it was reproduced, and that the target impact is inferred.
- Don't call an identifier a secret. Name the actual credential.

### 8. Report

Give each distinct root cause its own ID. Group items into one finding only when they share a root cause *and* a fix, such as everything left behind after logout. Don't group by broad category: "supply chain" or "resource limits" usually hides several issues with different owners and severities. Keep IDs stable when you revise a report: mark withdrawn or reclassified items rather than renumbering.

Write the report with the template in `references/reporting.md`:
- summary and summary table (ID, severity, title, class, exposure, status);
- scope record; method; threat model;
- findings, most severe first, each with its evidence block;
- distribution and dependency coverage; platform and evidence coverage;
- a short hardening appendix (security-relevant, one line each);
- positive observations; reviewed-and-rejected leads;
- open questions, i.e. facts that would promote or demote conditional findings;
- revision history, when the report is updated.

Keep each finding self-contained so it can be pasted into a ticket, and give each finding the catalog IDs it falls under.

Save the coverage ledger next to the report (`<report-name>-coverage.md`), with the same permissions. The report's Method section summarizes it:
- how many items were checked;
- results by type;
- every item that's Not checked, and why.

Then give the user a brief summary in chat:
- counts by severity, and verified vs conditional;
- the top issues, one line each;
- where the report, the coverage ledger and the evidence are, and which catalog items weren't checked;
- suggested next steps: fix order, and what to confirm with the backend team.

Offer to fix specific findings, add regression tests, or turn the report into tickets. Don't start without being asked.

### Re-checking an existing report

When asked to review or recalibrate a report (yours or someone else's), apply steps 6 to 8 to each finding:
- re-read the code at the recorded revision;
- check every factual claim, including the reviewer's;
- set the evidence dimensions;
- reclassify;
- build or update the coverage ledger, and run the catalog items the report never covered. A report without a ledger usually skipped whole areas;
- record the changes in a revision history.

Accept corrections that hold up, say plainly which ones don't, and keep stable IDs.
