"""Template angle definitions for content diversity.

Each template has 10 distinct execution angles. An angle is a single-sentence
instruction to the LLM that changes HOW the template is executed — the evidence
type, perspective, emotional tone, or framing device — without changing the
template TYPE or its required structural sections.

An angle is randomly and exclusively sampled per run so that multiple posts
from the same template never repeat an approach within the same batch.

Usage:
    from src.config.template_angles import TEMPLATE_ANGLES, MAX_QUANTITY_PER_TEMPLATE
    import random

    angles = random.sample(TEMPLATE_ANGLES[template_id], quantity)
"""

from typing import Dict, List

# Maximum posts allowed per template per run — matches the length of each angle list.
# Enforced before generation so the batch never exhausts the unique-angle pool.
MAX_QUANTITY_PER_TEMPLATE = 10

TEMPLATE_ANGLES: Dict[int, List[str]] = {
    # -------------------------------------------------------------------------
    # Template 1: Problem-Recognition
    # Hook labels problem → validate frustration → reframe as opportunity →
    # example → CTA
    # -------------------------------------------------------------------------
    1: [
        "Open with a data point that quantifies exactly how widespread the problem is, then reframe the cost of inaction in concrete dollar or time terms.",
        "Open by naming the problem from the perspective of a skeptic who tried every conventional solution and still failed, validating their exhaustion before pivoting.",
        "Frame the problem as an industry-wide blind spot that even experienced practitioners overlook, establishing insider credibility before the reframe.",
        "Use a before/after contrast as the hook — the painful 'before' state described in visceral, specific detail — then pivot to the opportunity hidden inside it.",
        "Open with a counterintuitive claim: the problem most people are solving is actually a symptom; name the real root cause as the reframe.",
        "Ground the problem in a single hyper-specific scenario the target audience will recognise instantly — a day, a meeting, a metric — to create immediate identification.",
        "Apply a loss-aversion lens: quantify what the audience is silently losing each month by not solving this problem, then show the opportunity as stopping the bleed.",
        "Use a historical comparison — how this same problem played out in an adjacent industry a decade ago — to reframe it as a known, solvable pattern.",
        "Lead with social proof: describe the problem by aggregating what the audience's peers are privately complaining about, making them feel seen before the pivot.",
        "Take the aspirational angle: describe the transformed state first, then work backward to name the problem blocking most people from reaching it.",
    ],
    # -------------------------------------------------------------------------
    # Template 2: Statistic + Insight
    # Surprising stat → common misinterpretation → actual meaning →
    # real-world application → CTA
    # -------------------------------------------------------------------------
    2: [
        "Lead with a stat that contradicts a widely held optimistic belief in the industry, then explain the gap between what people want it to mean and what it actually means.",
        "Open with a stat the audience has probably seen before but consistently misreads — use the misinterpretation itself as the hook, then correct it with authority.",
        "Use a cost-framing stat (money lost, time wasted, opportunity missed) and explain why the conventional response to that number makes it worse, not better.",
        "Source the stat from an unexpected sector — behavioural economics, military logistics, healthcare — and draw a precise, non-obvious analogy to the client's industry.",
        "Open with two stats that appear to contradict each other, then resolve the tension to reveal the real insight hiding between them.",
        "Anchor to a trend-over-time stat (year-over-year shift) and explain why the direction of change matters more than the absolute number.",
        "Use a micro-level stat (per-person, per-day, per-transaction) instead of the macro aggregate to make the number feel immediate and personal.",
        "Lead with a stat about what high performers do differently, then explain the mechanism — why that behaviour produces the result — rather than just repeating the finding.",
        "Open with a stat that will surprise experts, not just beginners, to establish that even experienced practitioners have a knowledge gap worth closing.",
        "Frame the stat as the punchline to a mystery: open by describing a puzzling outcome, then reveal the data that explains it.",
    ],
    # -------------------------------------------------------------------------
    # Template 3: Against-the-Grain Contrarian
    # Contrarian headline → acknowledge conventional wisdom → where it breaks →
    # your method → caveat → CTA
    # -------------------------------------------------------------------------
    3: [
        "Choose a conventional wisdom that is almost universally repeated in the industry and dismantle it using a specific, falsifiable example from the client's own results.",
        "Open with the most confident, authoritative version of the conventional belief — steelman it fully — then show the precise edge case where it reliably fails.",
        "Frame the contrarian position through a cost lens: calculate what following the conventional advice actually costs practitioners over 12 months in concrete terms.",
        "Take the expert insider angle: the conventional wisdom works for beginners but actively harms advanced practitioners — explain exactly where the threshold is.",
        "Use historical evidence: show that the conventional wisdom was correct in a prior era, then trace the specific market shift that made it obsolete.",
        "Lead with a surprising admission — acknowledge one scenario where the conventional wisdom IS correct — then show the larger context in which it fails.",
        "Frame the contrarian take as a question the audience is too polite to ask out loud, then answer it directly and without hedging.",
        "Apply a first-principles lens: strip the conventional wisdom to its core assumption, show the assumption is false, and rebuild the correct conclusion from scratch.",
        "Use social proof in reverse: describe the high failure rate among people who follow the conventional wisdom correctly and perfectly, not those who do it wrong.",
        "Make the contrarian claim aspirational: the unconventional path is not just more effective — it is what separates a specific elite group the audience wants to join.",
    ],
    # -------------------------------------------------------------------------
    # Template 4: Here's What Changed (Evolution)
    # Old method context → trigger for change → new approach →
    # old vs new comparison → lesson → invitation
    # -------------------------------------------------------------------------
    4: [
        "Ground the old method in a specific year or market condition so the audience understands why it made sense then, before explaining the trigger that broke it.",
        "Frame the trigger for change as a near-miss or costly mistake — something that forced the pivot — rather than a planned strategic evolution.",
        "Use a data-driven comparison: show a specific metric that was flat or declining under the old approach and improved measurably after the change.",
        "Tell the evolution through the lens of what the client gave up — something that felt like a sacrifice at the time — to add authenticity to the new approach.",
        "Apply the beginner's perspective: explain why the old method looks correct on the surface, why most people still use it, and what experience now reveals.",
        "Frame the evolution as industry-wide, not just personal: describe the broader shift happening across the sector, then show how the client got ahead of it.",
        "Use a structured contrast in the text: explicitly compare 5 specific behaviours or outputs, old vs new, to make the change concrete and scannable.",
        "Open with the lesson first, then reconstruct the journey that produced it — inverted structure that makes the payoff clear before the story unfolds.",
        "Emphasise the emotional arc: the discomfort of abandoning a method that was working 'well enough' and the counterintuitive decision to change anyway.",
        "Apply a forward-looking lens: if the trigger for change was this, what will force the next evolution — and what should the audience be watching for?",
    ],
    # -------------------------------------------------------------------------
    # Template 5: Question Post (Engagement Magnet)
    # Specific surprising question → why asking → your take first →
    # invitation to comment
    # -------------------------------------------------------------------------
    5: [
        "Make the question one that reveals a hidden split in the audience — where experienced and inexperienced practitioners give opposite answers — then share which side you are on and why.",
        "Frame the question as something the audience debates privately but rarely says publicly, lowering the barrier to commenting by naming the unspoken conversation first.",
        "Use a data-led setup: reference a surprising finding or statistic, then turn it into a question that invites the audience to explain the 'why' behind it.",
        "Make the question an honest confession of uncertainty — something you genuinely do not have a settled answer on — to model intellectual humility and invite real dialogue.",
        "Frame the question as a prediction: ask the audience to forecast a specific outcome 12 months from now, share your own prediction with reasoning, and invite disagreement.",
        "Ground the question in a specific, named scenario the audience will recognise — a client type, a platform change, a common situation — to make it concrete, not abstract.",
        "Use a loss-aversion framing: ask what the audience would do differently if they knew a specific commonly ignored risk was real, sharing your own answer first.",
        "Make the question one that has changed significantly in the last 2-3 years — flag that explicitly — to create urgency and recency in the responses you invite.",
        "Pose a question that challenges a decision most of the audience has already made and committed to, making it genuinely risky to answer honestly and therefore more compelling.",
        "Ask the question from a beginner's perspective: frame it as something you wish someone had asked you years ago, surfacing the counterintuitive answer that only experience reveals.",
    ],
    # -------------------------------------------------------------------------
    # Template 6: Personal Story
    # Relatable scenario → crisis/realization → the feeling → lesson →
    # application → CTA
    # -------------------------------------------------------------------------
    6: [
        "Open the scenario with a specific sensory or situational detail that places the audience inside the moment — not a summary of it — before the crisis unfolds.",
        "Choose a scenario where the mistake was subtle and reasonable at the time, not an obvious blunder, so the audience recognises their own similar choices without shame.",
        "Frame the crisis as the moment a metric or external signal confirmed what was already being felt internally — the collision of intuition and data.",
        "Use a financial or time cost to make the realization concrete: quantify what the wrong approach was actually costing before the lesson landed.",
        "Tell the story from the perspective of the person hardest to convince — the internal sceptic — and let the realization come through their eyes.",
        "Make the feeling section the emotional core: spend more time on the specific experience of being wrong and uncertain than on the resolution, because that is what the audience shares.",
        "Apply a loss-aversion arc: the story is not about gaining something new — it is about realising what was being lost the entire time without noticing.",
        "Use a compressed timeline: show the same lesson playing out in three separate incidents over years, with the realization only landing on the third occurrence.",
        "Frame the application with an industry-specific lens: translate the personal lesson into a concrete, named behaviour change the audience can replicate tomorrow.",
        "End with a question embedded in the CTA that reveals the lesson is still unresolved — inviting the audience to share how they are navigating the same tension.",
    ],
    # -------------------------------------------------------------------------
    # Template 7: Myth-Busting
    # State myth → why it seems true → reality → why it matters →
    # evidence → what to do instead
    # -------------------------------------------------------------------------
    7: [
        "Choose a myth that is actively repeated by respected, well-intentioned experts — not just uninformed beginners — to establish that even trusted sources get this wrong.",
        "Lead with the emotional appeal of the myth: explain why it is psychologically satisfying or reassuring to believe, before showing the evidence against it.",
        "Use a controlled-comparison framing: describe two groups — those who followed the myth and those who did not — and show the measurable outcome difference.",
        "Source the evidence against the myth from the same type of authority that originally propagated it — research, industry bodies, data — to create an insider rebuttal.",
        "Apply a cost-framing lens: quantify what believers in the myth are concretely losing per quarter because they organised their behaviour around a false premise.",
        "Use historical evidence: show that the myth was factually true in a prior context, trace how conditions changed, and demonstrate it is now reliably false.",
        "Take the beginner's perspective: explain why the myth is the first thing people learn, why it makes intuitive sense at entry level, and precisely when experience exposes it.",
        "Frame the myth through a risk lens: following this myth does not merely leave value on the table — it creates a specific, named downside risk most practitioners are unaware of.",
        "Present the reality as a spectrum rather than a binary: the myth oversimplifies a nuanced truth, and 'what to do instead' is conditional on where the audience sits on that spectrum.",
        "Make the 'what to do instead' the core of the post — spend equal time on the alternative — so the audience leaves with a concrete behaviour change, not just a corrected belief.",
    ],
    # -------------------------------------------------------------------------
    # Template 8: Things I Got Wrong (Vulnerability)
    # Belief held → how long → the break → what's true instead →
    # behaviour change → implication for audience
    # -------------------------------------------------------------------------
    8: [
        "Choose a belief that was once a genuine competitive advantage — something that worked — so the admission is about growth past success, not correcting an obvious error.",
        "Quantify how long the wrong belief was held and what it concretely cost in that period: time, revenue, missed relationships, or delayed outcomes.",
        "Frame the break as coming from an unexpected source — a junior colleague, a client pushback, a throwaway comment — that landed harder than any formal critique.",
        "Make the 'what's true instead' section concrete and falsifiable: state it as a testable principle, not a vague reframe, so the audience can apply and verify it.",
        "Use a data-led break: the belief held until a specific metric or result made it impossible to rationalise further, and describe the reckoning that followed.",
        "Take the social proof angle: the behaviour change that followed the break produced a specific, named result that the audience will recognise as meaningful.",
        "Apply a loss-aversion lens: the implication for the audience is not just what they could gain — it is what they are already losing while they hold the equivalent belief.",
        "Make the vulnerability structural, not just emotional: show exactly how the wrong belief shaped specific decisions, systems, or advice given to others.",
        "Frame the implication as a question the audience should ask themselves this week — one concrete diagnostic that would reveal whether they hold the same belief.",
        "Use the historical comparison angle: this belief was the consensus in the industry 5 years ago, and what changed is not just personal — the entire field has quietly moved on.",
    ],
    # -------------------------------------------------------------------------
    # Template 9: Actionable How-To (Short)
    # Problem → 3-step process → result → CTA
    # -------------------------------------------------------------------------
    9: [
        "Frame each step with a time estimate (e.g., '15 minutes', 'one conversation', 'before your next meeting') to make the process feel immediately executable.",
        "Anchor the problem and result in a specific, named client type or scenario so the process feels tailored rather than generic.",
        "Lead each step with the mistake most people make at that stage before giving the correct action, turning the how-to into a corrective guide.",
        "Use a data-driven framing: open with the result metric first (e.g., 'This 3-step process cut our client's onboarding time by 40%') then reconstruct the steps backward.",
        "Write each step from the perspective of what to stop doing first — the subtraction that creates space for the correct behaviour — before stating the replacement action.",
        "Apply an expert-insider lens: label each step with the name practitioners in the field use for it, signalling that this is professional-grade process knowledge.",
        "Make Step 1 a diagnostic or audit rather than an action, so the audience can assess whether they actually need the remaining steps before committing.",
        "Frame the 3-step process as a weekly or monthly recurring rhythm rather than a one-time intervention, making it feel like a system rather than a tactic.",
        "Use a loss-aversion setup: describe what the problem costs per week if left unsolved, then present the 3 steps as the minimum viable intervention to stop the bleed.",
        "Embed a micro-decision into each step — one judgment call the practitioner must make — so the how-to respects the audience's intelligence rather than treating them as order-followers.",
    ],
    # -------------------------------------------------------------------------
    # Template 10: Comparison
    # Decision point → option A pros/cons → option B pros/cons →
    # when to choose which → nuance
    # -------------------------------------------------------------------------
    10: [
        "Open by naming the exact decision moment — a specific trigger or context — where the audience is forced to choose between the two options, grounding the comparison immediately.",
        "Use a cost-framing lens for both options: calculate the concrete cost (time, money, opportunity) of choosing each, not just the features or benefits.",
        "Apply the expert insider angle: describe which option beginners almost always choose and which experienced practitioners tend to prefer, then explain the experience gap.",
        "Use a conditional structure for the 'when to choose which' section: if X is true about your situation choose A; if Y is true choose B — with named, specific X and Y.",
        "Frame each option's cons as hidden costs that only emerge over time, not immediate drawbacks, to distinguish surface-level and depth-level comparison.",
        "Apply a risk-first lens: lead each option section with its failure mode — how it goes wrong — before describing how it works when it succeeds.",
        "Use social proof to differentiate: describe the type of operator, team, or business that thrives with each option, making the comparison audience-segmented rather than universal.",
        "Introduce a third factor — a prerequisite, a constraint, or an environmental condition — that makes one option clearly dominant when present and irrelevant otherwise.",
        "Apply a trend lens: one option is becoming more viable over time while the other is losing ground — explain the directional shift and its implications.",
        "Make the nuance section the core of the post: the point is not which option wins but why the binary framing itself is misleading, and what the audience should actually be optimising for.",
    ],
    # -------------------------------------------------------------------------
    # Template 11: What I Learned From... (Learning)
    # Quote trigger → why it hit → interpretation in your industry →
    # implication → question
    # -------------------------------------------------------------------------
    11: [
        "Choose a quote from an adjacent field — sports, military, architecture, medicine — and draw the industry translation with precision, naming exactly what maps and what does not.",
        "Use a quote that you initially dismissed or misunderstood — describe the first encounter and the wrong interpretation — then show what changed your reading of it.",
        "Apply a contrarian lens: use a quote that is widely cited in the industry but typically interpreted incorrectly, then offer the interpretation the originator likely intended.",
        "Frame the quote as the answer to a question you were actively trying to solve: reconstruct the problem you were wrestling with before the quote landed as a solution.",
        "Use a cost-framing interpretation: explain how not understanding this principle has a concrete, calculable cost for practitioners in the client's industry.",
        "Choose a quote from a historical figure and show how a specific recent development in the industry proves its continued relevance in a non-obvious way.",
        "Apply a risk lens to the implication: what the quote reveals is not just an opportunity to capture but a failure mode to avoid — name it specifically.",
        "Use the beginner's perspective: explain why this quote means nothing to someone new to the industry and exactly what experience is required before it becomes useful.",
        "Make the 'why it hit' section the emotional anchor: describe the specific moment in which the quote stopped being abstract and became personally urgent.",
        "Frame the question at the end as an invitation to share an equivalent principle from a different source — broadening the conversation rather than seeking validation.",
    ],
    # -------------------------------------------------------------------------
    # Template 12: Inside Look (Behind-the-Scenes)
    # Teaser → inside look → why we do it differently → vulnerability/limitation →
    # relevance to audience
    # -------------------------------------------------------------------------
    12: [
        "Use a process or system that looks inefficient or counterintuitive from the outside — lead with the teaser as a puzzle — then reveal the reasoning as the inside look.",
        "Apply the data-led angle: the inside look reveals a specific metric or outcome that the different approach produces, making the 'why we do it differently' falsifiable.",
        "Frame the vulnerability section as a real ongoing constraint — something not yet solved — rather than a past mistake, to make the transparency feel current and honest.",
        "Use an expert insider lens: describe the inside look as something industry veterans will recognise but rarely discuss publicly, establishing credibility through specificity.",
        "Make the relevance section a direct replication guide: explain precisely what the audience would need to change in their own operation to apply the same approach.",
        "Apply a cost-framing lens to the 'why we do it differently' section: quantify what the conventional approach was costing before the change and what changed afterward.",
        "Use a social proof angle for the vulnerability: name the specific type of client or situation where this approach fails, so the audience trusts the recommendation for cases where it works.",
        "Frame the inside look as a decision that was controversial internally — there was disagreement — and explain how it was resolved and what the dissenting view got right.",
        "Apply a trend lens: this behind-the-scenes approach is becoming more common among leading practitioners, and the audience is seeing it without knowing what they are looking at.",
        "Make the teaser a question that the audience has wondered about but assumed they could not know the answer to, then answer it directly and completely.",
    ],
    # -------------------------------------------------------------------------
    # Template 13: Future-Thinking (Prediction)
    # Observed trend → extrapolation → why it matters → optional contrarian →
    # what to do now
    # -------------------------------------------------------------------------
    13: [
        "Anchor the observed trend in a specific, recent data point or event — not a vague directional feeling — to give the extrapolation a falsifiable foundation.",
        "Apply a cross-industry lens: the trend is already fully played out in an adjacent sector, and the client's industry is 3-5 years behind — use that as the evidence base.",
        "Use a loss-aversion frame: the prediction is not primarily about what early movers will gain — it is about what late movers will lose, and when the window closes.",
        "Frame the extrapolation as a second-order effect: the first-order change is visible and already discussed, but the downstream consequence that matters is under-analysed.",
        "Apply the contrarian section as the core of the post: steelman the case that the trend will not materialise, then show exactly why the evidence still points toward it.",
        "Use a historical parallel: find a past moment where the same type of trend signal appeared, trace what happened next, and show why the current situation rhymes with it.",
        "Make the 'what to do now' section a decision tree: if the prediction is correct do X; if it stalls do Y — giving the audience a robust rather than brittle response.",
        "Apply an insider credibility lens: the trend is visible in client behaviour, hiring patterns, or internal conversations before it shows up in published reports — describe those leading indicators.",
        "Frame the prediction around a specific time horizon (18 months, 3 years) and explain exactly what observable marker would confirm or refute it at that point.",
        "Use a beginner vs expert framing: the trend looks like noise to most observers right now, but experienced practitioners are already repositioning around it — explain what they are seeing.",
    ],
    # -------------------------------------------------------------------------
    # Template 14: Reader Question Response (Q&A)
    # Reader question → direct answer → nuanced explanation → broader principle →
    # invitation
    # -------------------------------------------------------------------------
    14: [
        "Choose a question that sounds simple on the surface but contains a hidden assumption — name the assumption, correct it, then answer the question the reader should have asked.",
        "Apply a data-led framing: the direct answer is backed by a specific piece of evidence or outcome, not just experience or opinion, making it verifiable.",
        "Use the expert insider angle: answer the question the way an experienced practitioner actually would, including the caveats and conditions that beginner answers omit.",
        "Frame the nuanced explanation as a spectrum: the direct answer is correct for a specific set of conditions, and spell out exactly what conditions change the answer.",
        "Apply a cost-framing lens: the broader principle is that ignoring this question — or acting on the wrong answer — has a specific, calculable cost most people do not account for.",
        "Use a contrarian direct answer: answer in a way that contradicts what most people in the industry would say, then use the nuanced explanation to justify the deviation.",
        "Make the broader principle the payoff: the specific question is the entry point, but the principle it reveals applies to a wider class of problems the audience faces regularly.",
        "Frame the invitation as a follow-up question that logically flows from the answer — not a generic 'what do you think' — to continue a specific conversation thread.",
        "Apply a beginner's perspective: answer the question assuming no prior knowledge, then layer in the nuance that separates the beginner's correct answer from the expert's correct answer.",
        "Use a social proof framing: this question came up repeatedly across multiple clients or situations — aggregate that pattern as the evidence base for the broader principle.",
    ],
    # -------------------------------------------------------------------------
    # Template 15: Milestone/Celebration
    # Specific achievement → what it took → lesson → gratitude → invitation
    # -------------------------------------------------------------------------
    15: [
        "Lead the 'what it took' section with the least glamorous operational reality — the boring, repeated work — before any dramatic moment or turning point.",
        "Use a data-led milestone: the achievement is defined by a specific, named metric rather than a round number or vanity milestone, making it feel earned rather than arbitrary.",
        "Apply a cost-framing lens to 'what it took': quantify what was given up or sacrificed — opportunities, comfort, revenue in the short term — to reach the milestone.",
        "Frame the lesson as something the achievement disproved: a belief held going in that turned out to be wrong, with the milestone as the evidence that corrected it.",
        "Use a loss-aversion angle: the lesson is not primarily about what the achievement unlocked — it is about what would have been permanently missed without a specific early decision.",
        "Apply an insider credibility lens: the 'what it took' section names a specific, non-obvious operational challenge that only people who have attempted this would recognise.",
        "Make the gratitude section specific and named: credit particular people, decisions, or resources by category to make the acknowledgment concrete rather than generic.",
        "Frame the invitation as a question about what the audience is building toward — not what they think of the milestone — shifting focus from celebration to shared aspiration.",
        "Apply a trend lens: this achievement would have been significantly harder or easier 3 years ago — explain what changed in the environment that made this the right moment.",
        "Use a beginner's perspective for the lesson: state what you would tell yourself at the very start of this journey, knowing what the milestone required, as the core takeaway.",
    ],
}
