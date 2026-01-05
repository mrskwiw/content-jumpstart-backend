"""Story Mining Tool - Extract Customer Success Stories

Interactive tool that extracts customer success stories and case study
material through guided conversation and Claude-powered analysis.

Price: $500
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from ..models.story_mining_models import (
    Challenge,
    CustomerBackground,
    DecisionProcess,
    FuturePlans,
    Implementation,
    Results,
    StoryMiningAnalysis,
    SuccessStory,
    Testimonials,
)
from ..utils.anthropic_client import get_default_client
from .base import ResearchTool


class StoryMiner(ResearchTool):
    """Interactive customer story extraction"""

    @property
    def tool_name(self) -> str:
        return "story_mining"

    @property
    def price(self) -> int:
        return 500

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate required inputs"""
        required = ["business_description", "customer_context"]

        for field in required:
            if field not in inputs:
                raise ValueError(f"Missing required input: {field}")

        # Validate description length
        if len(inputs["business_description"]) < 50:
            raise ValueError("business_description too short (minimum 50 characters)")

        if len(inputs["customer_context"]) < 30:
            raise ValueError(
                "customer_context too short (minimum 30 characters). Provide basic customer info."
            )

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> StoryMiningAnalysis:
        """Execute interactive story mining"""
        business_description = inputs["business_description"]
        business_name = inputs.get("business_name", "Client")
        customer_context = inputs["customer_context"]
        interview_notes = inputs.get("interview_notes", "")

        client = get_default_client()

        print("[Story Mining] Starting customer story extraction...")
        print("[1/7] Gathering customer background...")

        # Step 1: Customer Background
        customer_background = self._gather_customer_background(
            client, business_description, customer_context, interview_notes
        )

        print("[2/7] Exploring the challenge...")

        # Step 2: Challenge
        challenge = self._gather_challenge(
            client, business_description, customer_background, interview_notes
        )

        print("[3/7] Understanding the decision process...")

        # Step 3: Decision Process
        decision_process = self._gather_decision_process(
            client, business_description, customer_background, challenge, interview_notes
        )

        print("[4/7] Mapping the implementation journey...")

        # Step 4: Implementation
        implementation = self._gather_implementation(
            client, customer_background, challenge, decision_process, interview_notes
        )

        print("[5/7] Documenting results and outcomes...")

        # Step 5: Results
        results = self._gather_results(
            client, customer_background, challenge, implementation, interview_notes
        )

        print("[6/7] Extracting testimonials and quotes...")

        # Step 6: Testimonials
        testimonials = self._gather_testimonials(
            client, customer_background, challenge, results, interview_notes
        )

        print("[7/7] Capturing future plans...")

        # Step 7: Future Plans
        future_plans = self._gather_future_plans(
            client, customer_background, results, interview_notes
        )

        print("[Synthesis] Synthesizing story insights...")

        # Synthesis
        (
            one_sentence_summary,
            key_takeaways,
            use_cases,
        ) = self._synthesize_story(
            client,
            customer_background,
            challenge,
            decision_process,
            implementation,
            results,
            testimonials,
        )

        # Build complete story
        story = SuccessStory(
            story_title=f"{customer_background.customer_name or 'Customer'} Success Story",
            business_name=business_name,
            customer_background=customer_background,
            challenge=challenge,
            decision_process=decision_process,
            implementation=implementation,
            results=results,
            testimonials=testimonials,
            future_plans=future_plans,
            one_sentence_summary=one_sentence_summary,
            key_takeaways=key_takeaways,
            use_cases=use_cases,
        )

        # Generate content recommendations
        content_recommendations = self._generate_content_recommendations(client, story)

        # Generate social proof snippets
        social_proof_snippets = self._generate_social_proof(client, story)

        # Generate case study outline
        case_study_outline = self._generate_case_study_outline(client, story)

        # Create analysis
        analysis = StoryMiningAnalysis(
            story=story,
            interview_notes=interview_notes,
            content_recommendations=content_recommendations,
            social_proof_snippets=social_proof_snippets,
            case_study_outline=case_study_outline,
        )

        return analysis

    def _gather_customer_background(
        self, client: Any, business_description: str, customer_context: str, notes: str
    ) -> CustomerBackground:
        """Gather customer background"""
        prompt = f"""You are conducting a story mining interview. Based on this information, determine the customer's background.

Business: {business_description}
Customer Context: {customer_context}
{f'Additional Notes: {notes}' if notes else ''}

Extract customer background:
1. Customer/company name (if mentioned)
2. Industry vertical
3. Company size (if known)
4. Customer's role/title
5. Starting situation (before using solution)
6. Key responsibilities (3-5 items)

Return JSON with:
- customer_name: string (or null)
- industry: string
- company_size: string (or null)
- role_title: string
- starting_situation: string
- key_responsibilities: array of strings"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2000
        )

        data = self._extract_json_from_response(response)

        return CustomerBackground(
            customer_name=data.get("customer_name"),
            industry=data.get("industry"),
            company_size=data.get("company_size"),
            role_title=data.get("role_title"),
            starting_situation=data.get("starting_situation"),
            key_responsibilities=data.get("key_responsibilities", []),
        )

    def _gather_challenge(
        self,
        client: Any,
        business_description: str,
        customer_background: CustomerBackground,
        notes: str,
    ) -> Challenge:
        """Gather challenge details"""
        prompt = f"""Continue the story mining interview. Explore the customer's challenge.

Business: {business_description}
Customer: {customer_background.customer_name or 'Customer'} ({customer_background.role_title})
Starting Situation: {customer_background.starting_situation}

Extract challenge details:
1. Problem description (what was the main problem)
2. Impact on business (how it affected them)
3. Urgency level (why urgent/important)
4. Failed attempts (what they tried before)
5. Pain points (specific frustrations)
6. Cost of inaction (what if not solved)

Return JSON with:
- problem_description: string
- impact_on_business: string
- urgency_level: string
- failed_attempts: array of strings
- pain_points: array of strings
- cost_of_inaction: string"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2500
        )

        data = self._extract_json_from_response(response)

        return Challenge(
            problem_description=data.get("problem_description", ""),
            impact_on_business=data.get("impact_on_business"),
            urgency_level=data.get("urgency_level"),
            failed_attempts=data.get("failed_attempts", []),
            pain_points=data.get("pain_points", []),
            cost_of_inaction=data.get("cost_of_inaction"),
        )

    def _gather_decision_process(
        self,
        client: Any,
        business_description: str,
        customer_background: CustomerBackground,
        challenge: Challenge,
        notes: str,
    ) -> DecisionProcess:
        """Gather decision process"""
        prompt = f"""Continue the story mining interview. Understand the decision process.

Business: {business_description}
Customer: {customer_background.customer_name or 'Customer'}
Problem: {challenge.problem_description}

Extract decision process:
1. Why chose this solution (key reasons)
2. Alternatives considered (3-5 other options)
3. Key decision factors (what made them choose)
4. Decision timeline (how long to decide)
5. Stakeholders involved (who decided)
6. Concerns overcome (objections addressed)

Return JSON with:
- why_chose_solution: string
- alternatives_considered: array of strings
- key_decision_factors: array of strings
- decision_timeline: string
- stakeholders_involved: array of strings
- concerns_overcome: array of strings"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2500
        )

        data = self._extract_json_from_response(response)

        return DecisionProcess(
            why_chose_solution=data.get("why_chose_solution", ""),
            alternatives_considered=data.get("alternatives_considered", []),
            key_decision_factors=data.get("key_decision_factors", []),
            decision_timeline=data.get("decision_timeline"),
            stakeholders_involved=data.get("stakeholders_involved", []),
            concerns_overcome=data.get("concerns_overcome", []),
        )

    def _gather_implementation(
        self,
        client: Any,
        customer_background: CustomerBackground,
        challenge: Challenge,
        decision_process: DecisionProcess,
        notes: str,
    ) -> Implementation:
        """Gather implementation details"""
        prompt = f"""Continue the story mining interview. Map the implementation journey.

Customer: {customer_background.customer_name or 'Customer'}
Challenge: {challenge.problem_description}

Extract implementation journey:
1. Getting started (initial steps)
2. Implementation timeline (how long)
3. Key milestones (3-5 milestones)
4. Obstacles overcome (challenges during implementation)
5. Surprises/discoveries (unexpected learnings)
6. Support needed (what help was required)

Return JSON with:
- getting_started: string
- implementation_timeline: string
- key_milestones: array of strings
- obstacles_overcome: array of strings
- surprises_discoveries: array of strings
- support_needed: string"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2500
        )

        data = self._extract_json_from_response(response)

        return Implementation(
            getting_started=data.get("getting_started"),
            implementation_timeline=data.get("implementation_timeline"),
            key_milestones=data.get("key_milestones", []),
            obstacles_overcome=data.get("obstacles_overcome", []),
            surprises_discoveries=data.get("surprises_discoveries", []),
            support_needed=data.get("support_needed"),
        )

    def _gather_results(
        self,
        client: Any,
        customer_background: CustomerBackground,
        challenge: Challenge,
        implementation: Implementation,
        notes: str,
    ) -> Results:
        """Gather results and outcomes"""
        prompt = f"""Continue the story mining interview. Document results achieved.

Customer: {customer_background.customer_name or 'Customer'}
Challenge: {challenge.problem_description}
Timeline: {implementation.implementation_timeline}

Extract results:
1. Quantitative results (with numbers/percentages)
2. Qualitative improvements (quality changes)
3. ROI metrics (cost savings, revenue)
4. Time savings (efficiency gains)
5. Before vs after comparison
6. Unexpected benefits (bonus outcomes)

Return JSON with:
- quantitative_results: array of strings with numbers
- qualitative_improvements: array of strings
- roi_metrics: string
- time_savings: string
- before_after_comparison: string
- unexpected_benefits: array of strings"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2500
        )

        data = self._extract_json_from_response(response)

        return Results(
            quantitative_results=data.get("quantitative_results", []),
            qualitative_improvements=data.get("qualitative_improvements", []),
            roi_metrics=data.get("roi_metrics"),
            time_savings=data.get("time_savings"),
            before_after_comparison=data.get("before_after_comparison"),
            unexpected_benefits=data.get("unexpected_benefits", []),
        )

    def _gather_testimonials(
        self,
        client: Any,
        customer_background: CustomerBackground,
        challenge: Challenge,
        results: Results,
        notes: str,
    ) -> Testimonials:
        """Extract testimonials and quotes"""
        prompt = f"""Continue the story mining interview. Extract powerful testimonials.

Customer: {customer_background.customer_name or 'Customer'} ({customer_background.role_title})
Challenge: {challenge.problem_description}
Results: {', '.join(results.quantitative_results[:3])}

Create testimonials:
1. Headline quote (powerful 1-2 sentence quote)
2. Detailed quotes (3-5 longer testimonial quotes)
3. Specific wins (customer's words about wins)
4. Would recommend (why recommend to others)
5. Advice for others (what to know)

Return JSON with:
- headline_quote: string
- detailed_quotes: array of strings
- specific_wins: array of strings
- would_recommend: string
- advice_for_others: string

Make quotes sound authentic and specific."""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2500
        )

        data = self._extract_json_from_response(response)

        return Testimonials(
            headline_quote=data.get("headline_quote"),
            detailed_quotes=data.get("detailed_quotes", []),
            specific_wins=data.get("specific_wins", []),
            would_recommend=data.get("would_recommend"),
            advice_for_others=data.get("advice_for_others"),
        )

    def _gather_future_plans(
        self,
        client: Any,
        customer_background: CustomerBackground,
        results: Results,
        notes: str,
    ) -> FuturePlans:
        """Gather future plans"""
        prompt = f"""Continue the story mining interview. Explore future plans.

Customer: {customer_background.customer_name or 'Customer'}
Current Results: {', '.join(results.quantitative_results[:2])}

Extract future plans:
1. Ongoing success (how success continues)
2. Next goals (what's next)
3. Long-term vision (future plans)
4. Expansion plans (how expand usage)

Return JSON with:
- ongoing_success: string
- next_goals: array of strings
- long_term_vision: string
- expansion_plans: string"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=1500
        )

        data = self._extract_json_from_response(response)

        return FuturePlans(
            ongoing_success=data.get("ongoing_success"),
            next_goals=data.get("next_goals", []),
            long_term_vision=data.get("long_term_vision"),
            expansion_plans=data.get("expansion_plans"),
        )

    def _synthesize_story(
        self,
        client: Any,
        customer_background: CustomerBackground,
        challenge: Challenge,
        decision_process: DecisionProcess,
        implementation: Implementation,
        results: Results,
        testimonials: Testimonials,
    ) -> tuple[str, List[str], List[str]]:
        """Synthesize story insights"""
        prompt = f"""Synthesize this customer success story.

Customer: {customer_background.customer_name or 'Customer'} ({customer_background.industry})
Challenge: {challenge.problem_description}
Results: {', '.join(results.quantitative_results[:3])}
Quote: {testimonials.headline_quote}

Provide:
1. One-sentence story summary
2. Key takeaways (3-5 lessons from story)
3. Use cases (3-5 use cases this demonstrates)

Return JSON with:
- one_sentence_summary: string
- key_takeaways: array of strings
- use_cases: array of strings"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2000
        )

        data = self._extract_json_from_response(response)

        return (
            data.get("one_sentence_summary", ""),
            data.get("key_takeaways", []),
            data.get("use_cases", []),
        )

    def _generate_content_recommendations(
        self, client: Any, story: SuccessStory
    ) -> List[str]:
        """Generate content recommendations"""
        prompt = f"""Based on this success story, recommend 5-7 pieces of content to create.

Story: {story.one_sentence_summary}
Results: {', '.join(story.results.quantitative_results[:3])}
Use Cases: {', '.join(story.use_cases[:3])}

Recommend specific content like:
- Blog post: [specific angle]
- Case study: [specific focus]
- Social posts: [specific messages]
- Video: [specific story]
- Webinar: [specific topic]

Return JSON array of strings."""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=1500
        )

        return self._extract_json_from_response(response)

    def _generate_social_proof(self, client: Any, story: SuccessStory) -> List[str]:
        """Generate social proof snippets"""
        prompt = f"""Based on this success story, create 5-7 short social proof snippets.

Headline Quote: {story.testimonials.headline_quote}
Results: {', '.join(story.results.quantitative_results[:3])}
Customer: {story.customer_background.customer_name or 'Customer'}

Create snippets like:
- Tweet-length testimonials
- LinkedIn post quotes
- Website testimonials
- Email signature quotes

Each snippet should be 1-2 sentences, punchy, with results.

Return JSON array of strings."""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=1500
        )

        return self._extract_json_from_response(response)

    def _generate_case_study_outline(self, client: Any, story: SuccessStory) -> str:
        """Generate case study outline"""
        prompt = f"""Create a case study outline from this success story.

Customer: {story.customer_background.customer_name or 'Customer'} ({story.customer_background.industry})
Challenge: {story.challenge.problem_description}
Solution: {story.decision_process.why_chose_solution}
Results: {', '.join(story.results.quantitative_results[:3])}

Create a structured case study outline with:
1. Title
2. Executive summary
3. Challenge section
4. Solution section
5. Results section
6. Conclusion

Return as markdown text (not JSON)."""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2000
        )

        return response.strip()

    def generate_reports(self, analysis: StoryMiningAnalysis) -> Dict[str, Path]:
        """Generate output files"""
        outputs = {}

        # JSON format
        json_path = self.output_dir / "success_story.json"
        json_path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
        outputs["json"] = json_path

        # Markdown format
        markdown_path = self.output_dir / "success_story.md"
        markdown_content = self.format_output_markdown(analysis)
        markdown_path.write_text(markdown_content, encoding="utf-8")
        outputs["markdown"] = markdown_path

        # Case study format
        case_study_path = self.output_dir / "case_study.md"
        case_study_path.write_text(
            analysis.case_study_outline or "Case study outline not generated",
            encoding="utf-8",
        )
        outputs["case_study"] = case_study_path

        # Social proof snippets
        snippets_path = self.output_dir / "social_proof_snippets.txt"
        snippets_content = "\n\n".join(
            [f"{i}. {snippet}" for i, snippet in enumerate(analysis.social_proof_snippets, 1)]
        )
        snippets_path.write_text(snippets_content, encoding="utf-8")
        outputs["snippets"] = snippets_path

        return outputs

    def format_output_markdown(self, analysis: StoryMiningAnalysis) -> str:
        """Format as markdown report"""
        story = analysis.story

        md = f"""# Success Story: {story.story_title}

**Created:** {story.created_date}
**Business:** {story.business_name or 'Not specified'}

---

## Executive Summary

{story.one_sentence_summary}

---

## Customer Background

**Customer:** {story.customer_background.customer_name or 'Anonymous'}
**Industry:** {story.customer_background.industry or 'Not specified'}
**Role:** {story.customer_background.role_title or 'Not specified'}
**Company Size:** {story.customer_background.company_size or 'Not specified'}

**Starting Situation:**
{story.customer_background.starting_situation or 'Not specified'}

**Key Responsibilities:**
{self._format_list(story.customer_background.key_responsibilities)}

---

## The Challenge

**Problem:**
{story.challenge.problem_description}

**Impact on Business:**
{story.challenge.impact_on_business or 'Not specified'}

**Urgency:**
{story.challenge.urgency_level or 'Not specified'}

**Pain Points:**
{self._format_list(story.challenge.pain_points)}

**Previous Attempts:**
{self._format_list(story.challenge.failed_attempts)}

**Cost of Inaction:**
{story.challenge.cost_of_inaction or 'Not specified'}

---

## Decision Process

**Why They Chose This Solution:**
{story.decision_process.why_chose_solution}

**Alternatives Considered:**
{self._format_list(story.decision_process.alternatives_considered)}

**Key Decision Factors:**
{self._format_list(story.decision_process.key_decision_factors)}

**Timeline:** {story.decision_process.decision_timeline or 'Not specified'}

**Stakeholders:** {', '.join(story.decision_process.stakeholders_involved) or 'Not specified'}

**Concerns Overcome:**
{self._format_list(story.decision_process.concerns_overcome)}

---

## Implementation Journey

**Getting Started:**
{story.implementation.getting_started or 'Not specified'}

**Timeline:** {story.implementation.implementation_timeline or 'Not specified'}

**Key Milestones:**
{self._format_list(story.implementation.key_milestones)}

**Obstacles Overcome:**
{self._format_list(story.implementation.obstacles_overcome)}

**Surprises & Discoveries:**
{self._format_list(story.implementation.surprises_discoveries)}

**Support Needed:**
{story.implementation.support_needed or 'Not specified'}

---

## Results Achieved

### Quantitative Results
{self._format_list(story.results.quantitative_results)}

### Qualitative Improvements
{self._format_list(story.results.qualitative_improvements)}

**ROI:** {story.results.roi_metrics or 'Not specified'}

**Time Savings:** {story.results.time_savings or 'Not specified'}

**Before vs After:**
{story.results.before_after_comparison or 'Not specified'}

**Unexpected Benefits:**
{self._format_list(story.results.unexpected_benefits)}

---

## Customer Testimonials

### Headline Quote

> {story.testimonials.headline_quote or 'No quote provided'}

### Detailed Quotes

{self._format_list(story.testimonials.detailed_quotes, quote=True)}

### Specific Wins (in customer's words)

{self._format_list(story.testimonials.specific_wins)}

**Would They Recommend?**
{story.testimonials.would_recommend or 'Not specified'}

**Advice for Others:**
{story.testimonials.advice_for_others or 'Not specified'}

---

## Future Plans

**Ongoing Success:**
{story.future_plans.ongoing_success or 'Not specified'}

**Next Goals:**
{self._format_list(story.future_plans.next_goals)}

**Long-Term Vision:**
{story.future_plans.long_term_vision or 'Not specified'}

**Expansion Plans:**
{story.future_plans.expansion_plans or 'Not specified'}

---

## Key Takeaways

{self._format_list(story.key_takeaways, numbered=True)}

---

## Use Cases Demonstrated

{self._format_list(story.use_cases)}

---

## Content Recommendations

{self._format_list(analysis.content_recommendations, numbered=True)}

---

*Story Mining Interview - ${self.price}*
"""

        return md

    def _format_list(
        self, items: List[str], numbered: bool = False, quote: bool = False
    ) -> str:
        """Format list for markdown"""
        if not items:
            return "None specified\n"

        if quote:
            return "\n\n".join([f"> {item}" for item in items])
        elif numbered:
            return "\n".join([f"{i}. {item}" for i, item in enumerate(items, 1)])
        else:
            return "\n".join([f"- {item}" for item in items])

    def _extract_json_from_response(self, text: str) -> Any:
        """Extract JSON from Claude response"""
        try:
            # Try to parse entire response as JSON
            return json.loads(text)
        except json.JSONDecodeError:
            # Look for JSON in code blocks
            import re

            json_match = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Try to find JSON object/array
            json_match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            raise ValueError(f"Could not extract JSON from response: {text[:200]}")
