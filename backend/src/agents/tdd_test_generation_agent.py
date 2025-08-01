# src/agents/tdd_test_generation_agent.py
"""
TDD-based Test Generation Agent
Generates TypeScript Playwright test files based on .tdd.md templates
"""

import os
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json
import uuid
from ..core.azure_client import AzureOpenAIClient

class TDDTestGenerationAgent:
    """
    Agent responsible for generating TypeScript Playwright test files from .tdd.md templates
    """
    
    def __init__(self, azure_client: AzureOpenAIClient):
        self.azure_client = azure_client
        self.tdd_files_path = "/Users/varsaraf/Downloads/MVP/backend/tdd_files"
        self.e2e_output_path = "/Users/varsaraf/Downloads/MVP/backend/e2e"
    
    async def generate_test_from_template(self, 
                                        intent_type: str,
                                        url: str, 
                                        username: str, 
                                        password: str,
                                        fabric_name: str = None,
                                        session_id: str = None) -> Dict[str, Any]:
        """
        Generate TypeScript test by using existing template and replacing values via LLM
        
        Args:
            intent_type: Type of test (login, get_fabric, etc.)
            url: Target URL for testing
            username: Username for authentication
            password: Password for authentication
            fabric_name: Fabric name (for fabric-related tests)
            session_id: Session ID for file naming
            
        Returns:
            Dictionary with generation results and file paths
        """
        try:
            print(f"🔄 [TDDTestGenerationAgent] Generating test from template for intent: {intent_type}")
            
            # Step 1: Determine template file based on intent
            template_file = self._get_template_file_for_intent(intent_type)
            template_path = os.path.join(self.e2e_output_path, template_file)
            
            if not os.path.exists(template_path):
                raise Exception(f"Template file not found: {template_path}")
            
            # Step 2: Read template content
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            print(f"📖 [TDDTestGenerationAgent] Read template: {template_file}")
            
            # Step 3: Use LLM to replace values in template
            updated_content = await self._replace_values_with_llm(
                template_content, url, username, password, fabric_name, intent_type
            )
            
            # Step 4: Save updated file with session ID in filename directly in e2e folder
            if not session_id:
                session_id = self._generate_session_id()
            
            # Save directly in e2e folder with session ID in filename
            test_filename = f"{session_id}_{intent_type}.spec.ts"
            test_file_path = os.path.join(self.e2e_output_path, test_filename)
            
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print(f"💾 [TDDTestGenerationAgent] Saved updated test: {test_file_path}")
            
            return {
                "success": True,
                "test_file_path": test_file_path,
                "session_dir": self.e2e_output_path,  # Use e2e folder as session dir
                "session_id": session_id,
                "test_type": intent_type,
                "message": f"Generated {intent_type} test from template with updated values"
            }
            
        except Exception as e:
            print(f"❌ [TDDTestGenerationAgent] Failed to generate test from template: {e}")
            return {
                "success": False,
                "error": str(e),
                "intent_type": intent_type
            }
    
    def _get_template_file_for_intent(self, intent_type: str) -> str:
        """Get the appropriate template file for the given intent type"""
        template_mapping = {
            "login": "login.spec.ts",
            "get_fabric": "get_fabric.spec.ts",
            "data_verification": "get_fabric.spec.ts",  # Data verification uses fabric template
            "device_provisioning": "get_fabric.spec.ts",  # Use fabric template as base
            "inventory_workflow": "get_fabric.spec.ts",   # Use fabric template as base
            "fabric_creation": "get_fabric.spec.ts",      # Use fabric template as base
        }
        
        return template_mapping.get(intent_type, "login.spec.ts")  # Default to login
    
    async def _replace_values_with_llm(self, template_content: str, url: str, username: str, 
                                     password: str, fabric_name: str, intent_type: str) -> str:
        """Use Azure OpenAI to replace values in the template"""
        try:
            fabric_instruction = ""
            if fabric_name:
                fabric_instruction = f"- Replace any fabric name with: {fabric_name}"
            
            prompt = f"""You are a code replacement assistant. I have a TypeScript Playwright test file template that needs specific values replaced.

TEMPLATE CONTENT:
```typescript
{template_content}
```

REPLACEMENT INSTRUCTIONS:
- Replace any URL/baseURL with: {url}
- Replace any username with: {username}
- Replace any password with: {password}
{fabric_instruction}

IMPORTANT RULES:
1. Keep ALL the existing code structure, imports, functions, and logic exactly the same
2. ONLY replace the hardcoded values for URL, username, password, and fabric name
3. Do NOT change any of the test logic, selectors, or Playwright commands
4. Do NOT add any new functionality or change existing functionality
5. Keep import paths exactly as they are in the template (the template already has correct relative paths)
6. Return ONLY the complete TypeScript code with replaced values
7. Do NOT include any markdown formatting, explanations, or additional text

Return the complete updated TypeScript file content with the specified values replaced."""

            print(f"🤖 [TDDTestGenerationAgent] Sending template to LLM...")
            
            # Call Azure OpenAI
            ai_response = await self.azure_client.call_agent(
                agent_name="TDDTestGenerationAgent",
                system_prompt="You are a precise code replacement assistant for TypeScript Playwright tests.",
                user_prompt=prompt,
                response_format="text",
                temperature=0.1  # Low temperature for precise replacements
            )
            
            if ai_response.success and ai_response.content and ai_response.content.strip():
                print(f"✅ [TDDTestGenerationAgent] LLM successfully generated tests")
                return ai_response.content.strip()
            else:
                raise Exception("LLM returned empty response")
                
        except Exception as e:
            print(f"❌ [TDDTestGenerationAgent] LLM value replacement failed: {e}")
            # Fallback to manual replacement
            return self.replace_dynamic_parameters(template_content, url, username, password, fabric_name)
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"session_{timestamp}_{unique_id}"
    
    async def generate_typescript_test(self, 
                                url: str, 
                                username: str, 
                                password: str,
                                test_type: str = "login") -> Dict[str, Any]:
        """
        Generate TypeScript Playwright test files based on TDD templates
        
        Args:
            url: Target URL for testing
            username: Username for authentication
            password: Password for authentication
            test_type: Type of test to generate (determines which .tdd.md file to use)
            
        Returns:
            Dictionary with generation results and file paths
        """
        try:
            # Step 1: Read the appropriate .tdd.md file
            tdd_content = self._read_tdd_file(test_type)
            print(f"📖 [TDDTestGenerationAgent] Read TDD content for type: {test_type}")
            
            # Step 2: Generate session ID for filename
            session_id = self._generate_session_id()
            print(f"🆔 [TDDTestGenerationAgent] Generated session ID: {session_id}")
            
            # No need to copy utility files since we're using e2e folder directly
            
            # Step 3: Generate the enhanced prompt with user's specifications
            enhanced_prompt = self._create_enhanced_prompt(url, username, password, tdd_content)
            print(f"🎯 [TDDTestGenerationAgent] Created enhanced prompt")
            
            # Step 4: Call Azure OpenAI to generate TypeScript test
            typescript_code = await self._generate_test_with_azure(enhanced_prompt)
            print(f"🤖 [TDDTestGenerationAgent] Generated TypeScript test code")
            
            # Step 5: Save the generated test file with session ID in filename
            test_filename = f"{session_id}_{test_type}.spec.ts"
            test_file_path = os.path.join(self.e2e_output_path, test_filename)
            self._save_test_file(test_file_path, typescript_code)
            print(f"💾 [TDDTestGenerationAgent] Saved test file: {test_file_path}")
            
            # No cleanup needed since files are in main e2e folder
            print(f"✅ [TDDTestGenerationAgent] Test generation completed for session: {session_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "test_file_path": test_file_path,
                "session_dir": self.e2e_output_path,  # Use e2e folder as session dir
                "test_type": test_type,
                "generated_at": datetime.now().isoformat(),
                "cleanup_scheduled": False  # No cleanup needed for e2e folder files
            }
            
        except Exception as e:
            print(f"❌ [TDDTestGenerationAgent] Generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "test_type": test_type,
                "failed_at": datetime.now().isoformat()
            }
    
    async def generate_typescript_test_with_login(self, 
                                url: str, 
                                username: str, 
                                password: str,
                                test_type: str = "workflow",
                                login_code: str = "") -> Dict[str, Any]:
        """
        Generate TypeScript Playwright test files with login code integration
        
        Args:
            url: Target URL for testing
            username: Username for authentication
            password: Password for authentication
            test_type: Type of test to generate (determines which .tdd.md file to use)
            login_code: Pre-built login code to integrate
            
        Returns:
            Dictionary with generation results and file paths
        """
        try:
            # Step 1: Read the appropriate .tdd.md file
            tdd_content = self._read_tdd_file(test_type)
            print(f"📖 [TDDTestGenerationAgent] Read TDD content for type: {test_type}")
            
            # Step 2: Generate session ID for filename
            session_id = self._generate_session_id()
            print(f"🆔 [TDDTestGenerationAgent] Generated session ID: {session_id}")
            
            # No need to copy utility files since we're using e2e folder directly
            
            # Step 3: Generate the enhanced prompt with login code integration
            enhanced_prompt = self._create_enhanced_prompt_with_login(url, username, password, tdd_content, login_code)
            print(f"🎯 [TDDTestGenerationAgent] Created enhanced prompt with login integration")
            
            # Step 4: Call Azure OpenAI to generate TypeScript test
            typescript_code = await self._generate_test_with_azure(enhanced_prompt)
            print(f"🤖 [TDDTestGenerationAgent] Generated TypeScript test code with login")
            
            # Step 5: Save the generated test file with session ID in filename
            test_filename = f"{session_id}_{test_type}.spec.ts"
            test_file_path = os.path.join(self.e2e_output_path, test_filename)
            self._save_test_file(test_file_path, typescript_code)
            print(f"💾 [TDDTestGenerationAgent] Saved test file: {test_file_path}")
            
            # No cleanup needed since files are in main e2e folder
            print(f"✅ [TDDTestGenerationAgent] Test generation with login completed for session: {session_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "test_file_path": test_file_path,
                "session_dir": self.e2e_output_path,  # Use e2e folder as session dir
                "test_type": test_type,
                "generated_at": datetime.now().isoformat(),
                "cleanup_scheduled": False,  # No cleanup needed for e2e folder files
                "login_integrated": True
            }
            
        except Exception as e:
            print(f"❌ [TDDTestGenerationAgent] Generation with login failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "test_type": test_type,
                "failed_at": datetime.now().isoformat()
            }
    
    def _read_tdd_file(self, test_type: str) -> str:
        """Read the appropriate .tdd.md file based on test type"""
        # MVP only supports these test types
        supported_types = ['login', 'get_fabric']
        
        if test_type not in supported_types:
            raise ValueError(f"Unsupported test type '{test_type}'. MVP only supports: {', '.join(supported_types)}")
        
        tdd_file_path = os.path.join(self.tdd_files_path, f"{test_type}.tdd.md")
        
        if not os.path.exists(tdd_file_path):
            available_files = [f for f in os.listdir(self.tdd_files_path) if f.endswith('.tdd.md')]
            print(f"⚠️ [TDDTestGenerationAgent] TDD file not found: {tdd_file_path}")
            print(f"📋 [TDDTestGenerationAgent] Available TDD files: {available_files}")
            
            # Only use supported fallbacks
            supported_fallbacks = [f for f in available_files if f.replace('.tdd.md', '') in supported_types]
            
            if supported_fallbacks:
                # Use the first supported file as fallback
                fallback_file = supported_fallbacks[0]
                tdd_file_path = os.path.join(self.tdd_files_path, fallback_file)
                print(f"🔄 [TDDTestGenerationAgent] Using fallback TDD file: {fallback_file}")
            else:
                raise FileNotFoundError(f"No supported TDD files found in {self.tdd_files_path}. Required: {supported_types}")
        
        try:
            with open(tdd_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"✅ [TDDTestGenerationAgent] Successfully read TDD file: {tdd_file_path}")
                return content
        except Exception as e:
            print(f"❌ [TDDTestGenerationAgent] Failed to read TDD file: {e}")
            raise
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"session_{timestamp}_{unique_id}"
    
    def _create_enhanced_prompt(self, url: str, username: str, password: str, tdd_content: str) -> str:
        """Create the enhanced prompt with user specifications"""
        
        # Base prompt from user requirements
        base_prompt = f"""Create playwright test for the java-based enterprise microservices application built using Spring Framework with Maven for dependency management for the URL: {url}

Test specs should be created based on the following TDD file content:
{tdd_content}

Use {username} and {password} from the input for valid cases.

Use multiple selector strategies (aria-label, data-test-name, data-test-id, CSS selectors, text content) to robustly find elements

Add appropriate timeout settings in the Playwright config:
- Set global timeout to 600 seconds
- Set action timeout to 300 seconds
- Set navigation timeout to 300 seconds

Implement retry logic for flaky actions like button clicks
Add detailed logging throughout the test for better debugging
Implement graceful error handling to make tests more resilient to timing issues
Take screenshots at key points for debugging failures
Configure Playwright to record videos and traces on test failures

Generate the code and save it in /Users/varsaraf/Downloads/MVP/backend/e2e folder.
Put all the playwright configs in a separate folder/file in this /Users/varsaraf/Downloads/MVP/backend/e2e folder.
Save the navigate, click, text input, and similar others in a separate utils file to reuse that as well in /Users/varsaraf/Downloads/MVP/backend/e2e folder.
Save the login related code in a separate common folder in the /Users/varsaraf/Downloads/MVP/backend/e2e folder if its not present, so that it can be reused.

CRITICAL REQUIREMENTS FOR TYPESCRIPT GENERATION:
1. Generate ONLY the TypeScript test file content, not the entire folder structure
3. Use the extended timeout settings consistently (360000ms for actions, 600000ms global)
4. Include comprehensive error handling and logging
5. Take screenshots at key test points
6. Use multiple selector strategies for robust element finding
7. Follow Playwright TypeScript best practices
8. Include test.describe and test blocks properly structured
9. Use the credentials provided: username="{username}", password="{password}"
10. Test against the URL: "{url}"

IMPORTANT: Return ONLY the TypeScript test file content. Do not include explanations, markdown formatting, or additional files. The response should be pure TypeScript code that can be directly saved as a .spec.ts file."""

        return base_prompt
    
    def _create_enhanced_prompt_with_login(self, url: str, username: str, password: str, tdd_content: str, login_code: str) -> str:
        """Create the enhanced prompt with user specifications and login code integration"""
        
        # Enhanced prompt with login code integration
        base_prompt = f"""Create playwright test for the java-based enterprise microservices application built using Spring Framework with Maven for dependency management for the URL: {url}

Test specs should be created based on the following TDD file content:
{tdd_content}

IMPORTANT: You have access to pre-built login functionality. Here is the login code to integrate:

```typescript
{login_code}
```

INTEGRATION REQUIREMENTS:
1. Import the login function from '../common/login' at the top of your test file
2. Call the login function at the beginning of your test workflow
3. Use the login function like this: await login(page, '{username}', '{password}');
4. After login, proceed with the specific workflow steps for {tdd_content}

Use {username} and {password} from the input for valid cases.

Use multiple selector strategies (aria-label, data-test-name, data-test-id, CSS selectors, text content) to robustly find elements

Add appropriate timeout settings in the Playwright config:
- Set global timeout to 600 seconds
- Set action timeout to 300 seconds
- Set navigation timeout to 300 seconds

Implement retry logic for flaky actions like button clicks
Add detailed logging throughout the test for better debugging
Implement graceful error handling to make tests more resilient to timing issues
Take screenshots at key points for debugging failures
Configure Playwright to record videos and traces on test failures

Generate the code and save it in /Users/varsaraf/Downloads/MVP/backend/e2e folder.
Put all the playwright configs in a separate folder/file in this /Users/varsaraf/Downloads/MVP/backend/e2e folder.
Save the navigate, click, text input, and similar others in a separate utils file to reuse that as well in /Users/varsaraf/Downloads/MVP/backend/e2e folder.

CRITICAL REQUIREMENTS FOR TYPESCRIPT GENERATION:
1. Generate ONLY the TypeScript test file content, not the entire folder structure
2. MUST import login function: import {{ login }} from '../common/login';
3. MUST call login function: await login(page, '{username}', '{password}');
4. Use the extended timeout settings consistently (360000ms for actions, 600000ms global)
5. Include comprehensive error handling and logging
6. Take screenshots at key test points
7. Use multiple selector strategies for robust element finding
8. Follow Playwright TypeScript best practices
9. Include test.describe and test blocks properly structured
10. Use the credentials provided: username="{username}", password="{password}"
11. Test against the URL: "{url}"
12. After login, focus on the specific workflow described in the TDD content

IMPORTANT: Return ONLY the TypeScript test file content. Do not include explanations, markdown formatting, or additional files. The response should be pure TypeScript code that can be directly saved as a .spec.ts file."""

        return base_prompt
    
    async def _generate_test_with_azure(self, prompt: str) -> str:
        """Generate TypeScript test code using Azure OpenAI"""
        try:
            system_prompt = """You are an expert Playwright TypeScript test generator for Java enterprise applications. 
            
Generate high-quality, robust TypeScript test code that. Create playwright test for the React application for the URL: https://{{cluster-ip))/
Test specs should be created based on the .tdd file
use the username and password for valid  scenarios
Use multiple selector strategies (aria-label, data-test-name, data-test-id, CSS selectors, text content) to robustly find elements
Add appropriate timeout settings in the Playwright config:
- Set global timeout to 600 seconds
- Set action timeout to 300 seconds
- Set navigation timeout to 300 seconds
Implement retry logic for flaky actions like button clicks
Add detailed logging throughout the test for better debugging
Implement graceful error handling to make tests more resilient to timing issues
Take screenshots at key points for debugging failures
Configure Playwright to record videos and traces on test failures

Return ONLY the TypeScript test file content without any markdown formatting or explanations."""
            
            # Call Azure OpenAI
            response = await self.azure_client.call_agent(
                agent_name="TDDTestGenerationAgent",
                system_prompt=system_prompt,
                user_prompt=prompt,
                response_format="text", 
                temperature=0.1
            )
            
            if response.success:
                print(f"✅ [TDDTestGenerationAgent] Azure OpenAI generation successful")
                return response.content
            else:
                print(f"❌ [TDDTestGenerationAgent] Azure OpenAI error: {response.error}")
                raise Exception(f"Azure OpenAI test generation failed: {response.error}")
                
        except Exception as e:
            print(f"❌ [TDDTestGenerationAgent] Azure call failed: {e}")
            raise
    
    def _save_test_file(self, file_path: str, content: str) -> None:
        """Save the generated TypeScript test content to file"""
        try:
            # Clean up content if it has markdown formatting
            if content.startswith('```'):
                # Remove markdown code block formatting
                lines = content.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]  # Remove first line with ```typescript or ```
                if lines[-1].strip() == '```':
                    lines = lines[:-1]  # Remove last line with ```
                content = '\n'.join(lines)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ [TDDTestGenerationAgent] Test file saved successfully: {file_path}")
            
            # Log file size for verification
            file_size = os.path.getsize(file_path)
            print(f"📊 [TDDTestGenerationAgent] Generated file size: {file_size} bytes")
            
        except Exception as e:
            print(f"❌ [TDDTestGenerationAgent] Failed to save test file: {e}")
            raise
    
    def _schedule_cleanup(self, session_dir: str) -> None:
        """Schedule cleanup of session directory after 24 hours"""
        try:
            # Create a cleanup metadata file
            cleanup_info = {
                "session_dir": session_dir,
                "created_at": datetime.now().isoformat(),
                "cleanup_at": (datetime.now() + timedelta(hours=24)).isoformat(),
                "status": "scheduled"
            }
            
            cleanup_file = os.path.join(session_dir, ".cleanup_info.json")
            with open(cleanup_file, 'w', encoding='utf-8') as f:
                json.dump(cleanup_info, f, indent=2)
            
            print(f"📋 [TDDTestGenerationAgent] Cleanup info saved: {cleanup_file}")
            
            # In a production environment, you would integrate with a job scheduler
            # For now, we just log the scheduled cleanup
            print(f"⏰ [TDDTestGenerationAgent] Cleanup scheduled for: {cleanup_info['cleanup_at']}")
            
        except Exception as e:
            print(f"⚠️ [TDDTestGenerationAgent] Failed to schedule cleanup: {e}")
            # Don't raise exception as this is not critical for test generation
    
    def list_available_tdd_types(self) -> List[str]:
        """List available TDD file types"""
        try:
            tdd_files = [f.replace('.tdd.md', '') for f in os.listdir(self.tdd_files_path) 
                        if f.endswith('.tdd.md')]
            print(f"📋 [TDDTestGenerationAgent] Available TDD types: {tdd_files}")
            return tdd_files
        except Exception as e:
            print(f"❌ [TDDTestGenerationAgent] Failed to list TDD types: {e}")
            return []
    
    def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """Clean up expired test sessions (24+ hours old)"""
        cleaned_sessions = []
        errors = []
        
        try:
            if not os.path.exists(self.e2e_output_path):
                return {"cleaned_sessions": [], "errors": [], "message": "E2E output path does not exist"}
            
            # Look for session directories
            for item in os.listdir(self.e2e_output_path):
                item_path = os.path.join(self.e2e_output_path, item)
                
                if os.path.isdir(item_path) and item.startswith('session_'):
                    cleanup_file = os.path.join(item_path, ".cleanup_info.json")
                    
                    if os.path.exists(cleanup_file):
                        try:
                            with open(cleanup_file, 'r', encoding='utf-8') as f:
                                cleanup_info = json.load(f)
                            
                            cleanup_time = datetime.fromisoformat(cleanup_info['cleanup_at'])
                            
                            if datetime.now() >= cleanup_time:
                                # Time to clean up
                                import shutil
                                shutil.rmtree(item_path)
                                cleaned_sessions.append({
                                    "session_dir": item_path,
                                    "cleaned_at": datetime.now().isoformat()
                                })
                                print(f"🧹 [TDDTestGenerationAgent] Cleaned up expired session: {item_path}")
                        
                        except Exception as e:
                            errors.append(f"Failed to clean up {item_path}: {e}")
                            print(f"❌ [TDDTestGenerationAgent] Cleanup error for {item_path}: {e}")
        
        except Exception as e:
            errors.append(f"General cleanup error: {e}")
            print(f"❌ [TDDTestGenerationAgent] General cleanup error: {e}")
        
        return {
            "cleaned_sessions": cleaned_sessions,
            "errors": errors,
            "cleanup_completed_at": datetime.now().isoformat()
        }
    
    def _copy_utility_files(self, session_dir: str) -> None:
        """Copy utility files to session directory for relative imports"""
        import shutil
        
        try:
            # Define source and destination paths
            utils_src = os.path.join(self.e2e_output_path, "utils")
            common_src = os.path.join(self.e2e_output_path, "common")
            
            utils_dst = os.path.join(session_dir, "utils")
            common_dst = os.path.join(session_dir, "common")
            
            # Copy utils directory if it exists
            if os.path.exists(utils_src):
                shutil.copytree(utils_src, utils_dst, dirs_exist_ok=True)
                print(f"📁 [TDDTestGenerationAgent] Copied utils directory to {utils_dst}")
            
            # Copy common directory if it exists
            if os.path.exists(common_src):
                shutil.copytree(common_src, common_dst, dirs_exist_ok=True)
                print(f"📁 [TDDTestGenerationAgent] Copied common directory to {common_dst}")
                
        except Exception as e:
            print(f"⚠️ [TDDTestGenerationAgent] Warning: Failed to copy utility files: {e}")
            # Don't fail the entire process for utility file copy errors

    def convert_workflow_steps_to_tdd(self, intent_type: str, workflow_steps: List[str], expected_outcomes: List[str] = None) -> str:
        """
        Convert workflow steps into TDD format similar to login.tdd.md
        
        Args:
            intent_type: The type of workflow (e.g., 'get_fabric', 'create_device')
            workflow_steps: List of workflow steps in plain English
            expected_outcomes: List of expected outcomes/verifications
            
        Returns:
            TDD formatted string content
        """
        try:
            # Create the test method name
            test_method_name = f"test_{intent_type}_workflow"
            
            # Start building the TDD content
            tdd_content = ["Test Cases (Write Tests First)"]
            tdd_content.append(test_method_name)
            
            # Add initial Given-When-Then for login (always required)
            tdd_content.append("Given: User with valid credentials and access to the system")
            tdd_content.append("When: User logs in successfully to the system")
            tdd_content.append("Then: The system should display the home page")
            
            # Convert workflow steps to Given-When-Then format
            for i, step in enumerate(workflow_steps, 1):
                # Clean up the step text
                step_clean = step.strip()
                if step_clean.startswith(f"{i}."):
                    step_clean = step_clean[len(f"{i}."):].strip()
                
                # Determine if this is a When or Then based on content
                if any(keyword in step_clean.lower() for keyword in ['click', 'navigate', 'enter', 'select', 'submit', 'wait']):
                    tdd_content.append(f"When: {step_clean}")
                else:
                    tdd_content.append(f"Then: {step_clean}")
            
            # Add expected outcomes if provided
            if expected_outcomes:
                for outcome in expected_outcomes:
                    tdd_content.append(f"Then: {outcome.strip()}")
            
            # Join all content with newlines
            return "\n".join(tdd_content)
            
        except Exception as e:
            print(f"❌ [TDDTestGenerationAgent] Failed to convert workflow steps to TDD: {e}")
            return f"Test Cases (Write Tests First)\ntest_{intent_type}_workflow\nGiven: User with valid credentials\nWhen: User performs {intent_type} workflow\nThen: The workflow should complete successfully"

    async def generate_workflow_from_steps(self, 
                                         intent_type: str,
                                         workflow_steps: List[str],
                                         url: str,
                                         username: str, 
                                         password: str,
                                         expected_outcomes: List[str] = None) -> Dict[str, Any]:
        """
        Generate complete workflow test from plain English steps
        
        Args:
            intent_type: The type of workflow (e.g., 'get_fabric')
            workflow_steps: List of workflow steps in plain English
            url: Target URL for testing
            username: Username for authentication
            password: Password for authentication
            expected_outcomes: List of expected outcomes/verifications
            
        Returns:
            Dictionary with generation results and file paths
        """
        try:
            print(f"🔄 [TDDTestGenerationAgent] Converting workflow steps to TDD format for: {intent_type}")
            
            # Step 1: Convert workflow steps to TDD format
            tdd_content = self.convert_workflow_steps_to_tdd(intent_type, workflow_steps, expected_outcomes)
            
            # Step 2: Save the TDD file
            tdd_file_path = os.path.join(self.tdd_files_path, f"{intent_type}.tdd.md")
            with open(tdd_file_path, 'w', encoding='utf-8') as f:
                f.write(tdd_content)
            print(f"💾 [TDDTestGenerationAgent] Saved TDD file: {tdd_file_path}")
            
            # Step 3: Read login code for integration
            login_code = ""
            login_ts_path = os.path.join(self.e2e_output_path, "common", "login.ts")
            if os.path.exists(login_ts_path):
                with open(login_ts_path, 'r', encoding='utf-8') as f:
                    login_code = f.read()
            
            # Step 4: Generate TypeScript test with login integration
            result = await self.generate_typescript_test_with_login(
                url=url,
                username=username,
                password=password,
                test_type=intent_type,
                login_code=login_code
            )
            
            if result.get("success"):
                # Step 5: Also create a pre-built spec file for future optimization
                prebuilt_spec_path = os.path.join(self.e2e_output_path, f"{intent_type}.spec.ts")
                
                # Read the generated test and save as pre-built
                generated_file = result.get("test_file_path")
                if generated_file and os.path.exists(generated_file):
                    with open(generated_file, 'r', encoding='utf-8') as f:
                        generated_content = f.read()
                    
                    with open(prebuilt_spec_path, 'w', encoding='utf-8') as f:
                        f.write(generated_content)
                    
                    print(f"💾 [TDDTestGenerationAgent] Created pre-built spec: {prebuilt_spec_path}")
                    result["prebuilt_spec_path"] = prebuilt_spec_path
            
            result["tdd_file_path"] = tdd_file_path
            return result
            
        except Exception as e:
            print(f"❌ [TDDTestGenerationAgent] Failed to generate workflow from steps: {e}")
            return {
                "success": False,
                "error": str(e),
                "intent_type": intent_type,
                "failed_at": datetime.now().isoformat()
            }
    
    def replace_dynamic_parameters(self, typescript_content: str, url: str, username: str, password: str, fabric_name: str = None) -> str:
        """Replace dynamic placeholders and hardcoded values in TypeScript content with actual values"""
        try:
            import re
            
            updated_content = typescript_content
            
            # First, handle placeholder replacements
            placeholder_replacements = {
                '{{TEST_URL}}': url,
                '{{TEST_USERNAME}}': username,
                '{{TEST_PASSWORD}}': password,
            }
            
            if fabric_name:
                placeholder_replacements['{{FABRIC_NAME}}'] = fabric_name
            
            for placeholder, value in placeholder_replacements.items():
                updated_content = updated_content.replace(placeholder, value)
            
            # Second, handle hardcoded value replacements using regex
            
            # Replace baseURL declarations (various formats)
            baseurl_patterns = [
                r"const\s+baseURL\s*=\s*['\"][^'\"]*['\"]",
                r"const\s+baseUrl\s*=\s*['\"][^'\"]*['\"]",
                r"const\s+BASE_URL\s*=\s*['\"][^'\"]*['\"]",
                r"let\s+baseURL\s*=\s*['\"][^'\"]*['\"]",
                r"var\s+baseURL\s*=\s*['\"][^'\"]*['\"]"
            ]
            
            for pattern in baseurl_patterns:
                updated_content = re.sub(pattern, f"const baseURL = '{url}'", updated_content, flags=re.IGNORECASE)
            
            # Replace username in login calls - look for common patterns
            username_patterns = [
                r'login\(page,\s*["\'][^"\']*["\']',  # login(page, "username"
                r'robustFill\([^,]+,\s*["\'][^"\']*["\']',  # robustFill(usernameField, "username"
            ]
            
            # Find and replace username in login calls
            login_pattern = r'login\(page,\s*["\'][^"\']*["\']'
            match = re.search(login_pattern, updated_content)
            if match:
                updated_content = re.sub(r'login\(page,\s*["\'][^"\']*["\']', f'login(page, "{username}"', updated_content)
            
            # Replace password in login calls - look for the second parameter
            password_pattern = r'login\(page,\s*["\'][^"\']*["\'],\s*["\'][^"\']*["\']'
            match = re.search(password_pattern, updated_content)
            if match:
                updated_content = re.sub(r'login\(page,\s*(["\'][^"\']*["\'])\s*,\s*["\'][^"\']*["\']', 
                                       f'login(page, \\1, "{password}"', updated_content)
            
            # Replace fabric name if provided
            if fabric_name:
                fabric_patterns = [
                    r'fabric["\'\s]*[=:]["\'\s]*[^"\']*["\']',
                    r'fabricName["\'\s]*[=:]["\'\s]*[^"\']*["\']',
                    r'FABRIC_NAME["\'\s]*[=:]["\'\s]*[^"\']*["\']'
                ]
                
                for pattern in fabric_patterns:
                    updated_content = re.sub(pattern, f'fabricName = "{fabric_name}"', updated_content, flags=re.IGNORECASE)
            
            print(f"✅ [TDDTestGenerationAgent] Replaced dynamic parameters: URL={url}, Username={username}, Fabric={fabric_name}")
            return updated_content
            
        except Exception as e:
            print(f"❌ [TDDTestGenerationAgent] Error replacing dynamic parameters: {str(e)}")
            return typescript_content  # Return original if replacement fails
    
    def parse_user_instruction_for_parameters(self, user_instruction: str) -> dict:
        """Parse user instruction to extract dynamic parameters like URL, username, password, fabric name"""
        import re
        try:
            parameters = {}
            
            print(f"🔍 [TDDTestGenerationAgent] Parsing instruction: {user_instruction[:200]}...")
            
            # Extract URL patterns (most specific first, avoid false positives)
            url_patterns = [
                r'(https?://[^\s,\)]+)',  # Any HTTP/HTTPS URL anywhere (highest priority)
                r'(?:url|website)[:\s]+([https?://][^\s,]+)',  # URL with protocol after url:
                r'(?:url|website)[:\s]+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s,]*)',  # domain.com format after url: (more restrictive)
            ]
            
            for pattern in url_patterns:
                match = re.search(pattern, user_instruction, re.IGNORECASE)
                if match:
                    url = match.group(1)
                    # Clean up URL if it has trailing punctuation
                    if url.endswith(',') or url.endswith(';') or url.endswith(')'):
                        url = url[:-1]
                    parameters['url'] = url
                    print(f"✅ [TDDTestGenerationAgent] Extracted URL from instruction: {url}")
                    break
            
            # Extract username patterns (more specific)
            username_patterns = [
                r'(?:username|user)[:\s]+([^\s,]+)',
                r'(?:login with|use)[:\s]+(?:user|username)[:\s]+([^\s,]+)',
                r'with user[:\s]+([^\s,]+)',
                r'credentials[:\s]+([^\s,/]+)(?:/|,|\s)',  # username/password format
            ]
            
            for pattern in username_patterns:
                match = re.search(pattern, user_instruction, re.IGNORECASE)
                if match:
                    username = match.group(1)
                    # Clean up username if it has trailing punctuation
                    if username.endswith(',') or username.endswith(';') or username.endswith('/'):
                        username = username[:-1]
                    parameters['username'] = username
                    print(f"✅ [TDDTestGenerationAgent] Extracted username from instruction: {username}")
                    break
            
            # Extract password patterns (more specific)
            password_patterns = [
                r'(?:password|pass)[:\s]+([^\s,]+)',
                r'credentials[:\s]+[^\s,/]+[/:]([^\s,]+)',  # username/password or username:password format
                r'(?:login with|use).*password[:\s]+([^\s,]+)',
            ]
            
            for pattern in password_patterns:
                match = re.search(pattern, user_instruction, re.IGNORECASE)
                if match:
                    password = match.group(1)
                    # Clean up password if it has trailing punctuation
                    if password.endswith(',') or password.endswith(';'):
                        password = password[:-1]
                    parameters['password'] = password
                    print(f"✅ [TDDTestGenerationAgent] Extracted password from instruction: {password}")
                    break
            
            # Extract fabric name patterns (more specific)
            fabric_patterns = [
                r'(?:fabric called|fabric named)[:\s]+([^\s,]+)',
                r'fabric[:\s]+([^\s,]+)',
                r'fabric name[:\s]+([^\s,]+)',
                r'get fabric[:\s]+([^\s,]+)',
                r'create fabric[:\s]+([^\s,]+)'
            ]
            
            for pattern in fabric_patterns:
                match = re.search(pattern, user_instruction, re.IGNORECASE)
                if match:
                    fabric_name = match.group(1)
                    # Clean up fabric name if it has trailing punctuation
                    if fabric_name.endswith(',') or fabric_name.endswith(';'):
                        fabric_name = fabric_name[:-1]
                    parameters['fabric_name'] = fabric_name
                    print(f"✅ [TDDTestGenerationAgent] Extracted fabric name from instruction: {fabric_name}")
                    break
            
            print(f"✅ [TDDTestGenerationAgent] Parsed parameters from instruction: {parameters}")
            return parameters
            
        except Exception as e:
            print(f"❌ [TDDTestGenerationAgent] Error parsing user instruction: {str(e)}")
            return {}
