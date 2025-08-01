# src/agents/nl_processor.py
"""
Natural Language Processor Agent
Converts natural language instructions into structured test requirements
"""

import asyncio
from typing import Dict, List, Any
from ..core.azure_client import AzureOpenAIClient, PromptTemplates
from ..models.test_models import UserIntent, IntentType, ComplexityLevel

class NLProcessor:
    """
    Natural Language Processing agent that converts user instructions
    into structured test requirements
    """
    
    def __init__(self, azure_client: AzureOpenAIClient):
        self.azure_client = azure_client
        
    def process_instructions(self, instructions: str, url: str) -> Dict[str, Any]:
        """
        Process natural language instructions into structured test data
        
        Args:
            instructions: User's natural language description
            url: Target URL for testing
            
        Returns:
            Structured test requirements
        """
        try:
            # Use Azure OpenAI for processing
            system_prompt = PromptTemplates.nl_processor_prompt()
            user_prompt = f"""
            URL: {url}
            Instructions: {instructions}
            
            Parse these instructions into the required JSON format for test automation.
            """
            
            # Call Azure OpenAI (synchronous wrapper for async call)
            response = self.azure_client.call_agent_sync(
                agent_name="NLProcessor",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                temperature=0.1
            )
            
            if response.success:
                # Validate and fix intent type for MVP
                content = response.content
                intent_type = content.get('intent_type', '')
                
                # MVP only supports login and get_fabric intents
                supported_intents = ['login', 'get_fabric']
                
                # Get original instruction text for analysis
                original_instructions = user_prompt.lower()
                
                # Strong fabric detection keywords
                fabric_keywords = [
                    'fabric', 'fabric details', 'fabric name', 'fabric management',
                    'border', 'site', 'global/', 'bld1', 'bld2', 
                    'view details', 'navigate to', 'show details', 'display',
                    'border_l3vn_design_site', 'catalyst centre'
                ]
                
                # Check if this should actually be get_fabric (even if AI said login)
                fabric_detected = any(keyword in original_instructions for keyword in fabric_keywords)
                
                if fabric_detected and intent_type == 'login':
                    print(f"🔄 [NLProcessor] Overriding intent '{intent_type}' to 'get_fabric' - fabric keywords detected in: {original_instructions}")
                    content['intent_type'] = 'get_fabric'
                elif intent_type not in supported_intents:
                    # Auto-correct unsupported intents
                    if fabric_detected:
                        print(f"🔄 [NLProcessor] Auto-correcting intent '{intent_type}' to 'get_fabric' based on fabric keywords")
                        content['intent_type'] = 'get_fabric'
                    # Check if it's login-related (without fabric context)
                    elif any(keyword in original_instructions for keyword in ['login', 'sign in', 'authenticate', 'credentials']) and not fabric_detected:
                        print(f"🔄 [NLProcessor] Auto-correcting intent '{intent_type}' to 'login' based on authentication keywords")
                        content['intent_type'] = 'login'
                    else:
                        raise Exception(f"Unsupported intent type '{intent_type}'. MVP only supports: {', '.join(supported_intents)}. Please modify your instructions to focus on login or fabric management tasks.")
                
                return content
            else:
                raise Exception(f"Azure OpenAI processing failed: {response.error}")
                
        except Exception as e:
            print(f"NL Processor Azure call failed: {e}")
            raise Exception(f"Natural language processing failed: {e}")

    async def parse_user_intent(self, user_input: str, context: Dict[str, Any] = None) -> UserIntent:
        """
        Parse user input into a UserIntent object for orchestrator use
        
        Args:
            user_input: User's natural language description
            context: Additional context information
            
        Returns:
            UserIntent object
        """
        try:
            # Get the URL from context if available
            url = context.get('url', 'https://example.com') if context else 'https://example.com'
            
            # Use the existing process_instructions method
            processed = await asyncio.to_thread(self.process_instructions, user_input, url)
            
            # Convert to UserIntent object
            return UserIntent(
                intent_type=IntentType(processed.get('intent_type', 'functional')),
                target_application=processed.get('target_application', f'Application at {url}'),
                primary_actions=processed.get('primary_actions', []),
                test_objectives=processed.get('test_objectives', []),
                complexity_level=ComplexityLevel(processed.get('complexity_level', 'medium')),
                estimated_steps=processed.get('estimated_steps', 5),
                requires_authentication=processed.get('requires_authentication', True),
                ui_patterns_expected=processed.get('ui_patterns_expected', []),
                additional_context=processed.get('additional_context', {}),
                workflow_type=processed.get('workflow_type'),
                requires_template=processed.get('requires_template', False),
                extracted_values=processed.get('extracted_values', {})
            )
            
        except Exception as e:
            print(f"NL Processor parse_user_intent failed: {e}")
            raise Exception(f"User intent parsing failed: {e}")

    def _determine_test_type(self, instructions: str) -> str:
        """Determine the type of test based on instructions"""
        instructions_lower = instructions.lower()
        
        if 'login' in instructions_lower or 'sign in' in instructions_lower:
            return 'authentication'
        elif 'click' in instructions_lower or 'button' in instructions_lower:
            return 'interaction'
        elif 'form' in instructions_lower or 'fill' in instructions_lower:
            return 'form_submission'
        elif 'verify' in instructions_lower or 'check' in instructions_lower:
            return 'verification'
        elif 'navigate' in instructions_lower or 'go to' in instructions_lower:
            return 'navigation'
        else:
            return 'functional'
    
    def _extract_actions(self, instructions: str) -> List[str]:
        """Extract possible actions from instructions"""
        actions = []
        instructions_lower = instructions.lower()
        
        # Map common verbs to actions
        action_mapping = {
            'click': 'click',
            'press': 'click',
            'type': 'input',
            'enter': 'input',
            'fill': 'input',
            'select': 'select',
            'choose': 'select',
            'navigate': 'navigate',
            'go to': 'navigate',
            'verify': 'verify',
            'check': 'verify',
            'wait': 'wait'
        }
        
        for verb, action in action_mapping.items():
            if verb in instructions_lower:
                actions.append(action)
        
        return list(set(actions)) or ['interaction']
    
    def _extract_validations(self, instructions: str) -> List[str]:
        """Extract validation requirements"""
        validations = []
        instructions_lower = instructions.lower()
        
        if 'success' in instructions_lower or 'successful' in instructions_lower:
            validations.append('success_message')
        if 'error' in instructions_lower or 'fail' in instructions_lower:
            validations.append('error_handling')
        if 'page' in instructions_lower or 'url' in instructions_lower:
            validations.append('page_navigation')
        if 'visible' in instructions_lower or 'display' in instructions_lower:
            validations.append('element_visibility')
        
        return validations or ['basic_validation']
    
    def _extract_test_data(self, instructions: str) -> Dict[str, Any]:
        """Extract test data from instructions"""
        test_data = {}
        
        # Look for quoted strings (potential data)
        import re
        quoted_strings = re.findall(r'"([^"]*)"', instructions)
        if quoted_strings:
            test_data['inputs'] = quoted_strings
        
        # Look for common patterns
        if 'username' in instructions.lower():
            test_data['requires_username'] = True
        if 'password' in instructions.lower():
            test_data['requires_password'] = True
        if 'email' in instructions.lower():
            test_data['requires_email'] = True
        
        return test_data
    
    def _determine_priority(self, instructions: str) -> str:
        """Determine test priority"""
        instructions_lower = instructions.lower()
        
        if 'critical' in instructions_lower or 'important' in instructions_lower:
            return 'high'
        elif 'optional' in instructions_lower or 'nice to have' in instructions_lower:
            return 'low'
        else:
            return 'medium'
    
    def _assess_complexity(self, instructions: str) -> str:
        """Assess test complexity"""
        instructions_lower = instructions.lower()
        
        # Count action words
        action_words = ['click', 'type', 'fill', 'select', 'navigate', 'verify', 'wait']
        action_count = sum(1 for word in action_words if word in instructions_lower)
        
        if action_count <= 2:
            return 'simple'
        elif action_count <= 5:
            return 'medium'
        else:
            return 'complex'
