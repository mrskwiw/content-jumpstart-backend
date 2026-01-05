from src.agents.content_generator import ContentGeneratorAgent
from src.models.client_brief import ClientBrief, Platform

agent = ContentGeneratorAgent()
brief = ClientBrief(
    company_name='Test',
    business_description='Test',
    ideal_customer='Test',
    main_problem_solved='Test'
)

for platform in Platform:
    prompt = agent._build_system_prompt(brief, platform)
    limit = 8000 if platform == Platform.BLOG else 5000
    exceeds = "EXCEEDS" if len(prompt) >= limit else "OK"
    print(f'{platform.value:12s}: {len(prompt):5d} chars (limit: {limit}) - {exceeds}')
