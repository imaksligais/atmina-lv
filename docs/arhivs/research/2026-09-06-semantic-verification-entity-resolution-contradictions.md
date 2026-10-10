# Semantic verification, entity resolution, and political contradictions

Date: 2026-09-06

Status: research and architecture discussion, based on project files and the linked research. Recommendations are proposals, not implemented changes or changes to standing publication rules. No new model evaluation was run for this discussion.

## Original questions

### 1. How do I verify LLM-extracted claims semantically, at scale, without a human in every loop?

The hardest unsolved thing here. The DeepSeek experiment (2026-08-10) proved lint catches formal defects but not semantic ones — title fabrication, verb-strength upgrades ("apsvēra" → "pieprasīja"), RT-with-verbatim-quote misattribution. Today the answer is "Opus subagents + heavy orchestrator QA + grammar gate," which works but doesn't scale and depends on reviewer attention. Every guardrail in the repo catches *structure*; none catch *a claim that is plausible, well-formed, and subtly wrong about what the politician actually said*. Is there an architecture (NLI-based entailment checking against the source doc? a second adversarial model with a verify-only prompt? calibrated abstention?) that catches the semantic class without doubling cost?

### 2. Entity resolution in a highly inflected language with homonyms and substring bombs — is there something structurally better than my curated substring matcher, or is the curation the irreducible cost?

The matcher is the project's permanent wound: diacritic folding, inflected surnames, "Kolu"→"Kolumbija", namesakes, negative_patterns as operator-only fixes. It works because of accumulated manual disambiguation, not because the approach is sound. Would a smarter person say "yes, modern entity linking / a small fine-tuned model solves this," or "no — for 60 tracked politicians in a low-resource language, curated substring matching with human-reviewed collision logs is actually the right answer, stop feeling bad about it"? The answer changes whether I invest in ML or in better review tooling.

### 3. Rhetoric-vs-action contradiction detection has a ~1-in-2700 yield and embeddings provably can't find it (T9). Is the real contradiction signal even in my data model, or am I looking in the wrong place entirely?

The structural SQL pass + faction checks find vote-chain anomalies, but the *interesting* contradictions ("said X in March, voted against X in June") require aligning free-text stances with structured ballot records across topics — a semantic alignment problem the current schema isn't designed for. Should claims be normalized into a proposition ontology (actor, policy object, direction, strength) at extraction time so contradictions become a query instead of a hunt? Or is the low yield simply the honest base rate of politics and the system is already correctly calibrated?

Common thread: all three are versions of *"the formal layer is solved; the semantic layer is held together by operator judgment"* — and I'd want to know which of the three is actually automatable and which I should stop trying to automate.

### Follow-up question

Explain more: "contextual political discrepancy deserves to be called a contradiction." Save the analysis and the questions in an .md file, then explain more concisely and in human language.

## Main assessment

All three can be automated further, but they need different boundaries. Invest first in source-grounded verification, then in resolving individual name mentions, and only then in a narrow proposition model for rhetoric–vote comparisons.

| Problem | Worth automating | Judgment to retain |
|---|---|---|
| Claim fidelity | Evidence attribution, unsupported additions, lost qualifications, routing uncertain cases | Ambiguous speech, sarcasm, incomplete sources; sampled audits |
| Entity resolution | Inflection handling, mention boundaries, contextual disambiguation | Identity registry, exceptional aliases, genuinely ambiguous mentions |
| Contradictions | Linking commitments to specific measures, interpreting vote chains, eliminating invalid comparisons | Whether the surviving discrepancy supports a publishable contradiction |

The shared architectural change is to make the evidence and intermediate decisions explicit, rather than asking a reviewer to reconstruct them from polished prose.

## 1. Semantic verification

### What the project evidence establishes

The [August 14 experiment](2026-08-14-deepseek-claim-extractor-test.md) recorded 9 of 42 initial claims needing intervention. This mixes semantic and language defects; it is not a semantic error-rate estimate. The later [11-case comparison](../eval/claim-extractor-model-ab-2026-08-18.md) also exposes the opposite failure: excessive abstention can silently discard legitimate positions. A successful verifier must measure both.

### Proposed architecture

1. **Extract evidence alongside the claim.** Store exact source spans and offsets, document version/hash, publisher, attributed speaker, speech act, qualifications, and whether the passage is quotation, reported speech, or reposted material.
2. **Run cheap deterministic checks.** Confirm spans exist; preserve repost boundaries; flag names, titles, numbers, and dates introduced by the paraphrase. These flags identify additions requiring evidence, rather than declaring every addition false.
3. **Run a small verifier against evidence and attribution context.** Check speaker, policy object, negation, modality, conditions, numbers, and added assertions separately. Return `supported`, `unsupported`, or `insufficient_context`.
4. **Escalate uncertain cases to a stronger verifier.** Give it the source and candidate claim without the extractor's persuasive reasoning. Require it to identify the unsupported component and cite the relevant passage. Expand to the full document when the local evidence is insufficient.
5. **Auto-accept only calibrated categories; audit a random sample of accepted claims.** Route the remainder to review or leave them unextracted. Automatic internal acceptance would not override the project's separate publication approval rules.

Unsupported is not the same as false. "The politician demanded X" may lack support even when the document never explicitly contradicts it.

The premise for entailment must be **this speaker said this, under these qualifications**. Checking the isolated proposition "X should happen" against a document misses RT attribution and quoted accusations. Checking whether an accusation was accurately attributed is separate from checking whether the accusation is true.

### Models and cost

Small grounding models are a credible research direction. MiniCheck reported a 770M-parameter model reaching GPT-4-level accuracy on its benchmark at substantially lower inference cost. This supports trying a specialized verifier; it does not establish Latvian attribution or modality performance. [MiniCheck paper](https://aclanthology.org/2024.emnlp-main.499/)

Benchmark a small multilingual verifier and a stronger verification-only LLM on actual project errors before considering fine-tuning. An adversarial prompt is useful only if measured: a model rewarded for finding problems can invent objections. Different model families can still share mistakes.

The cost model is:

`additional cost = cheap verification + escalation fraction × strong verification + audits`

Illustration only: if cheap verification costs 5% of extraction and 10% of claims need a second pass costing as much as extraction, model overhead is 15%, before audits and retries. These are assumptions, not a forecast. Measure **cost per accepted, correct claim**, including reviewer time and discarded valid claims.

### Calibration and evaluation

Calibrate abstention from held-out labels, not a model's self-reported confidence. Conformal methods offer relevant tools under their calibration assumptions; they do not remove distribution shift or annotation requirements. [Conformal factuality research](https://arxiv.org/abs/2402.10978)

The evaluation needs:

- Real corrected claims with their original source context.
- Controlled mutations: swap speaker, upgrade the verb, remove a condition, invent a title.
- Naturally occurring valid claims, including difficult ones.
- Source documents where extraction returned nothing.

Keep related articles and synthetic variants together when splitting training and evaluation. The existing 11 cases are useful regression tests, but too small and familiar to justify unattended acceptance. Zero errors in roughly 3,000 independent, representative accepted cases supports an approximate 95% upper error bound of 0.1%. A small clean benchmark cannot substantiate that precision.

**Recommendation:** eliminate routine per-claim review gradually, using measured acceptance coverage and residual error. Avoid a universal, unqualified "verified" flag.

## 2. Entity resolution

### What is already solved and what remains structural

The [current matcher](../../src/matcher.py) is more sophisticated than plain substring matching. Its single-word boundary logic explicitly handles `Kolu → Kolumbija`.

The more consequential problem is document-wide negative-pattern vetoing. A document can mention both the politician and a namesake or organization. Rejecting the entire document discards valid evidence. The project changelog records this collateral loss.

### Proposed architecture

`mention span → candidate identities → contextual resolution → document aggregation`

- Locate each name occurrence with token boundaries.
- Generate candidates using curated aliases and Latvian morphology.
- Resolve each occurrence using full names, nearby titles, institutional affiliation, date, handles, and other mentions.
- Allow **another person** and **unresolved** as outcomes.
- Aggregate resolved mentions into document links.
- Determine whether someone is a speaker or merely a subject separately.

A 60-person registry still requires an open-world decision: most people appearing in the corpus are outside those 60. A classifier forced to choose among tracked politicians will manufacture confident namesake links.

Latvian morphology need not be maintained entirely through surname-specific code. Tēzaurs provides inflection generation and named-entity normalization, with a published computational morphology model. These are candidates to test against the collision suite; neither establishes identity by itself. [Morphology services](https://morpho-api.tezaurs.lv/), [Latvian morphology paper](https://aclanthology.org/2024.lrec-main.20/)

Preserve the original spelling. Use diacritic folding as a weaker candidate-generation route, with its provenance recorded, rather than collapsing distinct forms into one identity key.

### Investment decision

Invest in review tooling before a custom entity-linking model. Capture corrections as structured labels, for example:

> This occurrence of “Zīle” refers to Arvis, with this supporting context.

That label can improve local rules today and train a contextual resolver later. A document-wide exception is much less reusable.

The irreducible curation is identity knowledge: aliases, name changes, handles, namesakes, and time-dependent affiliations. Repeatedly repairing document-level substring side effects is avoidable engineering cost.

## 3. Rhetoric versus action

### Two qualifications to the question's premises

T9 in [CLAUDE.md](../../CLAUDE.md) documents the inadequacy of the existing embedding workflow and its filtering. It is not a general proof that embeddings cannot help retrieve related material. Similarity can generate candidates; it cannot establish incompatible positions. This assessment does not propose overriding T9's operational rule.

**One publishable case per 2,700 raw pairs is pipeline yield, not an estimate of politics' underlying contradiction rate.** Yield depends on candidate generation, duplicated vote chains, source coverage, ranking, and publication criteria. Without measuring missed contradictions, low yield cannot demonstrate correct calibration.

The [30 rejected candidates](../eval/party_funnel_da_verdicti_2026-08-21.md) show concrete causes: six were directionally consistent, six merely shared a topic, and the rest failed on vote-chain, abstention, or procedural context. These findings justify better candidate construction.

### The missing representation

Actor, policy object, direction, and strength are useful but insufficient.

| Statement representation | Legislative-action representation |
|---|---|
| Speaker and represented organization | Actual voter and contemporaneous faction |
| Specific policy object and affected population | Exact bill version, provision, or amendment |
| Proposed change, conditions, exceptions | What adopting the motion would change |
| Commitment type and time horizon | Procedural stage, alternatives, and vote chain |
| Supporting source spans | Supporting legislative text and provenance |

The crucial missing object is the **change proposed by the measure**.

"Supports lower taxes" plus "voted against a tax bill" is uninformative. Voting against a tax increase may be consistent. Voting against a package containing a tax reduction may reflect another provision. Even a final substantive vote does not establish opposition to every component.

Normalize legislative meaning once per measure/version, then reuse it across individual ballots. This is a better cost structure than repeatedly asking a model to interpret each politician–vote pair.

The [existing Saeima schema](../../src/saeima/schema.py) supplies bill identifiers, stages, amendment references, and votes. Extend it with an optional, evidence-backed interpretation layer. Schema inspection alone cannot establish that all legislative text needed to populate this layer is already available.

Start with one narrow policy area and explicit commitments. Produce potential commitment–action discrepancies only when object, scope, direction, chronology, and vote semantics are sufficiently resolved. Leave broad aspirations and ambiguous packages unnormalized.

Normalization makes candidate discovery queryable. It does not make the final contradiction judgment mechanical. Faction discipline may explain a substantive conflicting vote; it should not automatically erase the discrepancy.

At one genuine case per 2,700 candidates, a detector with perfect recall and a 1% false-positive rate produces roughly 27 false alarms per true case. This is an illustration using the reported yield as an assumed prevalence, not a measured prevalence estimate.

## 4. What does “deserves to be called a contradiction” mean?

The phrase was too vague. It means: **does the evidence justify telling readers that the person's action conflicts with the commitment they actually made?** It should be an explicit editorial standard, not a reviewer's instinct or permission to excuse a favored politician.

There are three separate questions:

1. **What happened?** The exact words, the exact vote, the dates, the measure, and the attribution.
2. **Do those things conflict?** Would the action defeat or oppose the same commitment, covering the same people, conditions, and period?
3. **How strongly can we describe the conflict?** An apparent mismatch, a documented reversal, a broken commitment, and deliberate deception are different claims requiring different evidence.

A changed position is not necessarily a logical contradiction: someone can support a policy in March and openly oppose it in June. That is a reversal. It may conflict with an earlier promise, but it does not prove that the person lied in March. The language used in publication should preserve those distinctions.

### Hypothetical examples

| Words and later action | What can fairly be concluded? |
|---|---|
| “I support better healthcare.” Later votes against a budget containing hospital funding and many unrelated measures. | An apparent mismatch worth investigating. The broad statement and package vote do not establish a contradiction by themselves. |
| “I will vote against increasing this tax during this term.” Later votes for a standalone measure increasing that same tax during that term. | Strong evidence of an action conflicting with an explicit commitment, after checking attribution and the measure's effect. |
| “I will support this subsidy if it has a funding source.” Later votes against an unfunded version. | The stated condition was not met. No conflict is established. |
| “I support this reform.” Later rejects one version and votes for an alternative delivering the same reform. | Different means of pursuing the same stated objective; inspect the actual alternatives before alleging conflict. |
| “I used to oppose this measure; new evidence changed my mind.” Later votes for it. | An acknowledged reversal. The explanation is relevant, but does not make the historical change disappear. |

All examples above are invented to explain the distinction, not allegations about actual politicians.

### Context is evidence, not a blanket excuse

An explanation can have different effects:

- **It removes the supposed conflict:** the promise was conditional and its condition was not met; the vote concerned a different measure; the actor was misidentified.
- **It explains a real conflict:** party discipline or a negotiated compromise led the person to act against an explicit commitment. The conflict may remain reportable alongside that explanation.
- **It remains an unverified explanation:** the politician says the bill did something different. Check the bill; do not accept the explanation merely because it was offered.

Neither “there must be some explanation” nor “they voted the other way, therefore they lied” is an adequate standard.

Separate confidence from importance. A small but clear reversal remains clear; a dramatic but poorly supported allegation remains poorly supported. Editorial prominence is another decision and should not determine whether a factual conflict exists.

### What the machine should prepare for the reviewer

For each surviving candidate, assemble the original passage, exact commitment and qualifications, later action and its documented effect, relevant vote chain and alternatives, any recorded explanation, and the precise reason the two appear incompatible. Mark missing evidence explicitly.

The reviewer then answers a bounded question: **does this comparison hold, and what is the narrowest accurate description?** The reviewer should not have to rediscover the whole story.

Use explicit outcome labels such as `different_scope`, `condition_not_met`, `procedural_vote`, `insufficient_evidence`, `acknowledged_reversal`, and `commitment_action_conflict` as proposed review categories. These are not new production schema fields or approved publication classifications.

## 5. Recommended order of investment

1. Build a shared evidence-and-attribution representation and a held-out semantic verification benchmark.
2. Move entity resolution to individual mentions, with reusable correction labels.
3. Run a small, action-centered contradiction pilot. Evaluate known positives and a sample outside its selected candidates, rather than rewarding it for producing more findings.

This moves operator judgment into reusable labels, explicit definitions, and targeted audits. Retain human approval for the public judgment that a contextual political discrepancy supports a contradiction claim, while making that decision much less laborious.

## Plain-language explanation

The computer can spot: “They promised X, then voted against something mentioning X.”

The harder question is whether it was really the same thing. Was the promise conditional? Did the vote concern the policy itself or just parliamentary procedure? Was it a large package with other provisions? Did the person openly change their position?

Sometimes checking those details makes the apparent contradiction disappear. Sometimes it confirms a real broken commitment. An explanation such as party pressure can explain a broken commitment without cancelling it.

Automate gathering and comparing the evidence. Keep a person responsible for choosing accurate public wording: “voted against this commitment,” “changed position,” or “the evidence is inconclusive.” None of those, by itself, proves dishonesty.
