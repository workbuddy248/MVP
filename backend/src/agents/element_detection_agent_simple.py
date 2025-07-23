# src/agents/element_detection_agent.py
"""
Element Detection Agent
Detects and analyzes page elements for test automation
"""

import asyncio
from typing import Dict, Any, List
from ..core.azure_client import AzureOpenAIClient

class ElementDetectionAgent:
    """
    Agent responsible for detecting and analyzing page elements
    """
    
    def __init__(self, azure_client: AzureOpenAIClient):
        self.azure_client = azure_client
    
    def detect_elements(self, url: str, target_elements: List[str] = None) -> Dict[str, Any]:
        """
        Detect elements on the target page
        
        Args:
            url: Target URL to analyze
            target_elements: Specific elements to look for
            
        Returns:
            Dictionary of detected elements and their properties
        """
        try:
            # Use Azure OpenAI for element detection strategy
            system_prompt = self._get_element_detection_prompt()
            user_prompt = f"""
            Target URL: {url}
            Target Elements: {target_elements or 'common web elements'}
            
            Analyze this URL and provide element detection strategies for common web elements
            that would be found on a typical web application.
            
            Focus on elements like:
            - Login forms (username, password, submit button)
            - Navigation menus
            - Form inputs
            - Buttons and links
            - Tables and data displays
            """
            
            # Call Azure OpenAI
            response = self.azure_client.call_agent_sync(
                agent_name="ElementDetectionAgent",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                temperature=0.1
            )
            
            if response.success:
                return response.content
            else:
                raise Exception(f"Azure OpenAI element detection failed: {response.error}")
                
        except Exception as e:
            print(f"Element Detection Agent Azure call failed: {e}")
            raise Exception(f"Element detection failed: {e}")

    def _get_element_detection_prompt(self) -> str:
        """Get system prompt for element detection"""
        return """You are an expert at analyzing web applications and detecting elements for test automation.

Your task is to provide element detection strategies for web applications, focusing on:

1. Common Web Elements:
   - Login forms (username, password, submit buttons)
   - Navigation menus and links
   - Form inputs (text, select, checkbox, radio)
   - Buttons and clickable elements
   - Tables and data displays
   - Modal dialogs and overlays

2. Selector Strategies:
   - Primary CSS selectors (ID, class, attributes)
   - Fallback selectors for robustness
   - Text-based selectors for buttons/links
   - Structural selectors (parent/child relationships)

3. Element Properties:
   - Element type (button, input, form, nav, etc.)
   - Interaction method (click, fill, select, etc.)
   - Visibility and timing considerations
   - Confidence level in selector reliability

Output format:
{
    "target_url": "analyzed URL",
    "elements": {
        "element_name": {
            "selector": "primary CSS selector",
            "type": "element type",
            "description": "human readable description",
            "fallback_selectors": ["backup1", "backup2", "backup3"],
            "confidence": 0.0-1.0
        }
    },
    "recommendations": ["recommendation1", "recommendation2"],
    "timing_suggestions": {
        "page_load_wait": 300000,
        "element_wait": 180000,
        "action_delay": 3000
    }
}

Focus on elements that are commonly automated in web testing scenarios."""
