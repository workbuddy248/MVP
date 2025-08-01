# src/automation/test_executor.py - Updated to use Enhanced Browser Pool
"""
Enhanced Test Executor with Legacy Application Support
Integrates with the enhanced browser pool for robust Cisco Catalyst Centre testing
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from playwright.async_api import Page
from ..core.azure_client import AzureOpenAIClient
from ..models.test_models import (
    TestResults, StepExecutionResult, TestStatus, TestActionType, calculate_test_summary
)
from .browser_pool import BrowserPool
# from ..agents.self_healing_agent import SelfHealingAgent  # Temporarily disabled

logger = logging.getLogger(__name__)

class TestExecutor:
    """
    Enhanced Test Executor with Legacy Application Support
    Integrates with enhanced browser pool and provides robust timing for Cisco Catalyst Centre
    """
    
    def __init__(self, browser_config: Dict[str, Any], azure_client: AzureOpenAIClient):
        self.browser_config = browser_config
        self.azure_client = azure_client
        self.browser_pool = BrowserPool(browser_config)
        # self.self_healing_agent = SelfHealingAgent(azure_client)  # Temporarily disabled
        
        # Session management
        self._session_browser_context = None
        self._session_active = False
        
        # Legacy app specific settings
        self.legacy_app_ready = False
        self.initial_navigation_complete = False
        
        logger.info("TestExecutor initialized with enhanced legacy app support")
        
    async def execute_test_script(self, test_script: Dict[str, Any],
                                application_url: Optional[str] = None,
                                user_credentials: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Execute complete test script with enhanced legacy application support
        """
        
        logger.info(f"🚀 Executing test script: {test_script.get('test_name')}")
        
        test_results = TestResults(
            test_name=test_script.get("test_name", "Enhanced Legacy Test"),
            start_time=datetime.now().isoformat(),
            status=TestStatus.RUNNING
        )
        
        browser_context = None
        
        try:
            # Get or reuse browser context for the session
            if not self._session_active or not self._session_browser_context:
                await self._start_enhanced_browser_session()
            
            browser_context = self._session_browser_context
            page = browser_context.page
            
            # Enhanced navigation for legacy applications
            if application_url and not self.initial_navigation_complete:
                navigation_success = await self._enhanced_legacy_navigation(page, application_url)
                if not navigation_success:
                    raise Exception("Failed to properly navigate to legacy application")
                
                self.initial_navigation_complete = True
                self.legacy_app_ready = True
            
            # Execute setup steps if needed
            await self._execute_setup_steps(page, test_script.get("setup_steps", []))
            
            # Execute main test steps with enhanced timing
            test_steps = test_script.get("test_steps", [])
            await self._execute_enhanced_test_steps(page, test_steps, test_results)
            
            # Handle authentication if needed
            if user_credentials and self._requires_authentication(test_results):
                await self._handle_enhanced_authentication(page, user_credentials, test_results)
            
            # Execute cleanup steps
            await self._execute_cleanup_steps(page, test_script.get("cleanup_steps", []))
            
            # Calculate final results
            test_results.summary = calculate_test_summary(test_results.step_results)
            test_results.status = TestStatus.COMPLETED if test_results.summary.failed == 0 else TestStatus.FAILED
            
        except Exception as e:
            logger.error(f"❌ Enhanced test execution failed: {e}")
            test_results.status = TestStatus.ERROR
            test_results.error = str(e)
        
        finally:
            test_results.end_time = datetime.now().isoformat()
            
            # Don't close browser context - keep it alive for the session
            # Context will be closed when session ends or explicitly closed
        
        # Convert to dictionary for return
        return self._convert_results_to_dict(test_results)
    
    async def _start_enhanced_browser_session(self):
        """Start enhanced browser session with legacy application support"""
        logger.info("🚀 Starting enhanced browser session for legacy applications...")
        
        try:
            if not self.browser_pool.browser:
                await self.browser_pool.initialize()
            
            self._session_browser_context = await self.browser_pool.get_browser_context()
            self._session_active = True
            
            logger.info("✅ Enhanced browser session started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start enhanced browser session: {e}")
            self._session_active = False
            self._session_browser_context = None
            raise
    
    async def _enhanced_legacy_navigation(self, page: Page, url: str) -> bool:
        """Enhanced navigation specifically for legacy applications like Cisco Catalyst Centre"""
        
        logger.info(f"🌐 Enhanced legacy navigation to: {url}")
        
        try:
            # Use browser pool's enhanced navigation method
            navigation_success = await self.browser_pool.navigate_to_legacy_app(page, url)
            
            if navigation_success:
                logger.info("✅ Enhanced legacy navigation completed successfully")
                
                # Additional verification steps
                await self._verify_application_readiness(page)
                
                return True
            else:
                logger.error("❌ Enhanced legacy navigation failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Enhanced legacy navigation error: {e}")
            return False
    
    async def _verify_application_readiness(self, page: Page):
        """Verify that the legacy application is truly ready for interaction"""
        
        logger.info("🔍 Verifying application readiness...")
        
        try:
            # Check if page URL changed (indicating redirect occurred)
            current_url = page.url
            if '/auth/login' in current_url or '/login' in current_url:
                logger.info("🔄 Redirect to login page detected, skipping readiness verification to avoid context destruction")
                return
            
            # Use injected helpers to verify readiness
            is_ready = await page.evaluate("""
                async () => {
                    if (!window.legacyHelpers) {
                        return false;
                    }
                    
                    // Run all readiness checks
                    const catalystReady = await window.legacyHelpers.waitForCatalystCenter(60000);
                    const frameworkReady = await window.legacyHelpers.waitForFrameworkReady(30000);
                    const networkIdle = await window.legacyHelpers.waitForNetworkIdle(15000, 2000);
                    
                    return catalystReady && frameworkReady;
                }
            """)
            
            if is_ready:
                logger.info("✅ Application readiness verified successfully")
            else:
                logger.warning("⚠️ Application readiness check failed, but continuing")
                
        except Exception as e:
            error_msg = str(e)
            if "Execution context was destroyed" in error_msg:
                logger.info("🔄 Execution context destroyed during readiness check (likely due to redirect) - this is normal for legacy apps")
            else:
                logger.warning(f"⚠️ Application readiness verification error: {e}")
                
        logger.info("🚀 Proceeding with test execution...")
    
    async def _execute_enhanced_test_steps(self, page: Page, test_steps: list, test_results: TestResults):
        """Execute test steps with enhanced timing for legacy applications"""
        
        logger.info(f"🧪 Executing {len(test_steps)} enhanced test steps...")
        
        for step_config in test_steps:
            # Wait for application stability before each step
            if self.legacy_app_ready:
                await self._wait_for_legacy_app_stability(page)
            
            step_result = await self._execute_enhanced_single_step(page, step_config)
            test_results.step_results.append(step_result)
            
            # Stop execution on critical failures
            if step_result.status == TestStatus.FAILED and step_config.get("critical", False):
                logger.error(f"❌ Critical step failed: {step_config.get('description')}")
                break
            
            # Enhanced delay between steps for legacy apps
            await asyncio.sleep(3)  # 3 second delay between steps
    
    async def _wait_for_legacy_app_stability(self, page: Page):
        """Wait for legacy application to be stable before proceeding"""
        
        try:
            # Use injected helpers to check stability
            await page.evaluate("""
                async () => {
                    if (window.legacyHelpers) {
                        // Wait for any active requests to complete
                        await window.legacyHelpers.waitForNetworkIdle(5000, 1000);
                        
                        // Additional stability wait
                        await window.legacyHelpers.sleep(1000);
                    }
                }
            """)
            
        except Exception as e:
            logger.debug(f"Legacy app stability check: {e}")
    
    async def _execute_enhanced_single_step(self, page: Page, step_config: Dict[str, Any]) -> StepExecutionResult:
        """Execute a single test step with enhanced error handling and timing"""
        
        step_id = step_config.get("step_id", 0)
        action = TestActionType(step_config.get("action", "wait"))
        description = step_config.get("description", "")
        target = step_config.get("target", "")

        logger.info(f"🔧 Executing enhanced step {step_id}: {action.value} - {description}")
        
        step_result = StepExecutionResult(
            step_id=step_id,
            action=action,
            description=description,
            target=target,
            status=TestStatus.RUNNING,
            start_time=datetime.now().isoformat()
        )
        
        try:
            # Execute the step action with enhanced handling
            success = await self._perform_enhanced_step_action(page, step_config, step_result)
            
            if success:
                step_result.status = TestStatus.COMPLETED
                logger.info(f"✅ Enhanced step {step_id} completed successfully")
            else:
                step_result.status = TestStatus.FAILED
                step_result.error = "Enhanced action execution failed"
                
                # Self-healing temporarily disabled to avoid Clock errors
                # healing_result = await self.self_healing_agent.attempt_healing(
                #     page, step_config, step_result.error or "Unknown error"
                # )
                # 
                # if healing_result.success:
                #     step_result.healing_applied = True
                #     step_result.status = TestStatus.COMPLETED
                #     logger.info(f"✅ Enhanced step {step_id} healed successfully: {healing_result.strategy_used}")
                # else:
                #     logger.warning(f"⚠️ Enhanced step {step_id} failed and healing unsuccessful")
                
                logger.error(f"❌ Enhanced step {step_id} failed with error: {step_result.error}")
            
            # Take screenshot if requested or if step failed
            if step_config.get("screenshot_after", False) or step_result.status == TestStatus.FAILED:
                screenshot_path = await self._take_enhanced_screenshot(page, f"step_{step_id}")
                step_result.screenshot_path = screenshot_path
            
        except Exception as e:
            step_result.status = TestStatus.FAILED
            step_result.error = str(e)
            logger.error(f"❌ Enhanced step {step_id} failed with error: {e}")
            
            # Take error screenshot
            try:
                screenshot_path = await self._take_enhanced_screenshot(page, f"error_step_{step_id}")
                step_result.screenshot_path = screenshot_path
            except:
                pass
        
        finally:
            step_result.end_time = datetime.now().isoformat()
        
        return step_result
    
    async def _perform_enhanced_step_action(self, page: Page, step_config: Dict[str, Any], 
                                          step_result: StepExecutionResult) -> bool:
        """Perform step action with enhanced legacy application support"""
        
        action = TestActionType(step_config.get("action"))
        
        try:
            if action == TestActionType.NAVIGATE:
                # Try multiple sources for URL
                url = step_config.get("value", "") or step_config.get("primary_selector", "")
                
                # If URL is "N/A" or empty, try to extract from target description
                if not url or url == "N/A":
                    target = step_config.get("target", "")
                    # Extract URL from target description (e.g., "Login page at https://10.29.46.11/")
                    import re
                    url_match = re.search(r'https?://[^\s\)]+', target)
                    if url_match:
                        url = url_match.group(0)
                        logger.info(f"🔍 Extracted URL from target: {url}")
                
                if url and url != "N/A":
                    logger.info(f"🌐 Enhanced navigation to: {url}")
                    navigation_success = await self.browser_pool.navigate_to_legacy_app(page, url)
                    return navigation_success
                else:
                    step_result.error = "No valid URL found for enhanced navigation"
                    logger.error(f"❌ Navigation failed: No URL found in step config: {step_config}")
                    return False
            
            elif action == TestActionType.CLICK:
                return await self._enhanced_click_element(page, step_config, step_result)
            
            elif action == TestActionType.TYPE:
                return await self._enhanced_type_element(page, step_config, step_result)
            
            elif action == TestActionType.WAIT:
                # Enhanced wait with minimum legacy app timing
                wait_time = max(
                    int(step_config.get("timeout", 180000)),
                    int(step_config.get("value", 180000)),
                    180000  # Minimum 3 minutes for legacy apps
                )
                logger.info(f"⏱️ Enhanced wait for {wait_time}ms")
                await asyncio.sleep(wait_time / 1000)
                return True
            
            elif action == TestActionType.VERIFY:
                return await self._enhanced_verify_condition(page, step_config, step_result)
            
            elif action == TestActionType.SCREENSHOT:
                screenshot_path = await self._take_enhanced_screenshot(page, step_config.get("name", "screenshot"))
                step_result.screenshot_path = screenshot_path
                return True
            
            else:
                step_result.error = f"Unsupported enhanced action: {action}"
                return False
                
        except Exception as e:
            step_result.error = str(e)
            return False
    
    async def _enhanced_click_element(self, page: Page, step_config: Dict[str, Any], 
                                    step_result: StepExecutionResult) -> bool:
        """Enhanced click with legacy application timing and stability"""
        
        try:
            # Wait for application stability
            await self._wait_for_legacy_app_stability(page)
            
            # Use direct selector from step config
            selector = step_config.get('primary_selector') or step_config.get('target', '')
            if not selector:
                step_result.error = "No selector provided for click action"
                return False
                
            element = page.locator(selector)
            
            # Enhanced waiting and interaction for legacy apps
            await element.wait_for(state="visible", timeout=300000)  # 5 minutes
            
            # Use injected helpers to ensure element stability
            await page.evaluate(f"""
                async (selector) => {{
                    if (window.legacyHelpers) {{
                        await window.legacyHelpers.waitForStable(selector, 10000);
                        window.legacyHelpers.scrollToElement(selector);
                        await window.legacyHelpers.sleep(2000);
                    }}
                }}
            """, selector)
            
            # Perform the click with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await element.first.click(timeout=180000, force=True)
                    logger.info(f"✅ Enhanced click successful on attempt {attempt + 1}")
                    
                    # Wait for any resulting page changes
                    await asyncio.sleep(3)
                    await self._wait_for_legacy_app_stability(page)
                    
                    step_result.selector_used = selector
                    return True
                        
                except Exception as click_error:
                    logger.warning(f"⚠️ Enhanced click attempt {attempt + 1} failed: {click_error}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                    else:
                        step_result.error = f"Enhanced click failed after {max_retries} attempts: {click_error}"
                        return False
                
        except Exception as e:
            step_result.error = f"Enhanced click error: {str(e)}"
            return False
    
    async def _enhanced_type_element(self, page: Page, step_config: Dict[str, Any], 
                                   step_result: StepExecutionResult) -> bool:
        """Enhanced typing with legacy application support"""
        
        try:
            # Wait for application stability
            await self._wait_for_legacy_app_stability(page)
            
            # Use direct selector from step config
            selector = step_config.get('primary_selector') or step_config.get('target', '')
            if not selector:
                step_result.error = "No selector provided for type action"
                return False
                
            element = page.locator(selector)
            value = step_config.get("value", "")
            
            # Enhanced waiting and interaction
            await element.wait_for(state="visible", timeout=300000)  # 5 minutes
            
            # Use injected helpers for stability
            await page.evaluate(f"""
                async (selector) => {{
                    if (window.legacyHelpers) {{
                        await window.legacyHelpers.waitForStable(selector, 10000);
                        window.legacyHelpers.scrollToElement(selector);
                        await window.legacyHelpers.sleep(1000);
                    }}
                }}
            """, selector)
            
            # Clear and type with enhanced timing
            await element.first.clear()
            await asyncio.sleep(1)  # Wait after clear
            await element.first.type(value, delay=200)  # Slower typing for legacy apps
            await asyncio.sleep(2)  # Wait after typing
            
            step_result.selector_used = selector
            logger.info(f"✅ Enhanced typing completed: '{value}'")
            return True
                
        except Exception as e:
            step_result.error = f"Enhanced typing error: {str(e)}"
            return False
    
    async def _enhanced_verify_condition(self, page: Page, step_config: Dict[str, Any], 
                                       step_result: StepExecutionResult) -> bool:
        """Enhanced verification with legacy application timing"""
        
        verification = step_config.get("verification", "")
        target = step_config.get("target", "")
        
        try:
            # Wait for application stability before verification
            await self._wait_for_legacy_app_stability(page)
            
            # Enhanced text presence verification
            if "text" in verification.lower():
                # Wait longer for text to appear in legacy apps
                try:
                    await page.wait_for_function(
                        f"document.body.textContent.toLowerCase().includes('{target.lower()}')",
                        timeout=180000  # 3 minutes
                    )
                    logger.info(f"✅ Enhanced text verification successful: '{target}'")
                    return True
                except:
                    step_result.error = f"Enhanced text verification failed: {target}"
                    return False
            
            # Enhanced element presence verification
            elif "element" in verification.lower():
                # Use direct selector from step config
                selector = step_config.get('primary_selector') or step_config.get('target', '')
                if not selector:
                    step_result.error = "No selector provided for element verification"
                    return False
                    
                # Additional stability check for found element
                try:
                    await page.wait_for_selector(selector, state="visible", timeout=180000)
                    logger.info(f"✅ Enhanced element verification successful: {target}")
                    return True
                except:
                    step_result.error = f"Enhanced element verification failed (not visible): {target}"
                    return False
            
            # Enhanced URL verification
            elif "url" in verification.lower():
                # Wait for navigation to complete in legacy apps
                await asyncio.sleep(5)  # Additional wait for URL changes
                current_url = page.url
                if target.lower() in current_url.lower():
                    logger.info(f"✅ Enhanced URL verification successful: {target}")
                    return True
                else:
                    step_result.error = f"Enhanced URL verification failed. Expected: {target}, Got: {current_url}"
                    return False
            
            else:
                # Generic verification with enhanced timing
                await asyncio.sleep(3)  # Additional wait for legacy apps
                page_content = await page.content()
                result = target.lower() in page_content.lower()
                if result:
                    logger.info(f"✅ Enhanced generic verification successful: {target}")
                else:
                    step_result.error = f"Enhanced generic verification failed: {target}"
                return result
                
        except Exception as e:
            step_result.error = f"Enhanced verification failed: {str(e)}"
            return False
    
    async def _take_enhanced_screenshot(self, page: Page, name: str) -> str:
        """Take enhanced screenshot with legacy application context"""
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"enhanced_{name}_{timestamp}.png"
            filepath = f"screenshots/{filename}"
            
            # Ensure screenshots directory exists
            import os
            os.makedirs("screenshots", exist_ok=True)
            
            # Wait for page stability before screenshot
            await self._wait_for_legacy_app_stability(page)
            await asyncio.sleep(2)  # Additional wait for visual stability
            
            await page.screenshot(path=filepath, full_page=True)
            logger.info(f"📸 Enhanced screenshot saved: {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"❌ Enhanced screenshot failed: {e}")
            return ""
    
    async def _handle_enhanced_authentication(self, page: Page, credentials: Dict[str, str], 
                                            test_results: TestResults):
        """Enhanced authentication handling for legacy applications"""
        
        logger.info("🔐 Attempting enhanced authentication...")
        
        try:
            username = credentials.get("username", "")
            password = credentials.get("password", "")
            
            # Enhanced selectors for Cisco Catalyst Centre
            username_selectors = [
                "input[name='username']",
                "input[name='user']", 
                "input[name='login']",
                "input[type='text']",
                "#username",
                "#user",
                "[data-automation='username']",
                "[data-testid='username']"
            ]
            
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "#password",
                "[data-automation='password']",
                "[data-testid='password']"
            ]
            
            login_button_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Login')",
                "button:has-text('Sign In')",
                "#login-btn",
                ".login-button",
                "[data-automation='login']",
                "[data-testid='login']"
            ]
            
            # Wait for login page to be fully ready
            await self._wait_for_legacy_app_stability(page)
            await asyncio.sleep(5)  # Additional wait for login page
            
            # Enhanced username entry
            username_success = False
            for selector in username_selectors:
                try:
                    username_field = page.locator(selector)
                    if await username_field.count() > 0:
                        await username_field.wait_for(state="visible", timeout=180000)
                        await username_field.first.clear()
                        await asyncio.sleep(1)
                        await username_field.first.type(username, delay=200)
                        await asyncio.sleep(2)
                        username_success = True
                        logger.info(f"✅ Enhanced username entry successful with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Username selector failed: {selector} - {e}")
                    continue
            
            if not username_success:
                raise Exception("Failed to enter username with any selector")
            
            # Enhanced password entry
            password_success = False
            for selector in password_selectors:
                try:
                    password_field = page.locator(selector)
                    if await password_field.count() > 0:
                        await password_field.wait_for(state="visible", timeout=180000)
                        await password_field.first.clear()
                        await asyncio.sleep(1)
                        await password_field.first.type(password, delay=200)
                        await asyncio.sleep(2)
                        password_success = True
                        logger.info(f"✅ Enhanced password entry successful with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Password selector failed: {selector} - {e}")
                    continue
            
            if not password_success:
                raise Exception("Failed to enter password with any selector")
            
            # Enhanced login button click
            login_success = False
            for selector in login_button_selectors:
                try:
                    login_button = page.locator(selector)
                    if await login_button.count() > 0:
                        await login_button.wait_for(state="visible", timeout=180000)
                        await asyncio.sleep(2)  # Wait before click
                        await login_button.first.click(timeout=180000, force=True)
                        login_success = True
                        logger.info(f"✅ Enhanced login click successful with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Login button selector failed: {selector} - {e}")
                    continue
            
            if not login_success:
                raise Exception("Failed to click login button with any selector")
            
            # Enhanced wait for authentication to complete
            logger.info("⏱️ Waiting for enhanced authentication to complete...")
            await asyncio.sleep(10)  # Initial wait
            await self._wait_for_legacy_app_stability(page)
            await asyncio.sleep(5)   # Additional stability wait
            
            logger.info("✅ Enhanced authentication attempt completed")
            
        except Exception as e:
            logger.error(f"❌ Enhanced authentication failed: {e}")
            raise Exception(f"Enhanced authentication failed: {e}")
    
    # ... (keeping existing methods for compatibility)
    
    async def end_browser_session(self):
        """End the current enhanced browser session"""
        if self._session_browser_context and self._session_active:
            logger.info("🔄 Ending enhanced browser session...")
            await self.browser_pool.close_context(self._session_browser_context)
            self._session_browser_context = None
            self._session_active = False
            self.legacy_app_ready = False
            self.initial_navigation_complete = False
            logger.info("✅ Enhanced browser session ended")
    
    async def get_session_page(self):
        """Get the current session page for additional operations"""
        if self._session_active and self._session_browser_context:
            return self._session_browser_context.page
        return None
    
    def _convert_results_to_dict(self, test_results: TestResults) -> Dict[str, Any]:
        """Convert TestResults to dictionary for JSON serialization"""
        
        return {
            "test_name": test_results.test_name,
            "start_time": test_results.start_time,
            "end_time": test_results.end_time,
            "status": test_results.status.value,
            "step_results": [
                {
                    "step_id": step.step_id,
                    "action": step.action.value,
                    "description": step.description,
                    "target": step.target,
                    "status": step.status.value,
                    "start_time": step.start_time,
                    "end_time": step.end_time,
                    "error": step.error,
                    "screenshot_path": step.screenshot_path,
                    "selector_used": step.selector_used,
                    "retry_count": step.retry_count,
                    "healing_applied": step.healing_applied
                }
                for step in test_results.step_results
            ],
            "summary": {
                "total_steps": test_results.summary.total_steps,
                "passed": test_results.summary.passed,
                "failed": test_results.summary.failed,
                "skipped": test_results.summary.skipped,
                "success_rate": test_results.summary.success_rate,
                "total_duration": test_results.summary.total_duration,
                "average_step_duration": test_results.summary.average_step_duration,
                "healing_success_rate": test_results.summary.healing_success_rate
            } if test_results.summary else {},
            "screenshots": test_results.screenshots,
            "logs": test_results.logs,
            "performance_metrics": test_results.performance_metrics,
            "error": test_results.error
        }
    
    # Keep existing workflow execution methods
    async def execute_workflow_template(self, workflow_template: Dict[str, Any],
                                       field_values: Dict[str, Any],
                                       application_url: Optional[str] = None) -> Dict[str, Any]:
        """Execute workflow template with enhanced legacy application support"""
        logger.info(f"🔄 Executing enhanced workflow: {workflow_template.get('workflow_name', 'Unknown')}")
        
        execution_results = {
            "workflow_id": workflow_template.get("workflow_id"),
            "workflow_name": workflow_template.get("workflow_name"),
            "status": "executing",
            "steps_completed": 0,
            "total_steps": len(workflow_template.get("steps", [])),
            "step_results": [],
            "screenshots": [],
            "error": None,
            "start_time": datetime.now().isoformat()
        }
        
        try:
            # Get or start enhanced browser session
            if not self._session_active:
                await self._start_enhanced_browser_session()
            
            page = self._session_browser_context.page
            
            # Enhanced navigation if URL provided
            if application_url:
                navigation_success = await self._enhanced_legacy_navigation(page, application_url)
                if not navigation_success:
                    raise Exception("Enhanced workflow navigation failed")
                
                # Take initial screenshot
                screenshot = await page.screenshot(full_page=True)
                execution_results["screenshots"].append({
                    "step": "enhanced_initial_navigation",
                    "timestamp": datetime.now().isoformat(),
                    "data": screenshot
                })
            
            # Execute workflow steps with enhanced timing
            for step_index, step in enumerate(workflow_template.get("steps", [])):
                step_result = await self._execute_enhanced_workflow_step(
                    page, step, field_values, step_index + 1
                )
                
                execution_results["step_results"].append(step_result)
                execution_results["steps_completed"] += 1
                
                # If step failed and is critical, stop execution
                if step_result["status"] == "failed" and step.get("critical", True):
                    execution_results["status"] = "failed" 
                    execution_results["error"] = step_result.get("error", "Critical step failed")
                    break
                    
                # Take screenshot after each step
                screenshot = await page.screenshot(full_page=True)
                execution_results["screenshots"].append({
                    "step": f"enhanced_step_{step_index + 1}",
                    "timestamp": datetime.now().isoformat(),
                    "data": screenshot
                })
                
                # Enhanced wait between steps for legacy apps
                await asyncio.sleep(3)
            
            if execution_results["status"] != "failed":
                execution_results["status"] = "completed"
                
        except Exception as e:
            logger.error(f"❌ Enhanced workflow execution failed: {e}")
            execution_results["status"] = "failed"
            execution_results["error"] = str(e)
            
            if self._session_browser_context and self._session_browser_context.page:
                try:
                    screenshot = await self._session_browser_context.page.screenshot(full_page=True)
                    execution_results["screenshots"].append({
                        "step": "enhanced_error_screenshot",
                        "timestamp": datetime.now().isoformat(),
                        "data": screenshot
                    })
                except:
                    pass
                    
        finally:
            execution_results["end_time"] = datetime.now().isoformat()
            
        return execution_results

    async def _execute_enhanced_workflow_step(self, page: Page, step: Dict[str, Any], 
                                            field_values: Dict[str, Any], step_number: int) -> Dict[str, Any]:
        """Execute a single workflow step with enhanced legacy application support"""
        step_result = {
            "step_number": step_number,
            "step_id": step.get("step_id", step_number),
            "action": step.get("action"),
            "description": step.get("description"),
            "status": "executing", 
            "start_time": datetime.now().isoformat(),
            "error": None,
            "healing_applied": False
        }
        
        try:
            # Wait for application stability before each workflow step
            await self._wait_for_legacy_app_stability(page)
            
            action = step.get("action")
            
            if action == "navigate_to_hierarchy":
                await self._navigate_to_network_hierarchy(page)
            elif action == "check_area_exists":
                exists = await self._check_area_exists(page, field_values.get("area_name"))
                step_result["area_exists"] = exists
            elif action == "create_area" and step.get("conditional") == "if_area_not_exists":
                if not step_result.get("area_exists", True):
                    await self._create_area(page, field_values.get("area_name"))
            elif action == "expand_global":
                await self._expand_global_node(page)
            elif action == "check_building_exists":
                exists = await self._check_building_exists(page, field_values.get("building_name"))
                step_result["building_exists"] = exists  
            elif action == "create_building" and step.get("conditional") == "if_building_not_exists":
                if not step_result.get("building_exists", True):
                    await self._create_building(page, field_values.get("building_name"), 
                                              field_values.get("address", "Sanjose"))
            elif action == "verify_hierarchy":
                await self._verify_hierarchy_structure(page, field_values.get("area_name"), 
                                                     field_values.get("building_name"))
            # Add other workflow actions as needed
            else:
                await self._handle_enhanced_generic_step(page, step, field_values)
                
            step_result["status"] = "passed"
            
        except Exception as e:
            logger.error(f"❌ Enhanced workflow step {step_number} failed: {e}")
            step_result["status"] = "failed"
            step_result["error"] = str(e)
            
        step_result["end_time"] = datetime.now().isoformat()
        return step_result

    async def _navigate_to_network_hierarchy(self, page: Page):
        """Enhanced navigation to Network Hierarchy page"""
        # Wait for app stability
        await self._wait_for_legacy_app_stability(page)
        
        # Click hamburger menu with enhanced timing
        await page.wait_for_selector("button[data-testid='hamburger-menu'], .menu-toggle, .nav-toggle", 
                                    timeout=300000)
        await page.click("button[data-testid='hamburger-menu'], .menu-toggle, .nav-toggle")
        await asyncio.sleep(3)  # Enhanced wait
        
        # Click Design menu
        await page.wait_for_selector("a:has-text('Design'), button:has-text('Design')", timeout=300000)
        await page.click("a:has-text('Design'), button:has-text('Design')")
        await asyncio.sleep(3)  # Enhanced wait
        
        # Click Network Hierarchy
        await page.wait_for_selector("a:has-text('Network Hierarchy'), button:has-text('Network Hierarchy')", 
                                    timeout=300000)
        await page.click("a:has-text('Network Hierarchy'), button:has-text('Network Hierarchy')")
        await page.wait_for_load_state("networkidle", timeout=300000)
        
        # Enhanced verification with longer timeout
        await page.wait_for_selector(":has-text('Global')", timeout=300000)
        await self._wait_for_legacy_app_stability(page)

    async def _check_area_exists(self, page: Page, area_name: str) -> bool:
        """Enhanced check if area exists under Global"""
        try:
            await self._wait_for_legacy_app_stability(page)
            area_selector = f".hierarchy-node:has-text('{area_name}'), [data-testid*='{area_name}']"
            await page.wait_for_selector(area_selector, timeout=10000)
            return True
        except:
            return False

    async def _create_area(self, page: Page, area_name: str):
        """Enhanced create new area under Global"""
        await self._wait_for_legacy_app_stability(page)
        
        # Find and click overflow menu for Global with enhanced timing
        await page.wait_for_selector("[data-testid='global-overflow'], .overflow-menu:near(.hierarchy-node:has-text('Global'))", 
                                    timeout=300000)
        await page.click("[data-testid='global-overflow'], .overflow-menu:near(.hierarchy-node:has-text('Global'))")
        await asyncio.sleep(3)
        
        # Click Add Area
        await page.wait_for_selector("button:has-text('Add Area'), [data-testid='add-area-btn']", 
                                    timeout=300000)
        await page.click("button:has-text('Add Area'), [data-testid='add-area-btn']")
        await asyncio.sleep(3)
        
        # Enter area name with enhanced timing
        await page.wait_for_selector("input[name*='area'], input[placeholder*='area'], input[data-testid*='area-name']", 
                                    timeout=300000)
        await page.fill("input[name*='area'], input[placeholder*='area'], input[data-testid*='area-name']", area_name)
        await asyncio.sleep(2)
        
        # Click Add button
        await page.wait_for_selector("button:has-text('Add'), button[data-testid='add-btn'], button[type='submit']", 
                                    timeout=300000)
        await page.click("button:has-text('Add'), button[data-testid='add-btn'], button[type='submit']")
        
        # Enhanced wait for confirmation
        await page.wait_for_selector(":has-text('Area Added Successfully'), :has-text('Successfully created area')", 
                                    timeout=300000)
        await self._wait_for_legacy_app_stability(page)

    async def _expand_global_node(self, page: Page):
        """Enhanced expand Global node to show areas"""
        try:
            await self._wait_for_legacy_app_stability(page)
            await page.wait_for_selector(".expand-arrow:near(.hierarchy-node:has-text('Global')), [data-testid='expand-global']", 
                                        timeout=300000)
            await page.click(".expand-arrow:near(.hierarchy-node:has-text('Global')), [data-testid='expand-global']")
            await asyncio.sleep(3)
        except:
            # Already expanded or different structure
            pass

    async def _check_building_exists(self, page: Page, building_name: str) -> bool:
        """Enhanced check if building already exists"""
        try:
            await self._wait_for_legacy_app_stability(page)
            building_selector = f".hierarchy-node:has-text('{building_name}'), [data-testid*='{building_name}']"
            await page.wait_for_selector(building_selector, timeout=10000)
            return True
        except:
            return False

    async def _create_building(self, page: Page, building_name: str, address: str):
        """Enhanced create new building under area"""
        await self._wait_for_legacy_app_stability(page)
        
        # Find and click overflow menu for area with enhanced selectors
        await page.wait_for_selector(f".overflow-menu:near(.hierarchy-node:has-text('{building_name}'))", 
                                    timeout=300000)
        await page.click(f".overflow-menu:near(.hierarchy-node:has-text('{building_name}'))")
        await asyncio.sleep(3)
        
        # Click Add Building
        await page.wait_for_selector("button:has-text('Add Building'), [data-testid='add-building-btn']", 
                                    timeout=300000)
        await page.click("button:has-text('Add Building'), [data-testid='add-building-btn']")
        await asyncio.sleep(3)
        
        # Enter building name
        await page.wait_for_selector("input[name*='building'], input[placeholder*='building'], input[data-testid*='building-name']", 
                                    timeout=300000)
        await page.fill("input[name*='building'], input[placeholder*='building'], input[data-testid*='building-name']", building_name)
        await asyncio.sleep(2)
        
        # Enter address if provided
        if address:
            await page.wait_for_selector("input[name*='address'], input[placeholder*='address'], input[data-testid*='address']", 
                                        timeout=300000)
            await page.fill("input[name*='address'], input[placeholder*='address'], input[data-testid*='address']", address)
            await asyncio.sleep(2)
            
            # Select first dropdown option with enhanced timing
            try:
                await page.wait_for_selector(".dropdown-item:first, .suggestion-item:first", timeout=30000)
                await page.click(".dropdown-item:first, .suggestion-item:first")
                await asyncio.sleep(2)
            except:
                pass  # Address suggestions may not appear
        
        # Click Add button
        await page.wait_for_selector("button:has-text('Add'), button[data-testid='add-btn'], button[type='submit']", 
                                    timeout=300000)
        await page.click("button:has-text('Add'), button[data-testid='add-btn'], button[type='submit']")
        
        # Enhanced wait for confirmation
        await page.wait_for_selector(":has-text('Site Added Successfully'), :has-text('Building created successfully')", 
                                    timeout=300000)
        await self._wait_for_legacy_app_stability(page)

    async def _verify_hierarchy_structure(self, page: Page, area_name: str, building_name: str):
        """Enhanced verify the complete hierarchy structure"""
        await self._wait_for_legacy_app_stability(page)
        
        # Check that all elements exist with enhanced timeouts
        await page.wait_for_selector(".hierarchy-node:has-text('Global')", timeout=300000)
        await page.wait_for_selector(f".hierarchy-node:has-text('{area_name}')", timeout=300000)
        await page.wait_for_selector(f".hierarchy-node:has-text('{building_name}')", timeout=300000)
        
        logger.info(f"✅ Enhanced hierarchy verification completed: Global → {area_name} → {building_name}")

    async def _handle_enhanced_generic_step(self, page: Page, step: Dict[str, Any], field_values: Dict[str, Any]):
        """Enhanced handle generic workflow steps"""
        action = step.get("action")
        selector = step.get("selector", "")
        value = step.get("value")
        
        # Replace placeholders in selector and value
        if selector and "{{" in selector:
            for field_key, field_value in field_values.items():
                selector = selector.replace(f"{{{{{field_key}}}}}", str(field_value))
        
        if value and "{{" in str(value):
            for field_key, field_value in field_values.items():
                value = str(value).replace(f"{{{{{field_key}}}}}", str(field_value))
        
        await self._wait_for_legacy_app_stability(page)
        
        if action == "click":
            await page.wait_for_selector(selector, timeout=300000)
            await page.click(selector)
            await asyncio.sleep(3)  # Enhanced pause after clicks
            
        elif action == "verify":
            # Enhanced wait for element to be visible for verification
            await page.wait_for_selector(selector, timeout=300000)
            
        elif action == "screenshot":
            # Take screenshot with custom name if provided
            screenshot_name = value or f"step_{step.get('step_id', 'unknown')}"
            await self._take_enhanced_screenshot(page, screenshot_name)
            
        elif action == "type":
            field_value = field_values.get(value, value) if value else ""
            await page.wait_for_selector(selector, timeout=300000)
            await page.fill(selector, str(field_value))
            await asyncio.sleep(2)  # Enhanced pause after typing
            
        elif action == "wait":
            timeout = step.get("timeout", 3000)
            await asyncio.sleep(timeout / 1000)

    async def _execute_setup_steps(self, page: Page, setup_steps: list):
        """Execute browser setup steps"""
        logger.info("🔧 Executing enhanced setup steps...")
        
        for step in setup_steps:
            try:
                action = step.get("action", "")
                config = step.get("config", {})
                
                if action == "browser_init":
                    # Browser initialization already handled by enhanced browser pool
                    logger.info("✅ Enhanced browser initialization completed")
                
                elif action == "set_viewport":
                    viewport = config.get("viewport", {"width": 1920, "height": 1080})
                    await page.set_viewport_size(viewport["width"], viewport["height"])
                    logger.info(f"✅ Enhanced viewport set: {viewport}")
                
                # Add other setup actions as needed
                
            except Exception as e:
                logger.warning(f"⚠️ Enhanced setup step failed: {step} - {e}")

    def _requires_authentication(self, test_results: TestResults) -> bool:
        """Check if authentication is required based on current results"""
        
        # Simple heuristic: if we see login-related failures or redirects
        for step_result in test_results.step_results:
            if step_result.error and "login" in step_result.error.lower():
                return True
        
        return False

    async def _execute_cleanup_steps(self, page: Page, cleanup_steps: list):
        """Execute cleanup steps"""
        logger.info("🧹 Executing enhanced cleanup steps...")
        
        for step in cleanup_steps:
            try:
                action = step.get("action", "")
                
                if action == "screenshot":
                    name = step.get("name", "final_cleanup")
                    await self._take_enhanced_screenshot(page, name)
                
                elif action == "browser_close":
                    # Browser will be closed by enhanced browser pool
                    logger.info("Enhanced browser close requested - will be handled by browser pool")
                
                # Add other cleanup actions as needed
                
            except Exception as e:
                logger.warning(f"⚠️ Enhanced cleanup step failed: {step} - {e}")

if __name__ == "__main__":
    print("Enhanced Browser automation layer implementation completed!")
    print("✅ Enhanced Browser Pool Management")
    print("✅ Enhanced Test Executor with Legacy App Support")
    print("✅ Cisco Catalyst Centre Optimizations")
    print("\nNext: Implement simplified report generator...")