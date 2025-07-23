# src/agents/test_generation_agent.py
"""
Test Generation Agent
Generates actual test code based on strategy and detected elements
"""

import asyncio
from typing import Dict, Any
from ..core.azure_client import AzureOpenAIClient, PromptTemplates

class TestGenerationAgent:
    """
    Agent responsible for generating actual test code
    """
    
    def __init__(self, azure_client: AzureOpenAIClient):
        self.azure_client = azure_client
    
    def generate_test_code(self, strategy: Dict[str, Any], elements: Dict[str, Any], url: str, credentials: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Generate actual test code
        
        Args:
            strategy: Test strategy from TestStrategyAgent
            elements: Detected elements from ElementDetectionAgent
            url: Target URL
            credentials: Dictionary with username and password
            
        Returns:
            Generated test code and metadata
        """
        try:
            # Include credentials in the prompt if provided
            credentials_text = ""
            if credentials:
                credentials_text = f"""
            User Credentials:
            - Username: {credentials.get('username', 'testuser')}
            - Password: {credentials.get('password', 'testpassword')}
            
            Use these exact credentials in the generated test code.
            """
            
            # Use Azure OpenAI for code generation
            system_prompt = PromptTemplates.test_generation_prompt()
            user_prompt = f"""
            Target URL: {url}
            Test Strategy: {strategy}
            Detected Elements: {elements}
            {credentials_text}
            
            Generate Playwright test code that is robust and handles legacy Java web applications.
            
            CRITICAL TIMEOUT REQUIREMENTS - NO EXCEPTIONS:
            - Navigation timeout: 300 seconds (300000ms) - NEVER LESS
            - Page load timeout: 300 seconds (300000ms) - NEVER LESS
            - Element wait timeout: 180 seconds (180000ms) - NEVER LESS
            - Action timeout: 180 seconds (180000ms) - NEVER LESS
            - Default timeout: 180 seconds (180000ms) - NEVER LESS
            - Wait actions: Use 180000ms minimum, NEVER use 2000ms or other short values
            
            CRITICAL: ALL timeout values in the generated test MUST be >= 180000ms (180 seconds).
            Do NOT use any timeout values less than 180000ms anywhere in the test.
            Even for simple wait actions, use minimum 180000ms timeout.
            
            MANDATORY LOGIN FLOW STEPS:
            If this is a login/authentication test, you MUST include ALL these steps:
            1. Navigate to login page (with 300000ms timeout)
            2. Wait for username field to be visible (180000ms timeout)
            3. Type username into username field
            4. Wait for password field to be visible (180000ms timeout)
            5. Type password into password field
            6. Wait for login/submit button to be visible (180000ms timeout) - NEVER SKIP THIS
            7. Click the login/submit button (180000ms timeout) - NEVER SKIP THIS
            8. Wait for post-login page/navigation menu (300000ms timeout)
            9. Verify successful authentication (180000ms timeout)
            10. Optional stability wait for page completion
            
            LOGIN BUTTON REQUIREMENTS:
            - ALWAYS include step to wait for login button visibility
            - ALWAYS include step to click the login button
            - Use comprehensive selectors for login buttons:
              Primary: "button[type='submit'], input[type='submit'], button:contains('Login'), button:contains('Sign In')"
              Fallbacks: ["form button", "input[type='submit']", "button[class*='login']", ".login-btn", "#login-button"]
            
            BROWSER CONFIGURATION REQUIREMENTS:
            - headless: false (must show browser window)
            - Keep browser open throughout test execution
            - Use proper wait strategies (networkidle, domcontentloaded)
            - Add explicit waits between actions (2-3 seconds duration, but 180000ms timeout)
            
            Focus on reliability with EXTENDED timeouts, fallback strategies, and visible browser execution.
            Ensure browser stays open and visible during the entire test execution.
            REMEMBER: Every single timeout value must be at least 180000ms (180 seconds).
            NEVER SKIP login button wait and click steps for authentication flows.
            """
            
            # Call Azure OpenAI
            response = self.azure_client.call_agent_sync(
                agent_name="TestGenerationAgent",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                temperature=0.1
            )
            
            print(f"🔍 [TestGenerationAgent] Azure Response Success: {response.success}")
            if response.success:
                print(f"🔍 [TestGenerationAgent] Response Type: {type(response.content)}")
                print(f"🔍 [TestGenerationAgent] Response Content: {response.content}")
                return response.content
            else:
                print(f"❌ [TestGenerationAgent] Azure Response Error: {response.error}")
                raise Exception(f"Azure OpenAI test generation failed: {response.error}")
                
        except Exception as e:
            print(f"❌ Test Generation Agent Azure call failed: {e}")
            print(f"🔍 Exception type: {type(e)}")
            raise Exception(f"Test generation failed: {e}")

    def _generate_test_generation_prompt(self, strategy: Dict[str, Any], elements: Dict[str, Any], url: str) -> str:
        """Generate prompt for test generation"""
        return f"""
        Generate comprehensive Playwright test code for the following scenario:
        
        Target URL: {url}
        Test Strategy: {strategy}
        Detected Elements: {elements}
        
        MANDATORY TIMEOUT REQUIREMENTS - ABSOLUTELY NO EXCEPTIONS:
        1. Generate robust Playwright Python test code with EXTENDED TIMEOUTS ONLY
        2. Navigation timeout: 300 seconds (300000ms) - NEVER USE SHORTER VALUES
        3. Page load timeout: 300 seconds (300000ms) - NEVER USE SHORTER VALUES
        4. Element timeout: 180 seconds (180000ms) - NEVER USE SHORTER VALUES
        5. Action timeout: 180 seconds (180000ms) - NEVER USE SHORTER VALUES
        6. Default timeout: 180 seconds (180000ms) - NEVER USE SHORTER VALUES
        7. Browser must be visible (headless: false)
        8. Add 2-3 second delays between actions (but with 180000ms timeouts)
        9. Use proper wait strategies (networkidle, domcontentloaded)
        10. Keep browser open throughout execution
        
        CRITICAL RULE: Every single timeout value in your response must be >= 180000 (180 seconds).
        Do not use 2000, 5000, 10000, 30000, or any value less than 180000 for timeouts.
        
        Return JSON format:
        {{
            "test_name": "descriptive_test_name",
            "framework": "playwright",
            "language": "python",
            "test_code": "complete Python test code with extended timeouts",
            "setup_requirements": ["playwright", "pytest", "pytest-playwright"],
            "configuration": {{
                "browser": "chromium",
                "headless": false,
                "timeout": 180000,
                "navigation_timeout": 300000,
                "action_timeout": 180000
            }},
            "test_data": {{
                "credentials": {{"username": "test", "password": "test"}},
                "form_data": {{}},
                "expected_results": {{}}
            }},
            "expected_files": ["test_file.py", "conftest.py", "requirements.txt"]
        }}
        
        FINAL REMINDER: ALL timeout values must be at least 180000ms. No exceptions.
        """
