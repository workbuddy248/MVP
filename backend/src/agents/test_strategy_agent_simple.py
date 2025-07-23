# src/agents/test_strategy_agent.py
"""
Test Strategy Agent
Generates comprehensive test strategies for web applications
"""

from typing import Dict, Any
from ..core.azure_client import AzureOpenAIClient, PromptTemplates

class TestStrategyAgent:
    """
    Agent responsible for generating test strategies based on processed instructions
    """
    
    def __init__(self, azure_client: AzureOpenAIClient):
        self.azure_client = azure_client
    
    def generate_strategy(self, processed_instructions: Dict[str, Any], url: str) -> Dict[str, Any]:
        """
        Generate a comprehensive test strategy
        
        Args:
            processed_instructions: Output from NL processor
            url: Target URL
            
        Returns:
            Test strategy dictionary
        """
        try:
            # Use Azure OpenAI for strategy generation
            system_prompt = PromptTemplates.test_strategy_prompt()
            user_prompt = f"""
            Target URL: {url}
            Processed Instructions: {processed_instructions}
            
            Generate a comprehensive test strategy for this application.
            Consider the test type: {processed_instructions.get('test_type', 'functional')}
            Expected actions: {processed_instructions.get('actions', [])}
            Complexity level: {processed_instructions.get('complexity', 'medium')}
            """
            
            # Call Azure OpenAI
            response = self.azure_client.call_agent_sync(
                agent_name="TestStrategyAgent",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                temperature=0.2
            )
            
            if response.success:
                return response.content
            else:
                raise Exception(f"Azure OpenAI strategy generation failed: {response.error}")
                
        except Exception as e:
            print(f"Test Strategy Agent Azure call failed: {e}")
            raise Exception(f"Test strategy generation failed: {e}")

    def _generate_prompt(self, processed_instructions: Dict[str, Any], url: str) -> str:
        """Generate optimized prompt for Azure OpenAI test strategy generation"""
        test_type = processed_instructions.get('test_type', 'functional')
        complexity = processed_instructions.get('complexity', 'medium')
        actions = processed_instructions.get('actions', [])
        priority = processed_instructions.get('priority', 'medium')
        
        prompt = f"""
        Generate a comprehensive test strategy for a {complexity} {test_type} test scenario.
        
        Target URL: {url}
        Test Type: {test_type}
        Complexity Level: {complexity}
        Priority: {priority}
        Required Actions: {', '.join(actions) if actions else 'Standard interactions'}
        
        CRITICAL TIMEOUT REQUIREMENTS:
        - All timeouts must be extended for slow/legacy applications
        - Navigation timeout: 300 seconds minimum
        - Page load timeout: 300 seconds minimum  
        - Element timeout: 180 seconds minimum
        - Action timeout: 180 seconds minimum
        - Add 2-3 second delays between actions
        
        Create a JSON response with the following structure:
        {{
            "strategy_name": "Descriptive name for this test strategy",
            "target_url": "{url}",
            "approach": "Testing methodology with extended timeouts",
            "execution_phases": [
                {{
                    "phase": "phase_name",
                    "description": "What happens in this phase",
                    "timeout": 300,
                    "critical": true/false
                }}
            ],
            "test_cases": [
                {{
                    "name": "test_case_name",
                    "description": "What this test validates",
                    "priority": "high/medium/low",
                    "actions": ["action1", "action2"]
                }}
            ],
            "timing_strategy": {{
                "base_timeout": 180,
                "element_timeout": 180,
                "page_load_timeout": 300,
                "navigation_timeout": 300,
                "action_delay": 3,
                "retry_attempts": 3,
                "retry_delay": 2
            }},
            "error_handling": {{
                "screenshot_on_failure": true/false,
                "retry_on_timeout": true/false,
                "continue_on_non_critical_failure": true/false,
                "log_detailed_errors": true/false,
                "fallback_selectors": true/false
            }},
            "reporting": {{
                "screenshots": true/false,
                "video_recording": true/false,
                "detailed_logs": true/false,
                "performance_metrics": true/false
            }}
        }}
        
        Consider the complexity level when setting timeouts and retry strategies.
        For {test_type} tests, focus on relevant validation points.
        Include appropriate error handling and recovery mechanisms.
        ENSURE ALL TIMEOUTS ARE EXTENDED FOR SLOW/LEGACY APPLICATIONS.
        BROWSER MUST REMAIN VISIBLE (headless: false) THROUGHOUT EXECUTION.
        """
        
        return prompt
