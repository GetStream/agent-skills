# Classification, evidence, severity and reporting

Contents
1. Classes
2. Evidence and status
3. Severity rubric
4. Report template
5. Writing tips

## 1. Classes

The report is about security vulnerabilities. Classify before rating: only the first two classes are findings.

| Class | Use when | In the report |
|---|---|---|
| **Vulnerability** | An attacker crosses a stated or strongly implied trust boundary and gets concrete security impact: confidentiality, integrity, availability, or control of the user's account or device. You can name the broken invariant. | A finding, rated with the rubric below |
| **Conditional vulnerability** | The client weakness is established, but reachability or impact depends on a named external fact (server acceptance, a configuration, a platform behavior). | A finding, with a two-part rating ("Medium; High if ...") |
| **Hardening** | A security-relevant gap without a demonstrated attack path (defense in depth, a safer default). | One line in the hardening appendix, no severity |
| *Not a vulnerability* | No attacker or no security impact: user-chosen actions behind a clear gesture, standard semantics (Markdown link text), compliance and declarations (privacy manifests, licences), performance with no attacker, code quality. | Left out; a one-line "Reviewed and rejected" entry if a reader would expect it |

Denial of service is a security impact when an attacker can trigger it: crashes, freezes and resource exhaustion from content another user or a model controls are vulnerabilities.

Every Vulnerability or Conditional vulnerability names its **security invariant**: one sentence the code should guarantee and doesn't. Example: "peer-supplied attachment metadata must not choose a write path outside the downloads folder".

## 2. Evidence and status

Record each dimension separately for every finding:

| Dimension | Values | Meaning |
|---|---|---|
| Weakness | Confirmed in source / Reproduced with target code / Not confirmed | The client-side flaw itself |
| Reachability | Confirmed end-to-end / Conditional on *named fact* / Not established | Whether the attacker in the stated position can deliver the input to a victim. Backend source at a recorded commit supports this; only a run against a non-production server or the owner's confirmation makes it end-to-end |
| Exposure | Base default / Optional-module default / Opt-in / Sample only / Build & release | Who has it, and the configuration needed |
| Runtime impact | Reproduced on target (name platform, device/simulator) / Proxy harness only / Inferred | What was actually observed |
| Persistence | Confirmed / Conditional / One-shot / N/A | Only when the finding claims it survives relaunch or re-delivery |

**Status:**
- **Verified**: every fact the stated severity relies on is established.
- **Conditional**: anything else. Name what would promote it ("backend accepts a 300-level object in user custom data and returns it in channel queries") and, if relevant, what would demote it.

Most client-SDK findings that depend on server behavior are Conditional until someone checks the server. That is fine, and better than an overclaim.

## 3. Severity rubric

Rate what is established, for the configuration stated in **Exposure**. Four questions:

1. **Who can trigger it?** Remote peer or model output (any user, any steerable content) > malicious backend, CDN or third-party host > on-path network attacker > another app or process on the device > someone holding the device > the integrator themselves.
2. **What do they get?**
   1. Credential theft or account takeover, code execution, arbitrary file write, cross-user data exposure.
   2. Persistent remote crash, phishing through trusted UI, actions the user didn't choose.
   3. One-shot crash, privacy leak (IP, read times, identifiers).
   4. Defense-in-depth gaps.
3. **How much interaction?** None (on receipt or render) > one natural tap (open a link, download a file, approve something that looks benign) > unusual steps.
4. **How many are exposed?** Base default in every integration > default inside an optional module > common opt-in > rare configuration or sample code only.

| Severity | Typical shape |
|---|---|
| **Critical** | All of these at once: remote peer or model output, no interaction, base default, and credential theft, code execution or mass data exposure. Example: the session token sent to any host a peer names, on render. Rare in client SDKs. If any part is conditional, it isn't Critical yet. |
| **High** | Remote peer or model output; default (base or optional module) or one natural tap; serious impact: arbitrary file write in the app container, tokens to attacker hosts after a tap, a persistent crash loop for every recipient, exfiltration of secrets the user types, actions the user didn't choose. |
| **Medium** | Serious impact behind meaningful preconditions (opt-in feature, malicious server, network attacker with a downgrade), or moderate impact that is remote and default: one-shot remote crash, data left for the next user on a shared device, secrets in release logs, privacy leaks that defeat a feature's promise. |
| **Low** | Local or physical attacker; remote attacks with minor impact or heavy preconditions; insecure sample code integrators are likely to copy. |
| **Info** | Observations, documentation gaps, good-practice recommendations. |

Rules:
- **Two-part ratings.** When a missing fact would change the rating, write the established rating first: "Medium; High if the backend re-delivers the payload". The summary table shows both.
- **Optional modules.** "High for apps that use the optional AI module" is a different statement from "High". Write the module.
- **When unsure between two levels,** pick the lower and say what would raise it.
- **Consistency.** Two auditors with the same evidence should land on the same rating. If the rationale needs a paragraph of special pleading, use the lower level.

## 4. Report template

Use this structure. Keep findings self-contained, so each can become a ticket.

```markdown
# <SDK name> security audit - <date>

**Revision:** <n> (<date>) / **Commit:** <full sha> on <branch>, <clean | dirty: ...> / **Auditor:** <who/what>
**Disclosure:** <from SECURITY.md, or "no policy found">. Contains unpatched issues: keep out of public trackers.

## Summary

<3 to 5 sentences:
- the overall posture;
- what is verified, and what is conditional on the backend or the integration;
- the most important issues;
- what to fix first.>

| ID | Severity | Title | Class | Exposure | Status |
|---|---|---|---|---|---|
| SEC-01 | Medium; High if <fact> | ... | Conditional vulnerability | Base default | Conditional |

Counts: <n by severity>; <n Verified, n Conditional>.

## Scope

- Commit, worktree state, submodules/LFS; resolution files; dependency revisions (first-party and security-relevant).
- Products/modules audited per distribution channel; excluded and why.
- Platforms supported vs. platforms where anything was run (device / simulator / desktop proxy).
- Source-only vs. built-artifact coverage.
- Server source used for reachability (repo + commit), or "none".

## Method

<Recon, distribution pass, threat model, review split, verification approach, evidence folder location.>

Catalog coverage: <n> items. <n> findings, <n> hardening, <n> clean, <n> rejected, <n> N/A, <n> not checked. Ledger: `<path to <report-name>-coverage.md>`. Not checked: <each ID with the reason, or "none">.

## Threat model

<Assets, entry points, content provenance, attacker positions: a short table.>

## Findings

### SEC-01 - <Title>

| | |
|---|---|
| Class / Severity / Status | Conditional vulnerability / Medium; High if <fact> / Conditional |
| Invariant | <one sentence> |
| Catalog | <IDs from checklist.md, e.g. AUTH-05, LOG-01> |
| Attacker | <position, and the capability needed: e.g. "channel member with pin permission"> |
| Exposure | <Base default / ...> - <configuration needed> |
| Affected | <products, versions, platforms> |
| Weakness | <Confirmed in source / Reproduced with target code (E-n)> |
| Reachability | <Confirmed end-to-end / Conditional on ...> |
| Runtime impact | <Reproduced on target (E-n) / Proxy harness only (E-n) / Inferred> |
| Persistence | <...> |
| CWE | <only when it genuinely fits> |

**Where:** `path/file.ext:line`, ...

**What happens.** <One paragraph: the flaw, in plain words.>

**Trace.**
1. <source: where attacker data enters, and who authors it>
2. <hop>
3. <sink: the dangerous operation>

**Evidence.** <E-n references to the evidence appendix; payload; or "code reading only">

**Impact.** <What an attacker gets, for whom, under the stated exposure.>

**Fix.** <Specific change; mention existing safe code to copy.> **Regression test:** <sketch with the real module.>

## Distribution and dependencies

| Component | Version / revision | Ships via | Disposition |
|---|---|---|---|
| <first-party dep> | <rev> | <SPM/...> | Audited (areas) / Excluded (why) |
| <vendored lib> | <version> | <target> | Advisories checked (<tool/db date>): <applicable? why> |

<Artifact-content observations: what ships that the source review didn't cover, or vice versa.>

## Evidence and platform coverage

| ID | Finding | What ran | Target or proxy | Platform / config | Result | Location |
|---|---|---|---|---|---|---|
| E-1 | SEC-01 | <real module test / copied code> | Target | iOS 26 Simulator, Release | SIGTRAP in ... | <path> |

<Platforms supported vs exercised; findings never exercised at runtime.>

## Hardening

<Security-relevant gaps without a demonstrated attack path, one line each with the fix.>

## Positive observations

<Security properties the code gets right; this helps the team keep them.>

## Reviewed and rejected

<Leads that looked risky but aren't, one line each with the reason.>

## Open questions

<Facts that would promote or demote conditional findings, each with the finding IDs it affects and who can answer it.>

## Revision history

<Revision, date, what changed and why (e.g. "SEC-15 withdrawn: the image loader caps bytes and pixels").>
```

## 5. Writing tips

- Lead with impact in plain words, then the call chain.
- State preconditions in the summary table, not only in the body.
- Quote only the lines that matter (<=10 per excerpt).
- Name the attacker's concrete payload ("an attachment titled `../../../Library/Preferences/x.plist`") rather than a category ("malicious input").
- Make fixes specific and minimal. When the codebase already handles the same problem correctly somewhere else, point to it.
- Never include working exploit chains against third parties, real user data, or live credentials found during the audit. Describe them, and redact them to type + location + fingerprint.
