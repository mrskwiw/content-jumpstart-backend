"""Content-intelligence layer: pure, deterministic post-quality analysis.

Genericity detection, engagement prediction, and the assess_post facade. Placed in
src/ (the lower layer) so both the generation pipeline (src/agents) and the API
(backend) can import it without inverting the backend->src dependency direction.
"""
