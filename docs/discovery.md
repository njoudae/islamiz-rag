# Discovery and extraction contract

## Default hackathon source scope

The competition collection is `OFFICIAL_HACKATHON_REFERENCE`, backed by the Dorar Fiqh Encyclopedia at `https://dorar.net/feqhia`. The source is an encyclopedia, not a single-author fatwa site. Its native hierarchy is preserved:

`كتاب → باب → فصل → مبحث → مطلب`

Pages may also expose question/answer material, source references, evidence, named scholars and named madhhabs. Only explicitly present metadata is populated. Missing metadata remains null.

## Page structures sampled

1. Dorar entry 1444: hierarchy, references, and one explicit Q/A pair.
2. Dorar entry 1453: four explicitly named madhhabs, one explicitly named scholar, references, and one Q/A pair.
3. Dorar entry 1455: two explicitly named madhhabs, three explicitly named scholars, references, and two Q/A pairs.

The adapter never synthesizes a missing question, position, authority, madhhab, scholar, book, page, category, or citation. The cleaned original order is preserved.

## Deterministic extraction

- Numeric external ID from the canonical Dorar URL
- Canonical/source URL, source collection, authority, language, and source type
- Title and native hierarchy (book/category/subcategory/topic where present)
- Explicit question/answer pairs
- Explicit evidence, references, scholars, and madhhabs
- Original reference metadata, scrape timestamp, and SHA-256 content hash

Low-confidence or empty entries fail validation and are logged; no generative model repairs source text or fills metadata.

## Source separation

- `OFFICIAL_HACKATHON_REFERENCE`: default, approved Dorar collection.
- `BINBAZ_REFERENCE`: preserved legacy adapter, isolated and not part of default retrieval.
- `FUTURE_REFERENCE`: reserved for future separately indexed approved collections.

Retrieval always filters by collection. Different authorities are never flattened into a synthetic consensus. Genuine differences return `CONFLICTING_EVIDENCE` or are presented separately only when the source itself supports that presentation.

## Legacy Ibn Baz adapter

Canonical `https://binbaz.org.sa/fatwas/{numeric_id}/{slug}` pages remain supported by `IbnBazSourceAdapter`. Category pages are discovery inputs only. This adapter is retained for architecture continuity, not used as a fallback in the hackathon mode.

## Visual system

The supplied mobile reference contributes composition—not branding: stacked rounded panels, a dark anchoring cap, bright bodies, compact segmented controls, floating actions, and generous spacing. Daleel uses warm white, mint and saturated teal, charcoal green, and a restrained peach accent. The animated voice orb is the signature component. Arabic is the default RTL direction and desktop expands to a centered two-column workspace.

## Risks and controls

- Markup drift: cached fixtures, selector fallbacks, and parser regression tests.
- Source/terms constraints: no access-control bypass; controlled official-page fixtures, robots-aware crawling, configurable user agent, delay, cache, and resumable stages.
- Arabic normalization loss: normalization is retrieval-only; original cleaned text is immutable.
- False confidence: multi-signal evidence gate and invariant that no answer exists without a valid canonical source.
- Nuanced/personal cases: one grounded clarification or escalation; never unsupported analogical reasoning.
- Provider availability: replaceable interfaces and deterministic mocks.
- Contact accuracy: verified-only contacts from configuration/database; no seeded phone number.
