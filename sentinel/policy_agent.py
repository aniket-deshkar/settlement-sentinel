"""Separately hosted ADK policy specialist exposed through real A2A SDK."""
import json
import os
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types
from google.adk.a2a.utils.agent_to_a2a import to_a2a

class PolicyAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        # A deterministic policy agent is intentional: monetary authority is not probabilistic.
        policy = {'policy_version':'2026-09-01','max_adjustment_minor':200000,'currency':'INR','human_required':True,'simulation_only':True}
        yield Event(author=self.name,content=types.Content(role='model',parts=[types.Part(text=json.dumps(policy))]))
root_agent = PolicyAgent(name='policy_specialist',description='Return the authoritative simulated settlement adjustment policy in JSON. No funds are moved.')
app = to_a2a(root_agent, host=os.getenv('A2A_HOST','localhost'),port=int(os.getenv('A2A_PORT','8001')))
