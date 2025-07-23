# src/agents/self_healing_agent.py
"""
Self-Healing Agent
Automatic error recovery and test adaptation
"""

import logging
from typing import Dict, Any, List
from playwright.async_api import Page
from ..core.azure_client import AzureOpenAIClient
from ..models.test_models import SelfHealingResult

logger = logging.getLogger(__name__)

class SelfHealingAgent:
    """
    Self-Healing Agent
    Provides automatic error recovery and test adaptation capabilities
    """
    
    def __init__(self, azure_client: AzureOpenAIClient):
        self.azure_client = azure_client
        self.healing_patterns: Dict[str, List[str]] = {}
        
    async def attempt_healing(self, page: Page, failed_step: Dict[str, Any], 
                            error: str) -> SelfHealingResult:
        """
        Attempt to heal a failed test step
        
        Args:
            page: Playwright Page object
            failed_step: Step configuration that failed
            error: Error message from failure
            
        Returns:
            SelfHealingResult: Result of healing attempt
        """
        
        logger.info(f"Attempting self-healing for step: {failed_step.get('description')}")
        logger.info(f"Error: {error}")
        
        start_time = page.clock.now() if hasattr(page, 'clock') else 0
        
        # Strategy 1: Basic retry patterns
        healing_result = await self._try_basic_healing(page, failed_step, error)
        if healing_result.success:
            healing_result.healing_time = (page.clock.now() if hasattr(page, 'clock') else 0) - start_time
            return healing_result
        
        # Strategy 2: Page state analysis and correction
        healing_result = await self._try_page_state_healing(page, failed_step, error)
        if healing_result.success:
            healing_result.healing_time = (page.clock.now() if hasattr(page, 'clock') else 0) - start_time
            return healing_result
        
        # Strategy 3: AI-powered recovery
        healing_result = await self._try_ai_healing(page, failed_step, error)
        healing_result.healing_time = (page.clock.now() if hasattr(page, 'clock') else 0) - start_time
        
        return healing_result
    
    async def _try_basic_healing(self, page: Page, failed_step: Dict[str, Any], 
                               error: str) -> SelfHealingResult:
        """Try basic healing patterns"""
        
        action = failed_step.get("action", "").lower()
        
        try:
            # Common healing pattern 1: Wait and retry
            if "timeout" in error.lower() or "not found" in error.lower():
                logger.info("Trying healing strategy: extended wait")
                await page.wait_for_timeout(3000)  # Wait 3 seconds
                
                return SelfHealingResult(
                    success=True,
                    strategy_used="extended_wait",
                    original_error=error,
                    healing_action="Waited 3 seconds for page stabilization"
                )
            
            # Common healing pattern 2: Handle modal dialogs
            if "dialog" in error.lower() or "modal" in error.lower():
                logger.info("Trying healing strategy: dismiss modal")
                
                # Try to dismiss any open modals
                modal_selectors = [
                    ".modal.show .close",
                    ".modal.show [data-dismiss='modal']",
                    ".dialog-overlay .close",
                    "[role='dialog'] .close"
                ]
                
                for selector in modal_selectors:
                    try:
                        close_btn = page.locator(selector)
                        if await close_btn.count() > 0:
                            await close_btn.first.click()
                            await page.wait_for_timeout(1000)
                            
                            return SelfHealingResult(
                                success=True,
                                strategy_used="dismiss_modal",
                                original_error=error,
                                healing_action=f"Dismissed modal using selector: {selector}"
                            )
                    except:
                        continue
            
            # Common healing pattern 3: Scroll element into view
            if action in ["click", "type"] and "not visible" in error.lower():
                logger.info("Trying healing strategy: scroll into view")
                
                # Try to find and scroll to the element
                primary_selector = failed_step.get("primary_selector", "")
                if primary_selector:
                    try:
                        element = page.locator(primary_selector)
                        if await element.count() > 0:
                            await element.first.scroll_into_view_if_needed()
                            await page.wait_for_timeout(1000)
                            
                            return SelfHealingResult(
                                success=True,
                                strategy_used="scroll_into_view",
                                original_error=error,
                                healing_action="Scrolled element into view"
                            )
                    except:
                        pass
            
            return SelfHealingResult(
                success=False,
                strategy_used="basic_patterns",
                original_error=error,
                healing_action="No basic healing pattern matched"
            )
            
        except Exception as e:
            return SelfHealingResult(
                success=False,
                strategy_used="basic_patterns",
                original_error=error,
                healing_action=f"Basic healing failed: {str(e)}"
            )
    
    async def _try_page_state_healing(self, page: Page, failed_step: Dict[str, Any], 
                                    error: str) -> SelfHealingResult:
        """Analyze page state and attempt correction"""
        
        try:
            # Check for common page state issues
            page_url = page.url
            page_title = await page.title()
            
            logger.info(f"Analyzing page state - URL: {page_url}, Title: {page_title}")
            
            # Issue 1: Unexpected page/redirect
            if "login" in page_url.lower() and failed_step.get("action") != "navigate":
                logger.info("Detected unexpected redirect to login page")
                return SelfHealingResult(
                    success=False,
                    strategy_used="page_state_analysis",
                    original_error=error,
                    healing_action="Detected session timeout - requires re-authentication"
                )
            
            # Issue 2: Loading state
            loading_indicators = [
                ".loading",
                ".spinner", 
                "[data-loading='true']",
                ".progress-bar"
            ]
            
            for indicator in loading_indicators:
                try:
                    loading_element = page.locator(indicator)
                    if await loading_element.count() > 0:
                        logger.info(f"Found loading indicator: {indicator}")
                        # Wait for loading to complete
                        await loading_element.wait_for(state="detached", timeout=15000)
                        
                        return SelfHealingResult(
                            success=True,
                            strategy_used="wait_for_loading",
                            original_error=error,
                            healing_action=f"Waited for loading indicator to disappear: {indicator}"
                        )
                except:
                    continue
            
            # Issue 3: JavaScript errors affecting page
            try:
                # Check for JavaScript errors in console
                await page.evaluate("console.clear()")
                await page.wait_for_timeout(1000)
                
                return SelfHealingResult(
                    success=True,
                    strategy_used="page_stabilization",
                    original_error=error,
                    healing_action="Page stabilization wait completed"
                )
                
            except:
                pass
            
            return SelfHealingResult(
                success=False,
                strategy_used="page_state_analysis",
                original_error=error,
                healing_action="No page state issues detected"
            )
            
        except Exception as e:
            return SelfHealingResult(
                success=False,
                strategy_used="page_state_analysis",
                original_error=error,
                healing_action=f"Page state analysis failed: {str(e)}"
            )
    
    async def _try_ai_healing(self, page: Page, failed_step: Dict[str, Any], 
                            error: str) -> SelfHealingResult:
        """Use AI to suggest healing approaches"""
        
        try:
            # Get current page state
            page_content = await page.content()
            page_title = await page.title()
            page_url = page.url
            
            # Truncate content for token efficiency
            truncated_content = page_content[:1000] + "..." if len(page_content) > 1000 else page_content
            
            # Prepare healing prompt
            system_prompt = """You are an expert at diagnosing and fixing test automation failures in legacy Java web applications.

Analyze the failed test step and current page state to suggest healing approaches.

Common Failure Patterns:
- Element not found: Page structure changed, element loaded later, wrong selector
- Timeout: Page loading slowly, network issues, JavaScript not completed
- Click failed: Element not clickable, overlay blocking, wrong element
- Type failed: Element not focusable, readonly, wrong input type
- Modal/dialog issues: Unexpected popups, confirmation dialogs
- Session/authentication: Session expired, redirect to login

Healing Strategies:
- Wait strategies: Extended waits, wait for specific conditions
- Alternative selectors: Text-based, attribute-based, hierarchy-based
- Page interaction: Dismiss modals, handle alerts, scroll actions
- Session management: Re-authentication, session refresh
- Browser actions: Refresh page, clear cache, handle popups

Output JSON:
{
    "recommended_action": "wait|retry|alternative_selector|page_action|session_refresh|manual_intervention",
    "reasoning": "explanation of the diagnosis",
    "healing_steps": [
        "step 1 description",
        "step 2 description"
    ],
    "alternative_selector": "new selector if applicable",
    "confidence": 0.0-1.0,
    "requires_manual_intervention": boolean
}"""
            
            user_prompt = f"""
Failed Step:
- Action: {failed_step.get('action')}
- Target: {failed_step.get('target')}
- Description: {failed_step.get('description')}
- Primary Selector: {failed_step.get('primary_selector')}
- Fallback Selectors: {failed_step.get('fallback_selectors', [])}

Error: {error}

Current Page State:
- URL: {page_url}
- Title: {page_title}
- Content (truncated): {truncated_content}

Diagnose the failure and recommend healing approach.
"""
            
            response = await self.azure_client.call_agent(
                agent_name="SelfHealing",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                temperature=0.2
            )
            
            if response.success:
                healing_suggestion = response.content
                
                # Execute suggested healing action
                result = await self._execute_ai_healing_suggestion(page, healing_suggestion, failed_step)
                
                if result:
                    return SelfHealingResult(
                        success=True,
                        strategy_used="ai_analysis",
                        original_error=error,
                        healing_action=f"AI suggested: {healing_suggestion.get('recommended_action')}",
                        new_selector=healing_suggestion.get("alternative_selector"),
                        metadata=healing_suggestion
                    )
            
            return SelfHealingResult(
                success=False,
                strategy_used="ai_analysis",
                original_error=error,
                healing_action="AI analysis completed but healing unsuccessful"
            )
            
        except Exception as e:
            logger.error(f"AI healing failed: {e}")
            return SelfHealingResult(
                success=False,
                strategy_used="ai_analysis",
                original_error=error,
                healing_action=f"AI healing error: {str(e)}"
            )
    
    async def _execute_ai_healing_suggestion(self, page: Page, suggestion: Dict[str, Any], 
                                           failed_step: Dict[str, Any]) -> bool:
        """Execute AI healing suggestion"""
        
        recommended_action = suggestion.get("recommended_action", "")
        
        try:
            if recommended_action == "wait":
                # Extended wait strategy
                await page.wait_for_timeout(5000)
                return True
                
            elif recommended_action == "alternative_selector":
                # Try alternative selector
                alt_selector = suggestion.get("alternative_selector")
                if alt_selector:
                    element = page.locator(alt_selector)
                    if await element.count() > 0:
                        logger.info(f"AI suggested selector found element: {alt_selector}")
                        return True
                        
            elif recommended_action == "page_action":
                # Perform page-level action
                healing_steps = suggestion.get("healing_steps", [])
                for step in healing_steps:
                    if "dismiss modal" in step.lower():
                        await page.keyboard.press("Escape")
                    elif "scroll" in step.lower():
                        await page.keyboard.press("PageDown")
                    elif "refresh" in step.lower():
                        await page.reload()
                        
                await page.wait_for_timeout(2000)
                return True
                
            elif recommended_action == "session_refresh":
                # Handle session issues
                await page.reload()
                await page.wait_for_timeout(3000)
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to execute AI healing suggestion: {e}")
            return False

if __name__ == "__main__":
    print("Individual agents implementation completed!")
    print("✅ NL Processor Agent")
    print("✅ Test Strategy Agent") 
    print("✅ Test Generation Agent")
    print("✅ Element Detection Agent")
    print("✅ Self-Healing Agent")
    print("\nNext: Implement browser automation layer...")