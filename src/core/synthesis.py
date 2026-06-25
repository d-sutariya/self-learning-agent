import json
import logging
from typing import Dict, Any, Tuple
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from src.config import Config
from src.core.utils import setup_logger
from src.core.schema import CapabilitySchema

logger = setup_logger(__name__)

# Prompt for generating a new capability
SYNTHESIS_PROMPT = """
You are an expert Python developer tasked with creating a function to interact with the GitHub API.
The agent needs a new tool to accomplish the following intent: "{intent}"
The planner will pass these parameters to your function: {params}

You must write a self-contained Python function that performs this exact action. 
- Use the `requests` library.
- The GitHub token is available in `src.config.Config.GITHUB_TOKEN`.
- ALWAYS use these exact headers for the request: `headers = {{'Authorization': f'Bearer {{Config.GITHUB_TOKEN}}', 'User-Agent': 'WatermelonAgent/1.0', 'Accept': 'application/vnd.github.v3+json'}}`
- If querying a repository, ensure you use the format `owner/repo` (e.g., if the user provides a repository name without an owner, assume it's their own repo, so query `https://api.github.com/user` to get their login first, or if the full repo path is known, use `https://api.github.com/repos/{{owner}}/{{repo}}`).
- The function MUST accept a single argument `params` which is a dictionary.
- Ensure you extract parameters safely (e.g., using `params.get('key')`). If a required parameter is missing or None, raise a clear Exception.
- The function MUST return a dictionary with the results, or raise an Exception if the API call fails.
- CRITICAL JSON FORMATTING: You must escape all newlines in the `code` field with `\\n`. DO NOT use double quotes (`"`) inside your Python code; use single quotes (`'`) for all Python strings to avoid breaking the JSON structure.

Respond ONLY with a valid JSON object matching this schema:
{{
    "name": "snake_case_tool_name",
    "description": "Clear description of what the tool does",
    "parameters": {{"type": "object", "properties": {{...JSON schema for params...}}}},
    "code": "def run(params):\\n    import requests\\n    from src.config import Config\\n    headers = {{'Authorization': f'Bearer {{Config.GITHUB_TOKEN}}', 'User-Agent': 'WatermelonAgent/1.0'}}\\n    ... python code ...\\n    return {{'status': 'success'}}"
}}
"""

class CapabilitySynthesizer:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile", 
            api_key=Config.GROQ_API_KEY,
            temperature=0.1
        )
        self.prompt = PromptTemplate.from_template(SYNTHESIS_PROMPT)

    def synthesize(self, intent: str, params: Dict[str, Any] = None) -> Tuple[bool, Any]:
        """Synthesizes a new tool using the LLM."""
        logger.info(f"Synthesizing capability for intent: {intent}")
        params_str = str(params) if params else "{}"
        try:
            response = self.llm.invoke(self.prompt.format(intent=intent, params=params_str))
            
            # Clean up potential markdown formatting around JSON
            json_str = response.content.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
                
            data = json.loads(json_str)
            
            cap = CapabilitySchema(
                name=data["name"],
                description=data["description"],
                parameters=data["parameters"],
                code=data["code"],
                constraints=[]
            )
            
            # Test the code (Dry run or syntax check)
            success, msg = self._test_capability(cap)
            if not success:
                logger.error(f"Synthesized code failed validation: {msg}")
                return False, msg
                
            return True, cap
            
        except Exception as e:
            logger.error(f"Failed to synthesize capability: {e}")
            return False, str(e)
            
    def _test_capability(self, capability: CapabilitySchema) -> Tuple[bool, str]:
        """Safely tests the generated Python code to ensure it's structurally valid."""
        try:
            # We don't execute it right away, but we compile it to catch syntax errors
            compile(capability.code, "<string>", "exec")
            return True, "Valid syntax"
        except SyntaxError as e:
            return False, f"Syntax Error: {e}"
