# src/core/azure_client.py
"""
Azure OpenAI Client - Optimized for E2E Testing Agent
Handles all AI interactions with token management and error handling
"""

import json
import logging
import asyncio
import os
import base64
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from openai import AzureOpenAI
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from config/.env file
config_dir = Path(__file__).parent.parent.parent / "config"
env_path = config_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

@dataclass
class AIResponse:
    """Structured response from AI calls"""
    content: Any
    model: str
    success: bool
    error: Optional[str] = None

class AzureOpenAIClient:
    """
    Optimized Azure OpenAI client for E2E testing agents
    Features:
    - Token limit management 
    - Automatic retry with exponential backoff
    - Structured JSON response parsing
    - Agent-specific prompt optimization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Load credentials from environment variables or config
        self.client_id = os.getenv('AZURE_OPENAI_CLIENT_ID') or (config and config.get('client_id'))
        self.client_secret = os.getenv('AZURE_OPENAI_CLIENT_SECRET') or (config and config.get('client_secret'))
        self.app_key = os.getenv('APP_KEY') or (config and config.get('app_key'))
        self.deployment_name = os.getenv('AZURE_DEPLOYMENT_NAME', 'gpt-4.1') or (config and config.get('deployment_name', 'gpt-4.1'))
        self.api_version = os.getenv('AZURE_API_VERSION', '2024-07-01-preview') or (config and config.get('api_version', '2024-07-01-preview'))
        self.api_base = os.getenv('AZURE_ENDPOINT', 'https://chat-ai.cisco.com') or (config and config.get('api_base', 'https://chat-ai.cisco.com'))
        self.cisco_idp = os.getenv('AZURE_CISCO_IDP', 'https://id.cisco.com/oauth2/default/v1/token')
        
        # Validate required credentials
        if not all([self.client_id, self.client_secret, self.app_key]):
            raise ValueError("Missing required Azure credentials. Check environment variables or config.")
        
        # Get access token from Cisco IDP
        self.access_token = self._get_access_token()
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            azure_endpoint=self.api_base,
            api_key=self.access_token,
            api_version=self.api_version
        )
        
        logger.info(f"Azure OpenAI client initialized with deployment: {self.deployment_name}")
    
    def _get_access_token(self) -> str:
        """Get access token from Cisco IDP"""
        try:
            payload = "grant_type=client_credentials"
            value = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")).decode("utf-8")
            headers = {
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {value}"
            }

            token_response = requests.post(self.cisco_idp, headers=headers, data=payload)
            if token_response.status_code != 200:
                raise Exception(f"Failed to fetch token: {token_response.text}")

            access_token = token_response.json().get("access_token")
            if not access_token:
                raise Exception("No access token returned from Cisco IDP.")
            
            logger.info("Successfully obtained access token from Cisco IDP")
            return access_token
            
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            raise
    
    async def call_agent(self, 
                        agent_name: str,
                        system_prompt: str, 
                        user_prompt: str,
                        response_format: str = "json",
                        temperature: float = 0.1,
                        max_retries: int = 3) -> AIResponse:
        """
        Main method for agent AI calls with error handling and retries
        
        Args:
            agent_name: Name of calling agent (for logging)
            system_prompt: System instruction
            user_prompt: User query
            response_format: "json" or "text"
            temperature: Randomness (0.0-1.0)
            max_retries: Number of retry attempts
        """
        
        # Optimize prompts to stay within token limits
        optimized_system = self._optimize_prompt(system_prompt)
        optimized_user = self._optimize_prompt(user_prompt)
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"[{agent_name}] Making AI call (attempt {attempt + 1})")
                
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[
                        {"role": "system", "content": optimized_system},
                        {"role": "user", "content": optimized_user}
                    ],
                    temperature=temperature,
                    user=json.dumps({"appkey": self.app_key})
                )
                
                # Extract response content
                content = response.choices[0].message.content
                tokens_used = response.usage.total_tokens if response.usage else 0
                
                logger.info(f"[{agent_name}] AI call successful, tokens used: {tokens_used}")
                logger.info(f"[{agent_name}] Raw Azure OpenAI Response: {content}")
                
                # Parse response based on format
                if response_format == "json":
                    try:
                        parsed_content = self._parse_json_response(content)
                        logger.info(f"[{agent_name}] Parsed JSON Response: {parsed_content}")
                        return AIResponse(
                            content=parsed_content,
                            model=self.deployment_name,
                            success=True
                        )
                    except json.JSONDecodeError as e:
                        logger.warning(f"[{agent_name}] JSON parsing failed: {e}")
                        logger.warning(f"[{agent_name}] Failed content was: {content}")
                        # Try to extract JSON from text
                        cleaned_content = self._extract_json_from_text(content)
                        return AIResponse(
                            content=cleaned_content,
                            model=self.deployment_name,
                            success=True
                        )
                else:
                    return AIResponse(
                        content=content,
                        model=self.deployment_name,
                        success=True
                    )
                    
            except Exception as e:
                logger.error(f"[{agent_name}] AI call failed (attempt {attempt + 1}): {e}")
                
                if attempt < max_retries:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"[{agent_name}] Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    return AIResponse(
                        content={},
                        model=self.deployment_name,
                        success=False,
                        error=str(e)
                    )

    def call_agent_sync(self, 
                       agent_name: str,
                       system_prompt: str, 
                       user_prompt: str,
                       response_format: str = "json",
                       temperature: float = 0.1,
                       max_retries: int = 3) -> AIResponse:
        """
        Synchronous wrapper for call_agent method
        """
        return asyncio.run(self.call_agent(
            agent_name=agent_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=response_format,
            temperature=temperature,
            max_retries=max_retries
        ))
    
    def _optimize_prompt(self, prompt: str) -> str:
        """Optimize prompt length to stay within token limits"""
        if len(prompt) <= 0:
            return prompt
        
        # Truncate while preserving structure
        lines = prompt.split('\n')
        optimized_lines = []
        current_length = 0
        
        for line in lines:
            if current_length + len(line) <= 1000000:
                optimized_lines.append(line)
                current_length += len(line)
            else:
                # Add truncation indicator
                optimized_lines.append("... [content truncated for token limit]")
                break
        
        return '\n'.join(optimized_lines)
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON response with error handling"""
        # Remove common formatting issues
        cleaned_content = content.strip()
        
        # Remove markdown code blocks if present
        if cleaned_content.startswith('```json'):
            cleaned_content = cleaned_content[7:]
        if cleaned_content.endswith('```'):
            cleaned_content = cleaned_content[:-3]
        
        cleaned_content = cleaned_content.strip()
        
        try:
            return json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            # Handle "Extra data" error by finding the first complete JSON object
            if "Extra data" in str(e):
                try:
                    # Parse only up to the first complete JSON object
                    decoder = json.JSONDecoder()
                    result, idx = decoder.raw_decode(cleaned_content)
                    logger.warning(f"Found extra data after JSON: {cleaned_content[idx:]}")
                    return result
                except:
                    pass
            # If that fails, try to extract JSON from the content
            return self._extract_json_from_text(cleaned_content)
    
    def _extract_json_from_text(self, content: str) -> Dict[str, Any]:
        """Extract JSON from mixed text content"""
        import re
        
        # Try to find JSON object in text
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Fallback: return error structure
        return {
            "error": "Could not parse JSON response",
            "raw_content": content[:500]  # First 500 chars for debugging
        }

# Agent-specific prompt templates
class PromptTemplates:
    """Optimized prompt templates for different agents"""
    
    @staticmethod
    def nl_processor_prompt() -> str:
        return """You are an expert at understanding E2E testing requirements for legacy Java web applications.
Parse user input into structured test intent optimized for applications like Cisco Catalyst Centre.

Focus on:
- Login workflows and authentication
- Navigation patterns in enterprise apps
- Form interactions and data entry
- Table-based data verification
- Modal dialogs and confirmations

Output JSON format:
{
    "intent_type": "login|navigation|form_interaction|data_verification|workflow",
    "target_application": "brief description",
    "primary_actions": ["action1", "action2", "action3"],
    "test_objectives": ["objective1", "objective2"],
    "complexity_level": "simple|medium|complex",
    "estimated_steps": number,
    "requires_authentication": boolean,
    "ui_patterns_expected": ["tables", "forms", "modals", "navigation"]
}

Be specific and actionable. Focus on what can actually be automated."""
    
    @staticmethod
    def test_strategy_prompt() -> str:
        return """Create comprehensive test strategy for legacy Java web applications.
Consider enterprise application patterns like Cisco Catalyst Centre.

Analyze:
- Legacy UI patterns (tables, forms, slow loading)
- Authentication requirements
- Element detection challenges
- Timing and synchronization needs

Output JSON format:
{
    "strategy_name": "descriptive name",
    "application_analysis": {
        "app_type": "legacy_java",
        "ui_patterns": ["tables", "forms", "modals", "navigation"],
        "expected_challenges": ["slow_loading", "dynamic_content", "authentication"],
        "timing_requirements": "extended_waits"
    },
    "test_approach": {
        "primary_method": "playwright_with_fallbacks",
        "timeout_strategy": "extended_waits_30s",
        "element_strategy": "multiple_selectors_with_ai",
        "authentication_handling": "session_management"
    },
    "execution_plan": [
        {
            "phase": "authentication",
            "actions": ["navigate_to_login", "enter_credentials", "verify_login"],
            "critical": true
        },
        {
            "phase": "main_test",
            "actions": ["based on user intent"],
            "critical": true
        },
        {
            "phase": "verification",
            "actions": ["assertions", "screenshots", "cleanup"],
            "critical": false
        }
    ]
}

Optimize for reliability over speed. Legacy apps need patience."""
    
    @staticmethod
    def test_generation_prompt() -> str:
        return """Generate Playwright test script optimized for legacy Java web applications.

Key considerations:
- EXTENDED timeouts (180s minimum for actions, 300s for navigation) - NEVER USE SHORT TIMEOUTS
- Multiple selector strategies per element
- Slow-mo execution for stability
- Screenshot capture for debugging
- Authentication flow handling
- Browser must be visible (headless: false)

CRITICAL RULE: ALL timeout values must be at least 180000ms (180 seconds). Never use 2000, 5000, 30000 or any value less than 180000.

MANDATORY LOGIN FLOW REQUIREMENTS:
For any login/authentication scenario, you MUST include these steps in order:
1. Navigate to login page
2. Wait for username field visibility
3. Type username into username field
4. Wait for password field visibility  
5. Type password into password field
6. Wait for login/submit button visibility
7. Click the login/submit button
8. Wait for post-login page/navigation menu
9. Verify successful authentication
10. Optional stability wait

NEVER skip the login button wait and click steps! Every login test MUST include steps to:
- Wait for submit/login button to be visible
- Click the submit/login button
- Wait for post-login page to load

Output JSON format:
{
    "test_name": "descriptive name",
    "setup_steps": [
        {
            "action": "browser_init",
            "config": {
                "headless": false,
                "slow_mo": 1000,
                "timeout": 300000
            }
        }
    ],
    "test_steps": [
        {
            "step_id": 1,
            "action": "navigate|click|type|wait|verify",
            "description": "human readable description",
            "target": "element description for user",
            "primary_selector": "preferred CSS selector",
            "fallback_selectors": ["alternative1", "alternative2", "alternative3"],
            "timeout": 180000,
            "wait_condition": "networkidle|load|visible|domcontentloaded",
            "value": "input value if needed",
            "verification": "what to verify after action",
            "critical": boolean,
            "screenshot_after": boolean
        }
    ],
    "cleanup_steps": [
        {
            "action": "screenshot",
            "name": "final_state",
            "full_page": true
        },
        {
            "action": "browser_close"
        }
    ]
}

LOGIN BUTTON SELECTORS - Include these for step 6 (wait) and step 7 (click):
Primary: "button[type='submit'], input[type='submit'], button:contains('Login'), button:contains('Sign In')"
Fallbacks: ["form button", "input[type='submit']", "button[class*='login']", ".login-btn", "#login-button"]

IMPORTANT: 
- Ensure ALL timeout values are at least 180000ms. No exceptions.
- ALWAYS include login button wait + click steps for authentication flows
- Make tests robust and debuggable. Include detailed selectors.
- For login scenarios, include post-login verification steps"""

# Usage example and testing
async def test_azure_client():
    """Test the Azure OpenAI client functionality"""
    
    # Client will use environment variables from .env file
    # No need to pass config if environment variables are set
    try:
        client = AzureOpenAIClient()
        
        # Test NL Processor call
        system_prompt = PromptTemplates.nl_processor_prompt()
        user_prompt = "Login to the application with username 'admin1' and password 'P@ssword99', then verify the dashboard loads"
        
        response = await client.call_agent(
            agent_name="NLProcessor",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format="json"
        )
        
        if response.success:
            print("✅ Azure OpenAI client test successful!")
            print(f"Tokens used: {response.tokens_used}")
            print(f"Response: {json.dumps(response.content, indent=2)}")
        else:
            print(f"❌ Azure OpenAI client test failed: {response.error}")
            
    except Exception as e:
        print(f"❌ Failed to initialize Azure OpenAI client: {e}")
        print("Make sure your .env file in the config folder contains:")
        print("AZURE_OPENAI_CLIENT_ID=your_client_id")
        print("AZURE_OPENAI_CLIENT_SECRET=your_client_secret") 
        print("APP_KEY=your_app_key")

if __name__ == "__main__":
    # Test the client (uncomment and add your credentials)
    # asyncio.run(test_azure_client())
    print("Azure OpenAI Client implementation ready!")
    print("Update the config with your credentials and run test_azure_client()")