import json
import logging
import re
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

Respond EXACTLY with the following two parts:
1. A valid JSON object containing the tool metadata enclosed in ```json ... ``` tags.
2. A Python code block containing the code enclosed in ```python ... ``` tags.

Example Response format:
```json
{{
    "name": "snake_case_tool_name",
    "description": "Clear description of what the tool does",
    "parameters": {{"type": "object", "properties": {{...JSON schema for params...}}}}
}}
```
```python
def run(params):
    import requests
    from src.config import Config
    headers = {{'Authorization': f'Bearer {{Config.GITHUB_TOKEN}}', 'User-Agent': 'WatermelonAgent/1.0', 'Accept': 'application/vnd.github.v3+json'}}
    # ... your python code ...
    return {{'status': 'success'}}
```
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
            
            content = response.content
            
            # Extract JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if not json_match:
                # Fallback
                json_match = re.search(r'(\{.*?\})', content, re.DOTALL)
                if not json_match:
                    raise Exception("Could not find JSON metadata block in response")
            json_str = json_match.group(1)
                
            # Extract Python
            python_match = re.search(r'```python\s*(.*?)\s*```', content, re.DOTALL)
            if not python_match:
                raise Exception("Could not find Python code block in response")
            python_code = python_match.group(1)
                
            data = json.loads(json_str)
            
            cap = CapabilitySchema(
                name=data.get("name", "generated_tool"),
                description=data.get("description", "A generated tool"),
                parameters=data.get("parameters", {}),
                code=python_code,
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
