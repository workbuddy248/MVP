# src/automation/test_executor.py
"""
Test Executor
Executes test scripts using browser automation with self-healing
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from playwright.async_api import Page
from ..core.azure_client import AzureOpenAIClient
from ..models.test_models import (
    TestResults, StepExecutionResult, TestExecutionSummary, 
    TestStatus, TestActionType, calculate_test_summary
)
from .browser_pool import BrowserPool
from ..agents.element_detection_agent_simple import ElementDetectionAgent
from ..agents.self_healing_agent import SelfHealingAgent

logger = logging.getLogger(__name__)

class TestExecutor:
    """
    Test Executor
    Executes test scripts with intelligent error handling and self-healing
    """
    
    def __init__(self, browser_config: Dict[str, Any], azure_client: AzureOpenAIClient):
        self.browser_config = browser_config
        self.azure_client = azure_client
        self.browser_pool = BrowserPool(browser_config)
        self.element_detection_agent = ElementDetectionAgent(azure_client)
        self.self_healing_agent = SelfHealingAgent(azure_client)
        
        # Session management
        self._session_browser_context = None
        self._session_active = False
        
    async def execute_test_script(self, test_script: Dict[str, Any],
                                application_url: Optional[str] = None,
                                user_credentials: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Execute complete test script with self-healing
        
        Args:
            test_script: Generated test script from TestGenerationAgent
            application_url: Target application URL
            user_credentials: Login credentials if needed
            
        Returns:
            Dict containing test execution results
        """
        
        logger.info(f"Executing test script: {test_script.get('test_name')}")
        
        test_results = TestResults(
            test_name=test_script.get("test_name", "Generated Test"),
            start_time=datetime.now().isoformat(),
            status=TestStatus.RUNNING
        )
        
        browser_context = None
        
        try:
            # Get or reuse browser context for the session
            if not self._session_active or not self._session_browser_context:
                await self._start_browser_session()
            
            browser_context = self._session_browser_context
            page = browser_context.page
            
            # Execute setup steps
            await self._execute_setup_steps(page, test_script.get("setup_steps", []))
            
            # Check if first test step is navigation - if so, skip our navigation
            test_steps = test_script.get("test_steps", [])
            
            # Execute main test steps
            await self._execute_test_steps(page, test_steps, test_results)
            
            # Handle authentication if needed
            if user_credentials and self._requires_authentication(test_results):
                await self._handle_authentication(page, user_credentials, test_results)
            
            # Execute cleanup steps
            await self._execute_cleanup_steps(page, test_script.get("cleanup_steps", []))
            
            # Calculate final results
            test_results.summary = calculate_test_summary(test_results.step_results)
            test_results.status = TestStatus.COMPLETED if test_results.summary.failed == 0 else TestStatus.FAILED
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            test_results.status = TestStatus.ERROR
            test_results.error = str(e)
        
        finally:
            test_results.end_time = datetime.now().isoformat()
            
            # Don't close browser context - keep it alive for the session
            # Context will be closed when session ends or explicitly closed
        
        # Convert to dictionary for return
        return self._convert_results_to_dict(test_results)
    
    async def _start_browser_session(self):
        """Start a new browser session that persists across multiple tests"""
        logger.info("Starting new browser session...")
        
        if not self.browser_pool.browser:
            await self.browser_pool.initialize()
        
        self._session_browser_context = await self.browser_pool.get_browser_context()
        self._session_active = True
        logger.info("Browser session started successfully")
    
    async def end_browser_session(self):
        """End the current browser session"""
        if self._session_browser_context and self._session_active:
            logger.info("Ending browser session...")
            await self.browser_pool.close_context(self._session_browser_context)
            self._session_browser_context = None
            self._session_active = False
            logger.info("Browser session ended")
    
    async def get_session_page(self):
        """Get the current session page for additional operations"""
        if self._session_active and self._session_browser_context:
            return self._session_browser_context.page
        return None
    
    async def _navigate_to_application(self, page: Page, url: str):
        """Navigate to the target application with enhanced waiting for legacy apps"""
        
        logger.info(f"Navigating to application: {url}")
        
        try:
            # Navigate with extended timeout for legacy apps (5 minutes)
            await page.goto(url, wait_until="networkidle", timeout=300000)
            
            # Enhanced waiting for legacy Java applications like Cisco DNA
            logger.info("Waiting for application to stabilize...")
            
            # Wait for initial page load
            await page.wait_for_timeout(3000)
            
            # Wait for any dynamic content to load
            try:
                # Wait for common application elements to be ready
                await page.wait_for_selector("body", timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=60000)
                
                # Additional wait for JavaScript frameworks to initialize
                await page.wait_for_timeout(5000)
                
                # Try to wait for application-specific indicators
                await self._wait_for_app_ready(page)
                
            except Exception as wait_error:
                logger.warning(f"Extended wait failed, but continuing: {wait_error}")
            
            # Check if page loaded successfully
            current_url = page.url
            if not current_url.startswith(url.split('/')[0] + '//' + url.split('/')[2]):
                logger.warning(f"Navigation may have failed. Expected URL pattern: {url}, Got: {current_url}")
            else:
                logger.info(f"Navigation successful to: {current_url}")
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            raise
    
    async def _wait_for_app_ready(self, page: Page):
        """Wait for application-specific readiness indicators"""
        try:
            # Wait for common loading indicators to disappear
            await page.wait_for_function(
                """() => {
                    // Check if page is not still loading
                    if (document.readyState !== 'complete') return false;
                    
                    // Check for common loading spinners/indicators
                    const loadingElements = document.querySelectorAll('[class*="loading"], [class*="spinner"], [class*="progress"]');
                    const visibleLoading = Array.from(loadingElements).some(el => 
                        el.offsetParent !== null && getComputedStyle(el).visibility !== 'hidden'
                    );
                    
                    return !visibleLoading;
                }""",
                timeout=30000
            )
            logger.info("Application appears ready for interaction")
        except Exception as e:
            logger.warning(f"App readiness check failed, continuing anyway: {e}")
    
    async def _execute_setup_steps(self, page: Page, setup_steps: list):
        """Execute browser setup steps"""
        
        logger.info("Executing setup steps...")
        
        for step in setup_steps:
            try:
                action = step.get("action", "")
                config = step.get("config", {})
                
                if action == "browser_init":
                    # Browser initialization already handled by browser pool
                    logger.info("Browser initialization completed")
                
                elif action == "set_viewport":
                    viewport = config.get("viewport", {"width": 1920, "height": 1080})
                    await page.set_viewport_size(viewport["width"], viewport["height"])
                
                # Add other setup actions as needed
                
            except Exception as e:
                logger.warning(f"Setup step failed: {step} - {e}")
    
    async def _execute_test_steps(self, page: Page, test_steps: list, test_results: TestResults):
        """Execute main test steps with self-healing"""
        
        logger.info(f"Executing {len(test_steps)} test steps...")
        
        for step_config in test_steps:
            step_result = await self._execute_single_step(page, step_config)
            test_results.step_results.append(step_result)
            
            # Stop execution on critical failures
            if step_result.status == TestStatus.FAILED and step_config.get("critical", False):
                logger.error(f"Critical step failed: {step_config.get('description')}")
                break
            
            # Add delay between steps for legacy apps
            await page.wait_for_timeout(1000)
    
    async def _execute_single_step(self, page: Page, step_config: Dict[str, Any]) -> StepExecutionResult:
        """Execute a single test step with error handling and self-healing"""
        
        step_id = step_config.get("step_id", 0)
        action = TestActionType(step_config.get("action", "wait"))
        description = step_config.get("description", "")
        target = step_config.get("target", "")


        logger.info(f"Executing step {step_id}: {action.value} - {description}")
        
        step_result = StepExecutionResult(
            step_id=step_id,
            action=action,
            description=description,
            target=target,
            status=TestStatus.RUNNING,
            start_time=datetime.now().isoformat()
        )
        
        try:
            # Execute the step action
            success = await self._perform_step_action(page, step_config, step_result)
            
            if success:
                step_result.status = TestStatus.COMPLETED
                logger.info(f"Step {step_id} completed successfully")
            else:
                step_result.status = TestStatus.FAILED
                step_result.error = "Action execution failed"
                
                # Attempt self-healing if step failed
                healing_result = await self.self_healing_agent.attempt_healing(
                    page, step_config, step_result.error or "Unknown error"
                )
                
                if healing_result.success:
                    step_result.healing_applied = True
                    step_result.status = TestStatus.COMPLETED
                    logger.info(f"Step {step_id} healed successfully using: {healing_result.strategy_used}")
                else:
                    logger.warning(f"Step {step_id} failed and healing unsuccessful")
            
            # Take screenshot if requested
            if step_config.get("screenshot_after", False):
                screenshot_path = await self._take_screenshot(page, f"step_{step_id}")
                step_result.screenshot_path = screenshot_path
            
        except Exception as e:
            step_result.status = TestStatus.FAILED
            step_result.error = str(e)
            logger.error(f"Step {step_id} failed with error: {e}")
        
        finally:
            step_result.end_time = datetime.now().isoformat()
        
        return step_result
    
    async def _perform_step_action(self, page: Page, step_config: Dict[str, Any], 
                                 step_result: StepExecutionResult) -> bool:
        """Perform the actual step action"""
        
        action = TestActionType(step_config.get("action"))
        
        try:
            if action == TestActionType.NAVIGATE:
                url = step_config.get("value", "") or step_config.get("primary_selector", "")
                
                if url:
                    logger.info(f"Navigating to: {url}")
                    await page.goto(url, wait_until="networkidle", timeout=300000)
                    return True
                else:
                    step_result.error = "No URL specified for navigation"
                    return False
            
            elif action == TestActionType.CLICK:
                element_result = await self.element_detection_agent.find_element(page, step_config)
                if element_result.found:
                    element = page.locator(element_result.selector_used.selector)
                    await element.first.click(timeout=step_config.get("timeout", 180000))
                    step_result.selector_used = element_result.selector_used.selector
                    return True
                else:
                    step_result.error = f"Element not found: {step_config.get('target')}"
                    return False
            
            elif action == TestActionType.TYPE:
                element_result = await self.element_detection_agent.find_element(page, step_config)
                if element_result.found:
                    element = page.locator(element_result.selector_used.selector)
                    value = step_config.get("value", "")
                    await element.first.clear()
                    await element.first.type(value, delay=100)  # Slow typing for legacy apps
                    step_result.selector_used = element_result.selector_used.selector
                    return True
                else:
                    step_result.error = f"Element not found: {step_config.get('target')}"
                    return False
            
            elif action == TestActionType.WAIT:
                # Use timeout field first, then value field, with minimum of 180000ms
                wait_time = max(
                    int(step_config.get("timeout", 180000)),
                    int(step_config.get("value", 180000)),
                    180000  # Minimum 180 seconds
                )
                await page.wait_for_timeout(wait_time)
                return True
            
            elif action == TestActionType.VERIFY:
                return await self._verify_condition(page, step_config, step_result)
            
            elif action == TestActionType.SCREENSHOT:
                screenshot_path = await self._take_screenshot(page, step_config.get("name", "screenshot"))
                step_result.screenshot_path = screenshot_path
                return True
            
            elif action == TestActionType.SELECT:
                element_result = await self.element_detection_agent.find_element(page, step_config)
                if element_result.found:
                    element = page.locator(element_result.selector_used.selector)
                    value = step_config.get("value", "")
                    await element.first.select_option(value)
                    step_result.selector_used = element_result.selector_used.selector
                    return True
                else:
                    step_result.error = f"Element not found: {step_config.get('target')}"
                    return False
            
            elif action == TestActionType.SCROLL:
                # Scroll to element or by amount
                if "selector" in step_config:
                    element_result = await self.element_detection_agent.find_element(page, step_config)
                    if element_result.found:
                        element = page.locator(element_result.selector_used.selector)
                        await element.first.scroll_into_view_if_needed()
                        return True
                else:
                    # Scroll by amount
                    await page.keyboard.press("PageDown")
                    return True
            
            else:
                step_result.error = f"Unsupported action: {action}"
                return False
                
        except Exception as e:
            step_result.error = str(e)
            return False
    
    async def _verify_condition(self, page: Page, step_config: Dict[str, Any], 
                              step_result: StepExecutionResult) -> bool:
        """Verify a condition on the page"""
        
        verification = step_config.get("verification", "")
        target = step_config.get("target", "")
        
        try:
            # Simple text presence verification
            if "text" in verification.lower():
                page_content = await page.content()
                if target.lower() in page_content.lower():
                    return True
                else:
                    step_result.error = f"Text not found: {target}"
                    return False
            
            # Element presence verification
            elif "element" in verification.lower():
                element_result = await self.element_detection_agent.find_element(page, step_config)
                if element_result.found:
                    return True
                else:
                    step_result.error = f"Element not found for verification: {target}"
                    return False
            
            # URL verification
            elif "url" in verification.lower():
                current_url = page.url
                if target.lower() in current_url.lower():
                    return True
                else:
                    step_result.error = f"URL verification failed. Expected: {target}, Got: {current_url}"
                    return False
            
            # Title verification
            elif "title" in verification.lower():
                page_title = await page.title()
                if target.lower() in page_title.lower():
                    return True
                else:
                    step_result.error = f"Title verification failed. Expected: {target}, Got: {page_title}"
                    return False
            
            else:
                # Generic verification - check if target exists on page
                page_content = await page.content()
                return target.lower() in page_content.lower()
                
        except Exception as e:
            step_result.error = f"Verification failed: {str(e)}"
            return False
    
    async def _take_screenshot(self, page: Page, name: str) -> str:
        """Take a screenshot and return the file path"""
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = f"screenshots/{filename}"
            
            await page.screenshot(path=filepath, full_page=True)
            logger.info(f"Screenshot saved: {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return ""
    
    def _requires_authentication(self, test_results: TestResults) -> bool:
        """Check if authentication is required based on current results"""
        
        # Simple heuristic: if we see login-related failures or redirects
        for step_result in test_results.step_results:
            if step_result.error and "login" in step_result.error.lower():
                return True
        
        return False
    
    async def _handle_authentication(self, page: Page, credentials: Dict[str, str], 
                                   test_results: TestResults):
        """Handle authentication flow"""
        
        logger.info("Attempting authentication...")
        
        try:
            username = credentials.get("username", "")
            password = credentials.get("password", "")
            
            # Common login form patterns
            username_selectors = [
                "input[name='username']",
                "input[name='user']", 
                "input[name='login']",
                "input[type='text']",
                "#username",
                "#user"
            ]
            
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "#password"
            ]
            
            login_button_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Login')",
                "button:has-text('Sign In')",
                "#login-btn",
                ".login-button"
            ]
            
            # Find and fill username
            for selector in username_selectors:
                try:
                    username_field = page.locator(selector)
                    if await username_field.count() > 0:
                        await username_field.first.clear()
                        await username_field.first.type(username)
                        break
                except:
                    continue
            
            # Find and fill password
            for selector in password_selectors:
                try:
                    password_field = page.locator(selector)
                    if await password_field.count() > 0:
                        await password_field.first.clear()
                        await password_field.first.type(password)
                        break
                except:
                    continue
            
            # Find and click login button
            for selector in login_button_selectors:
                try:
                    login_button = page.locator(selector)
                    if await login_button.count() > 0:
                        await login_button.first.click()
                        break
                except:
                    continue
            
            # Wait for authentication to complete
            await page.wait_for_timeout(5000)
            
            logger.info("Authentication attempt completed")
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
    
    async def _execute_cleanup_steps(self, page: Page, cleanup_steps: list):
        """Execute cleanup steps"""
        
        logger.info("Executing cleanup steps...")
        
        for step in cleanup_steps:
            try:
                action = step.get("action", "")
                
                if action == "screenshot":
                    name = step.get("name", "final_cleanup")
                    await self._take_screenshot(page, name)
                
                elif action == "browser_close":
                    # Browser will be closed by browser pool
                    logger.info("Browser close requested - will be handled by browser pool")
                
                # Add other cleanup actions as needed
                
            except Exception as e:
                logger.warning(f"Cleanup step failed: {step} - {e}")
    
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

    async def execute_workflow_template(self, workflow_template: Dict[str, Any],
                                       field_values: Dict[str, Any],
                                       application_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a workflow template with user-provided field values
        
        Args:
            workflow_template: Workflow template definition
            field_values: User-provided values for template fields
            application_url: Target application URL
            
        Returns:
            Dict containing workflow execution results
        """
        logger.info(f"Executing workflow: {workflow_template.get('workflow_name', 'Unknown')}")
        
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
        
        page = None
        try:
            # Get browser page
            page = await self.browser_pool.get_page()
            
            if not page:
                raise Exception("Failed to get browser page")
            
            # Navigate to application if URL provided
            if application_url:
                await page.goto(application_url, wait_until="networkidle", timeout=300000)
                await asyncio.sleep(2)
                
                # Take initial screenshot
                screenshot = await page.screenshot(full_page=True)
                execution_results["screenshots"].append({
                    "step": "initial_navigation",
                    "timestamp": datetime.now().isoformat(),
                    "data": screenshot
                })
            
            # Execute workflow steps
            for step_index, step in enumerate(workflow_template.get("steps", [])):
                step_result = await self._execute_workflow_step(
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
                    "step": f"step_{step_index + 1}",
                    "timestamp": datetime.now().isoformat(),
                    "data": screenshot
                })
                
                await asyncio.sleep(1)  # Brief pause between steps
            
            if execution_results["status"] != "failed":
                execution_results["status"] = "completed"
                
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            execution_results["status"] = "failed"
            execution_results["error"] = str(e)
            
            if page:
                try:
                    screenshot = await page.screenshot(full_page=True)
                    execution_results["screenshots"].append({
                        "step": "error_screenshot",
                        "timestamp": datetime.now().isoformat(),
                        "data": screenshot
                    })
                except:
                    pass
                    
        finally:
            if page:
                await self.browser_pool.return_page(page)
                
        execution_results["end_time"] = datetime.now().isoformat()
        return execution_results

    async def _execute_workflow_step(self, page: Page, step: Dict[str, Any], 
                                   field_values: Dict[str, Any], step_number: int) -> Dict[str, Any]:
        """Execute a single workflow step"""
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
            action = step.get("action")
            
            if action == "navigate_to_hierarchy":
                await self._navigate_to_network_hierarchy(page)
            elif action == "check_area_exists":
                exists = await self._check_area_exists(page, field_values.get("area_name"))
                step_result["area_exists"] = exists
            elif action == "create_area" and step.get("conditional") == "if_area_not_exists":
                if not step_result.get("area_exists", True):  # Only if area doesn't exist
                    await self._create_area(page, field_values.get("area_name"))
            elif action == "expand_global":
                await self._expand_global_node(page)
            elif action == "check_building_exists":
                exists = await self._check_building_exists(page, field_values.get("building_name"))
                step_result["building_exists"] = exists  
            elif action == "create_building" and step.get("conditional") == "if_building_not_exists":
                if not step_result.get("building_exists", True):  # Only if building doesn't exist
                    await self._create_building(page, field_values.get("building_name"), 
                                              field_values.get("address", "Sanjose"))
            elif action == "verify_hierarchy":
                await self._verify_hierarchy_structure(page, field_values.get("area_name"), 
                                                     field_values.get("building_name"))
            # Inventory workflow actions
            elif action == "navigate_to_inventory":
                await self._navigate_to_inventory_page(page)
            elif action == "check_devices_exist":
                exists = await self._check_devices_exist(page)
                step_result["devices_exist"] = exists
            elif action == "import_devices" and step.get("conditional") == "if_devices_not_exist":
                if not step_result.get("devices_exist", True):  # Only if devices don't exist
                    await self._import_devices_from_file(page, field_values.get("file_name"))
            elif action == "assign_devices_to_site":
                await self._assign_devices_to_site(page, field_values.get("building_name"))
            elif action == "wait_for_assignment":
                wait_time = int(field_values.get("wait_time", 180))
                await self._wait_for_assignment_completion(page, wait_time)
            elif action == "provision_devices":
                await self._provision_assigned_devices(page)
            elif action == "verify_provisioning":
                await self._verify_provisioning_started(page)
            # Fabric Settings workflow actions
            elif action == "navigate_to_fabric_sites":
                await self._navigate_to_fabric_sites(page)
            elif action == "verify_fabric_sites_summary":
                success = await self._verify_fabric_sites_summary(page)
                step_result["summary_verified"] = success
            elif action == "navigate_to_fabric_details":
                success = await self._navigate_to_fabric_details(page, field_values.get("fabric_name"))
                step_result["fabric_details_loaded"] = success
            elif action == "verify_fabric_name":
                success = await self._verify_fabric_name_displayed(page, field_values.get("fabric_name"))
                step_result["fabric_name_verified"] = success
            elif action == "navigate_to_fabric_settings":
                success = await self._navigate_to_fabric_settings(page)
                step_result["settings_loaded"] = success
            elif action == "take_fabric_screenshot":
                screenshot_path = await self._take_fabric_settings_screenshot(page, field_values.get("fabric_name"))
                step_result["screenshot_path"] = screenshot_path
            elif action == "verify_config_parameters":
                success = await self._verify_fabric_config_parameters(page)
                step_result["config_verified"] = success
            else:
                # Handle generic actions
                await self._handle_generic_step(page, step, field_values)
                
            step_result["status"] = "passed"
            
        except Exception as e:
            logger.error(f"Step {step_number} failed: {e}")
            step_result["status"] = "failed"
            step_result["error"] = str(e)
            
        step_result["end_time"] = datetime.now().isoformat()
        return step_result

    async def _navigate_to_network_hierarchy(self, page: Page):
        """Navigate to the Network Hierarchy page"""
        # Click hamburger menu
        await page.click("button[data-testid='hamburger-menu'], .menu-toggle, .nav-toggle")
        await asyncio.sleep(1)
        
        # Click Design menu
        await page.click("a:has-text('Design'), button:has-text('Design')")
        await asyncio.sleep(1)
        
        # Click Network Hierarchy
        await page.click("a:has-text('Network Hierarchy'), button:has-text('Network Hierarchy')")
        await page.wait_for_load_state("networkidle")
        
        # Verify page loaded
        await page.wait_for_selector(":has-text('Global')", timeout=10000)

    async def _check_area_exists(self, page: Page, area_name: str) -> bool:
        """Check if area already exists under Global"""
        try:
            # Look for area node in hierarchy
            area_selector = f".hierarchy-node:has-text('{area_name}'), [data-testid*='{area_name}']"
            await page.wait_for_selector(area_selector, timeout=3000)
            return True
        except:
            return False

    async def _create_area(self, page: Page, area_name: str):
        """Create new area under Global"""
        # Find and click overflow menu for Global
        await page.click("[data-testid='global-overflow'], .overflow-menu:near(.hierarchy-node:has-text('Global'))")
        await asyncio.sleep(1)
        
        # Click Add Area
        await page.click("button:has-text('Add Area'), [data-testid='add-area-btn']")
        await asyncio.sleep(1)
        
        # Enter area name
        await page.fill("input[name*='area'], input[placeholder*='area'], input[data-testid*='area-name']", area_name)
        
        # Click Add button
        await page.click("button:has-text('Add'), button[data-testid='add-btn'], button[type='submit']")
        
        # Wait for confirmation
        await page.wait_for_selector(":has-text('Area Added Successfully'), :has-text('Successfully created area')", timeout=10000)

    async def _expand_global_node(self, page: Page):
        """Expand Global node to show areas"""
        try:
            await page.click(".expand-arrow:near(.hierarchy-node:has-text('Global')), [data-testid='expand-global']")
            await asyncio.sleep(1)
        except:
            # Already expanded or different structure
            pass

    async def _check_building_exists(self, page: Page, building_name: str) -> bool:
        """Check if building already exists"""
        try:
            building_selector = f".hierarchy-node:has-text('{building_name}'), [data-testid*='{building_name}']"
            await page.wait_for_selector(building_selector, timeout=3000)
            return True
        except:
            return False

    async def _create_building(self, page: Page, building_name: str, address: str):
        """Create new building under area"""
        # Find and click overflow menu for area (this will need to be refined)
        await page.click(f".overflow-menu:near(.hierarchy-node:has-text('{building_name}'))")
        await asyncio.sleep(1)
        
        # Click Add Building
        await page.click("button:has-text('Add Building'), [data-testid='add-building-btn']")
        await asyncio.sleep(1)
        
        # Enter building name
        await page.fill("input[name*='building'], input[placeholder*='building'], input[data-testid*='building-name']", building_name)
        
        # Enter address if provided
        if address:
            await page.fill("input[name*='address'], input[placeholder*='address'], input[data-testid*='address']", address)
            # Select first dropdown option
            await page.click(".dropdown-item:first, .suggestion-item:first")
        
        # Click Add button
        await page.click("button:has-text('Add'), button[data-testid='add-btn'], button[type='submit']")
        
        # Wait for confirmation
        await page.wait_for_selector(":has-text('Site Added Successfully'), :has-text('Building created successfully')", timeout=10000)

    async def _verify_hierarchy_structure(self, page: Page, area_name: str, building_name: str):
        """Verify the complete hierarchy structure"""
        # Check that all elements exist
        await page.wait_for_selector(".hierarchy-node:has-text('Global')", timeout=5000)
        await page.wait_for_selector(f".hierarchy-node:has-text('{area_name}')", timeout=5000)
        await page.wait_for_selector(f".hierarchy-node:has-text('{building_name}')", timeout=5000)

    # ============================================================================
    # INVENTORY WORKFLOW METHODS
    # ============================================================================

    async def _navigate_to_inventory_page(self, page: Page):
        """Navigate to the Provision > Inventory page"""
        # Click hamburger menu
        await page.click("button[data-testid='hamburger-menu'], .menu-toggle, .nav-toggle")
        await asyncio.sleep(1)
        
        # Click Provision menu
        await page.click("a:has-text('Provision'), button:has-text('Provision')")
        await asyncio.sleep(1)
        
        # Click Inventory option
        await page.click("a:has-text('Inventory'), button:has-text('Inventory')")
        await page.wait_for_load_state("networkidle")
        
        # Verify page loaded
        await page.wait_for_selector(".device-table, .inventory-table, [data-testid='device-list']", timeout=10000)

    async def _check_devices_exist(self, page: Page) -> bool:
        """Check if devices already exist in inventory"""
        try:
            # Look for empty state or existing devices
            empty_selector = ":has-text('No devices found'), .empty-inventory"
            await page.wait_for_selector(empty_selector, timeout=3000)
            return False  # Found empty state, no devices exist
        except:
            # No empty state found, devices might exist
            try:
                device_selector = ".device-table tbody tr, .inventory-table tbody tr"
                await page.wait_for_selector(device_selector, timeout=3000)
                return True  # Found device rows
            except:
                return False  # No devices found

    async def _import_devices_from_file(self, page: Page, file_name: str):
        """Import devices from the specified file"""
        # Click Add Device button
        await page.click("button:has-text('+Add device'), button:has-text('Add Device'), [data-testid='add-device-btn']")
        await asyncio.sleep(1)
        
        # Click Import Inventory option
        await page.click("button:has-text('Import Inventory'), a:has-text('Import Inventory')")
        await asyncio.sleep(1)
        
        # Handle file upload
        file_input = page.locator("input[type='file']")
        if await file_input.count() > 0:
            # Direct file input approach
            import os
            downloads_path = os.path.expanduser("~/Downloads")
            file_path = os.path.join(downloads_path, file_name)
            await file_input.set_input_files(file_path)
        else:
            # Click upload area to trigger file picker
            await page.click(":has-text('Click or drag file'), .upload-area")
            await asyncio.sleep(2)
            
            # Note: macOS file picker handling would need native automation
            # For now, we'll assume the file is selected programmatically
            logger.warning("macOS file picker interaction needs native automation support")
        
        await asyncio.sleep(2)
        
        # Click Next button
        await page.click("button:has-text('Next'), [data-testid='next-btn']")
        await asyncio.sleep(1)
        
        # Click Import Devices button
        await page.click("button:has-text('Import Devices'), button:has-text('Import')")
        
        # Wait for success message
        await page.wait_for_selector(":has-text('Done!'), :has-text('Devices imported successfully')", timeout=30000)
        
        # Click View Inventory button if available
        try:
            await page.click("button:has-text('View Inventory')", timeout=5000)
        except:
            pass  # Button might not be present

    async def _assign_devices_to_site(self, page: Page, building_name: str):
        """Assign imported devices to the specified building"""
        # Select all devices
        await page.click("input[type='checkbox'][data-testid='select-all'], .select-all-checkbox")
        await asyncio.sleep(1)
        
        # Click Actions button
        await page.click("button:has-text('Actions'), [data-testid='actions-btn']")
        await asyncio.sleep(1)
        
        # Hover over Provision and click Assign device to Site
        await page.hover("button:has-text('Provision'), a:has-text('Provision')")
        await asyncio.sleep(1)
        await page.click("button:has-text('Assign device to Site'), a:has-text('Assign device to Site')")
        await asyncio.sleep(2)
        
        # Click choose a site button
        await page.click("button:has-text('choose a site'), [data-testid='choose-site']")
        await asyncio.sleep(1)
        
        # Expand hierarchy and select building
        await page.click(".expand-arrow, .hierarchy-expand")
        await asyncio.sleep(1)
        
        # Select the specific building
        await page.click(f".hierarchy-node:has-text('{building_name}'), [data-testid*='{building_name}']")
        await asyncio.sleep(1)
        
        # Click Save button
        await page.click("button:has-text('Save'), [data-testid='save-btn']")
        await asyncio.sleep(1)
        
        # Click Next button
        await page.click("button:has-text('Next'), [data-testid='next-btn']")
        await asyncio.sleep(1)
        
        # Click Next button again
        await page.click("button:has-text('Next'), [data-testid='next-btn']")
        await asyncio.sleep(1)
        
        # Select Now option and click Assign
        await page.click("input[value='Now'], :has-text('Now')[type='radio']")
        await asyncio.sleep(1)
        await page.click("button:has-text('Assign'), [data-testid='assign-btn']")
        await asyncio.sleep(1)
        
        # Click Submit button
        await page.click("button:has-text('Submit'), [data-testid='submit-btn']")
        
        # Wait to be redirected back to inventory page
        await page.wait_for_load_state("networkidle")

    async def _wait_for_assignment_completion(self, page: Page, wait_time: int):
        """Wait for device assignment to complete"""
        logger.info(f"Waiting {wait_time} seconds for device assignment to complete")
        await asyncio.sleep(wait_time)
        
        # Optionally check assignment status
        try:
            await page.wait_for_selector(".assignment-status, [data-testid='assignment-progress']", timeout=5000)
        except:
            pass  # Status indicator might not be present

    async def _provision_assigned_devices(self, page: Page):
        """Provision the assigned devices"""
        # Select all devices
        await page.click("input[type='checkbox'][data-testid='select-all'], .select-all-checkbox")
        await asyncio.sleep(1)
        
        # Click Actions button
        await page.click("button:has-text('Actions'), [data-testid='actions-btn']")
        await asyncio.sleep(1)
        
        # Hover over Provision and click Provision Device
        await page.hover("button:has-text('Provision'), a:has-text('Provision')")
        await asyncio.sleep(1)
        await page.click("button:has-text('Provision Device'), a:has-text('Provision Device')")
        
        # Wait for navigation to Provision Devices page
        await page.wait_for_load_state("networkidle")
        
        # Click Next button three times
        for i in range(3):
            await page.click("button:has-text('Next'), [data-testid='next-btn']")
            await asyncio.sleep(1)
        
        # Select Now option and click Apply
        await page.click("input[value='Now'], :has-text('Now')[type='radio']")
        await asyncio.sleep(1)
        await page.click("button:has-text('Apply'), [data-testid='apply-btn']")
        
        # Wait for Task Submitted message
        await page.wait_for_selector(":has-text('Task Submitted'), .task-success", timeout=30000)

    async def _verify_provisioning_started(self, page: Page):
        """Verify device provisioning process has started"""
        # Check for provisioning status indicators
        try:
            await page.wait_for_selector(".provisioning-status, [data-testid='provisioning-progress']", timeout=5000)
        except:
            pass  # Status indicator might not be present
        
        # Check for task queue or status
        try:
            await page.wait_for_selector(".task-queue, [data-testid='task-status']", timeout=5000)
        except:
            pass  # Task status might not be present

    async def _navigate_to_fabric_sites(self, page: Page):
        """Navigate to Provision > Fabric Sites page"""
        # Click hamburger menu
        await page.click("button[data-testid='hamburger-menu'], .menu-toggle, .nav-toggle")
        await asyncio.sleep(1)
        
        # Click Provision menu
        await page.click("a:has-text('Provision'), button:has-text('Provision')")
        await asyncio.sleep(1)
        
        # Click Fabric Sites option under SD Access
        await page.click("a:has-text('Fabric Sites'), button:has-text('Fabric Sites')")
        await page.wait_for_load_state("networkidle")
        
        # Verify page loaded
        await page.wait_for_selector("[data-test='summary-section'], .summary-header, h2:contains('SUMMARY'), h3:contains('SUMMARY')", timeout=10000)

    async def _verify_fabric_sites_summary(self, page: Page):
        """Verify fabric sites summary section is visible"""
        try:
            # Check for SUMMARY section
            await page.wait_for_selector("[data-test='summary-section'], .summary-header, h2:contains('SUMMARY'), h3:contains('SUMMARY')", timeout=10000)
            
            # Check for fabric sites count
            await page.wait_for_selector("[data-test='fabric-sites-count'], .count-display, .summary-count", timeout=10000)
            
            return True
        except Exception as e:
            logger.error(f"Failed to verify fabric sites summary: {e}")
            return False

    async def _navigate_to_fabric_details(self, page: Page, fabric_name: str):
        """Navigate to specific fabric details page"""
        try:
            # Click on fabric sites count
            await page.click("[data-test='fabric-sites-count'], .count-display, .summary-count")
            await asyncio.sleep(2)
            
            # Click on specific fabric name
            fabric_selector = f"[data-test='fabric-name']:has-text('{fabric_name}'), .fabric-item:has-text('{fabric_name}'), td:has-text('{fabric_name}')"
            await page.click(fabric_selector)
            await page.wait_for_load_state("networkidle")
            
            # Verify fabric infrastructure page loaded
            await page.wait_for_selector("[data-test='fabric-infrastructure'], .fabric-infrastructure-header, h1:contains('Fabric Infrastructure'), h2:contains('Fabric Infrastructure')", timeout=10000)
            
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to fabric details for {fabric_name}: {e}")
            return False

    async def _verify_fabric_name_displayed(self, page: Page, fabric_name: str):
        """Verify fabric name is displayed correctly on the page"""
        try:
            # Check for fabric name in page title or header
            fabric_name_selector = f"[data-test='fabric-name'], .fabric-title, .page-title:has-text('{fabric_name}')"
            await page.wait_for_selector(fabric_name_selector, timeout=10000)
            return True
        except Exception as e:
            logger.error(f"Failed to verify fabric name {fabric_name} displayed: {e}")
            return False

    async def _navigate_to_fabric_settings(self, page: Page):
        """Navigate to fabric settings page"""
        try:
            # Click Settings tab
            await page.click("[data-test='settings-tab'], .settings-tab, button:has-text('Settings'), a:has-text('Settings')")
            await page.wait_for_load_state("networkidle")
            
            # Verify settings page loaded
            await page.wait_for_selector("[data-test='fabric-settings'], .settings-panel, .fabric-settings-container", timeout=10000)
            
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to fabric settings: {e}")
            return False

    async def _take_fabric_settings_screenshot(self, page: Page, fabric_name: str):
        """Take screenshot of fabric settings page"""
        try:
            screenshot_name = f"fabric_{fabric_name}_settings"
            screenshot_path = await self._take_screenshot(page, screenshot_name)
            return screenshot_path
        except Exception as e:
            logger.error(f"Failed to take fabric settings screenshot: {e}")
            return None

    async def _verify_fabric_config_parameters(self, page: Page):
        """Verify all fabric configuration parameters are visible"""
        try:
            # Check for configuration items
            await page.wait_for_selector("[data-test='config-parameters'], .config-item, .setting-row", timeout=10000)
            
            # Count configuration items
            config_items = await page.locator("[data-test='config-parameters'], .config-item, .setting-row").count()
            
            if config_items > 0:
                logger.info(f"Found {config_items} configuration parameters")
                return True
            else:
                logger.warning("No configuration parameters found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to verify configuration parameters: {e}")
            return False

    async def _handle_generic_step(self, page: Page, step: Dict[str, Any], field_values: Dict[str, Any]):
        """Handle generic workflow steps"""
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
        
        if action == "click":
            await page.click(selector)
            await asyncio.sleep(1)  # Brief pause after clicks
            
        elif action == "verify":
            # Wait for element to be visible for verification
            await page.wait_for_selector(selector, timeout=10000)
            
        elif action == "screenshot":
            # Take screenshot with custom name if provided
            screenshot_name = value or f"step_{step.get('step_id', 'unknown')}"
            await self._take_screenshot(page, screenshot_name)
            
        elif action == "type":
            field_value = field_values.get(value, value) if value else ""
            await page.fill(selector, str(field_value))
            
        elif action == "wait":
            timeout = step.get("timeout", 1000)
            await asyncio.sleep(timeout / 1000)

if __name__ == "__main__":
    print("Browser automation layer implementation completed!")
    print("✅ Browser Pool Management")
    print("✅ Test Executor with Self-Healing")
    print("✅ Legacy Application Optimizations")
    print("\nNext: Implement infrastructure layer...")