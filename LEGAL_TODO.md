# Legal TODOs — placeholder tracking

**Status**: EULA `LICENSE.txt` is in force but contains the following
placeholder that must be resolved before any commercial enforcement.
Do not delete this file until all placeholders are filled.

## Outstanding placeholders

### TODO-1 — Legal Contact email

**Location**: `LICENSE.txt`, Section 1 (Definitions of "Legal Contact"),
plus references in Sections 3(c), 4 (last paragraph), 9 (LGPL/MPL
source request), 12 / 13(f) (notices).

**Current**: Defined as "the email address designated for legal notices
under this Agreement, currently set to the placeholder address listed
in this repository's README. Licensor will update the README with the
operative address before this Agreement is enforced against any
recipient."

**README state**: `README.md` currently has **no Legal Contact email**.

**Required action**: When ready, do **both** of the following in the
same commit:

1. Pick an email and put it on a `**Legal contact:**` line in this
   repository's `README.md` under the License section. Suggested
   options:
   - `sencha.s1d@gmail.com` (current personal — quickest, lowest cost)
   - `huligan.legal@gmail.com` (new dedicated gmail — recommended)
   - `legal@huligan.io` or similar (requires buying a domain ~$30/yr —
     most professional, supports `support@`, `abuse@`, etc.)
2. Leave `LICENSE.txt` Section 1 unchanged — the definition already
   delegates the operative address to README.

**Why this is okay to defer**: the EULA's "Legal Contact" definition
points at README, so updating the README alone propagates the email
throughout the EULA without re-versioning LICENSE.txt. If you later
want to lock the email into LICENSE.txt itself (more formal), you can
do that — but then you'd bump LICENSE.txt to v1.2.

---

### TODO-2 — Trademark registration (optional, not blocking)

**Status**: deferred per user decision (2026-05-14).
Section 11 of `LICENSE.txt` claims unregistered common-law trademark
rights for "Huligan", which is sufficient for many jurisdictions
without registration.

**If/when you decide to register**:
- RU (Rospatent): ~30,000 RUB, ~12 months, class 9 (software) + 42
  (SaaS).
- US (USPTO TEAS Plus): $250-350 per class, ~12 months.
- EU (EUIPO): €850-1050 per class, ~5 months. Covers all 27 EU
  member states.
- WIPO Madrid (international): requires base RU/US registration first.

After registration, update Section 11 of `LICENSE.txt`:
- Replace "unregistered common-law trademarks" with "registered
  trademarks of the Huligan Project (e.g., RU registration No. XXXXXX,
  EUIPO registration No. XXXXXX)".

---

### TODO-3 — Legal entity (optional, not blocking)

**Status**: deferred per user decision (2026-05-14).
LICENSE.txt v1.1 uses the deliberately vague "the Huligan Project" with
a definition that defers entity structure to "the natural person(s)
acting as Licensor of record at the time of dispute." This is enough
to be enforceable but is weaker than a named legal entity.

**If/when you register an ИП, ООО, LLC, Ltd., GmbH, etc.**:
- Update the opening paragraph of `LICENSE.txt` to name the entity:
  e.g., "between you ... and Huligan Project LLC, a Cyprus limited
  liability company (registration No. HE XXXXXX), trading as 'Huligan
  Project' ('Licensor')".
- Update Section 1 definition of "Licensor" accordingly.
- Bump LICENSE.txt to v1.2 (or higher).

---

## Versioning protocol

`LICENSE.txt` carries `Version 1.1 — Last updated YYYY-MM-DD` on the
first line. When making changes:

- **Editorial changes (typos, formatting, README pointers)**: bump
  only the date, keep version 1.1.
- **Substantive changes** (different governing law, different
  arbitration body, new restrictions, new survival, etc.): bump
  to 1.2 / 1.3 / etc., and add a one-line changelog entry below.
- Each downloader is bound by the version of `LICENSE.txt` that was
  live at download time (see opening preamble of LICENSE.txt).

## Changelog

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0 | 2026-05-14 | Initial | First public draft |
| 1.1 | 2026-05-14 | Editorial | 18-point review: Cyprus + ICC arbitration, OFAC/sanctions clause, ML carve-out, LGPL 60-day deadline, liability formula, force majeure, class action waiver, Patches definition, employee/contractor clarification, extended survival list |
