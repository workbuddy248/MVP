# src/core/orchestrator.py
"""
Orchestration Layer - Coordinates NLProcessor and WorkflowIntelligenceAgent
Handles the decision-making between simple tests and complex workflows
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from ..agents.nl_processor_simple import NLProcessor
from ..agents.workflow_intelligence_agent import WorkflowIntelligenceAgent
from ..models.test_models import UserIntent
from ..models.workflow_models import (
    WorkflowDetectionResult, WorkflowTemplate, EnhancedWorkflow,
    WorkflowExecutionRequest, WorkflowExecutionResponse, WorkflowStatus
)
from ..core.azure_client import AzureOpenAIClient

logger = logging.getLogger(__name__)

class TestOrchestrator:
    """
    Central orchestrator that coordinates between NLP and workflow intelligence
    Decides whether to route through simple test generation or workflow templates
    """
    
    def __init__(self, azure_client: AzureOpenAIClient, config_path: Path, nl_processor: NLProcessor = None):
        self.azure_client = azure_client
        self.config_path = config_path
        
        # Use shared nl_processor if provided, otherwise create new one
        if nl_processor:
            self.nl_processor = nl_processor
        else:
            self.nl_processor = NLProcessor(azure_client)
            
        self.workflow_agent = WorkflowIntelligenceAgent(azure_client, config_path)
        
        logger.info("TestOrchestrator initialized")

    async def process_user_request(self, user_input: str, context: Dict[str, Any] = None) -> WorkflowExecutionResponse:
        """
        Main entry point - processes user input and returns appropriate response
        Routes between simple test generation and workflow template creation
        """
        try:
            execution_id = self._generate_execution_id()
            
            logger.info(f"Processing user request [{execution_id}]: {user_input}")
            
            # Step 1: Parse user intent with NLP
            user_intent = await self.nl_processor.parse_user_intent(user_input, context)
            
            # Step 2: Check if this requires workflow intelligence
            if user_intent.intent_type == "workflow" or getattr(user_intent, 'requires_template', False):
                return await self._handle_workflow_request(execution_id, user_input, user_intent, context)
            else:
                return await self._handle_simple_request(execution_id, user_intent, context)
                
        except Exception as e:
            logger.error(f"Error processing user request: {e}")
            return WorkflowExecutionResponse(
                execution_id=execution_id,
                status=WorkflowStatus.FAILED,
                workflow_template=None,
                enhanced_workflow=None,
                generated_test=None,
                error_message=str(e),
                next_action="retry"
            )

    async def _handle_workflow_request(self, execution_id: str, user_input: str, user_intent: UserIntent, context: Dict[str, Any]) -> WorkflowExecutionResponse:
        """Handle complex workflow requests requiring template customization"""
        try:
            logger.info(f"Handling workflow request [{execution_id}]")
            
            # Step 1: Detect specific workflow
            workflow_detection = await self.workflow_agent.detect_workflow(user_input, user_intent.__dict__)
            
            if not workflow_detection.detected:
                # Fallback to simple test generation
                logger.info(f"No specific workflow detected, falling back to simple test")
                return await self._handle_simple_request(execution_id, user_intent, context)
            
            # Step 2: Generate template
            workflow_template = await self.workflow_agent.generate_template(
                workflow_detection.workflow_id,
                workflow_detection.extracted_values
            )
            
            # Step 3: Pre-fill any values from context
            if context:
                self._prefill_template_from_context(workflow_template, context)
            
            logger.info(f"Generated workflow template [{execution_id}]: {workflow_detection.workflow_id}")
            
            return WorkflowExecutionResponse(
                execution_id=execution_id,
                status=WorkflowStatus.TEMPLATE_REQUIRED,
                workflow_template=workflow_template,
                enhanced_workflow=None,
                generated_test=None,
                error_message=None,
                next_action="customize_template"
            )
            
        except Exception as e:
            logger.error(f"Error handling workflow request [{execution_id}]: {e}")
            raise

    async def _handle_simple_request(self, execution_id: str, user_intent: UserIntent, context: Dict[str, Any]) -> WorkflowExecutionResponse:
        """Handle simple test requests that don't require workflow templates"""
        try:
            logger.info(f"Handling simple test request [{execution_id}]")
            
            # For simple requests, we'll return a basic test structure
            # This will be processed by the existing test generation pipeline
            
            simple_test = {
                "test_type": "simple",
                "user_intent": user_intent.__dict__,
                "context": context,
                "timeout_config": self._get_enhanced_timeout_config()
            }
            
            return WorkflowExecutionResponse(
                execution_id=execution_id,
                status=WorkflowStatus.COMPLETED,
                workflow_template=None,
                enhanced_workflow=None,
                generated_test=simple_test,
                error_message=None,
                next_action="execute_test"
            )
            
        except Exception as e:
            logger.error(f"Error handling simple request [{execution_id}]: {e}")
            raise

    async def process_template_submission(self, execution_id: str, workflow_id: str, user_values: Dict[str, Any], dependency_responses: Dict[str, Any]) -> WorkflowExecutionResponse:
        """
        Process user's customized template submission
        Generates enhanced workflow with dependencies
        """
        try:
            logger.info(f"Processing template submission [{execution_id}]: {workflow_id}")
            
            # Step 1: Enhance workflow with user values and dependencies
            enhanced_workflow = await self.workflow_agent.enhance_template(
                workflow_id, 
                user_values, 
                dependency_responses
            )
            
            # Step 2: Generate complete test structure
            complete_test = await self._generate_complete_test(enhanced_workflow)
            
            logger.info(f"Generated complete workflow test [{execution_id}] with {len(enhanced_workflow.included_workflows)} workflows")
            
            return WorkflowExecutionResponse(
                execution_id=execution_id,
                status=WorkflowStatus.COMPLETED,
                workflow_template=None,
                enhanced_workflow=enhanced_workflow,
                generated_test=complete_test,
                error_message=None,
                next_action="execute_test"
            )
            
        except Exception as e:
            logger.error(f"Error processing template submission [{execution_id}]: {e}")
            return WorkflowExecutionResponse(
                execution_id=execution_id,
                status=WorkflowStatus.FAILED,
                workflow_template=None,
                enhanced_workflow=None,
                generated_test=None,
                error_message=str(e),
                next_action="retry"
            )

    async def _generate_complete_test(self, enhanced_workflow: EnhancedWorkflow) -> Dict[str, Any]:
        """Generate complete test structure from enhanced workflow"""
        
        # Convert workflow steps to test generation format
        test_steps = []
        
        for step in enhanced_workflow.complete_test_steps:
            test_step = {
                "step_id": step["step_id"],
                "action": step["action"],
                "description": step["description"],
                "target": step.get("verification", ""),
                "primary_selector": step.get("selector", ""),
                "fallback_selectors": self._generate_fallback_selectors(step),
                "timeout": step.get("timeout", 180000),
                "wait_condition": self._get_wait_condition(step["action"]),
                "value": step.get("value"),
                "verification": step.get("verification", ""),
                "critical": step.get("critical", True),
                "screenshot_after": step.get("critical", False),
                "workflow_source": step.get("workflow_source", "unknown")
            }
            test_steps.append(test_step)
        
        # Create complete test structure
        complete_test = {
            "test_name": f"Workflow Test - {enhanced_workflow.main_workflow}",
            "test_type": "workflow",
            "setup_steps": [
                {
                    "action": "browser_init",
                    "config": {
                        "headless": False,
                        "slow_mo": 1000,
                        "timeout": 300000
                    }
                }
            ],
            "test_steps": test_steps,
            "cleanup_steps": [
                {
                    "action": "screenshot",
                    "name": "final_state",
                    "full_page": True
                },
                {
                    "action": "browser_close"
                }
            ],
            "enhanced_workflow": enhanced_workflow.__dict__,
            "timeout_config": self._get_enhanced_timeout_config()
        }
        
        return complete_test

    def _generate_fallback_selectors(self, step: Dict[str, Any]) -> list:
        """Generate fallback selectors for a step"""
        primary_selector = step.get("selector", "")
        action = step["action"]
        
        fallback_selectors = []
        
        if action == "click":
            fallback_selectors = [
                "button", 
                "a", 
                "input[type='button']",
                "input[type='submit']",
                "[role='button']"
            ]
        elif action == "type":
            fallback_selectors = [
                "input[type='text']",
                "input:not([type])",
                "textarea",
                "[contenteditable='true']"
            ]
        elif action == "select":
            fallback_selectors = [
                "select",
                "div[role='combobox']",
                "div[class*='dropdown']"
            ]
        
        # Remove primary selector from fallbacks if it exists
        if primary_selector:
            fallback_selectors = [fs for fs in fallback_selectors if fs != primary_selector]
        
        return fallback_selectors

    def _get_wait_condition(self, action: str) -> str:
        """Get appropriate wait condition for action"""
        wait_conditions = {
            "navigate": "networkidle",
            "click": "visible",
            "type": "visible",
            "wait": "visible",
            "verify": "visible",
            "select": "visible"
        }
        return wait_conditions.get(action, "visible")

    def _get_enhanced_timeout_config(self) -> Dict[str, int]:
        """Get enhanced timeout configuration for all operations"""
        return {
            "page_load": 300000,      # 300s for page loads
            "action_timeout": 180000, # 180s for individual actions
            "element_wait": 180000,   # 180s for element visibility
            "navigation": 300000,     # 300s for navigation
            "form_submission": 180000 # 180s for form submissions
        }

    def _prefill_template_from_context(self, template: WorkflowTemplate, context: Dict[str, Any]) -> None:
        """Pre-fill template fields from context"""
        context_mappings = {
            "url": "target_url",
            "username": "username", 
            "password": "password"
        }
        
        for context_key, field_id in context_mappings.items():
            if context_key in context:
                # Find and update field
                for field in template.fields + template.global_fields:
                    if field["field_id"] == field_id:
                        field["default_value"] = context[context_key]
                        logger.debug(f"Pre-filled {field_id} from context")
                        break

    def _generate_execution_id(self) -> str:
        """Generate unique execution ID"""
        import uuid
        import datetime
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"session_{timestamp}_{unique_id}"

    # Public methods for workflow management
    
    def list_available_workflows(self) -> list:
        """List all available workflows"""
        return self.workflow_agent.list_available_workflows()

    def search_workflows(self, query: str, category: Optional[str] = None) -> list:
        """Search workflows"""
        return self.workflow_agent.search_workflows(query, category)

    def refresh_workflows(self) -> None:
        """Refresh workflow definitions"""
        self.workflow_agent.refresh_workflows()
        logger.info("Workflows refreshed")

    async def validate_template_values(self, workflow_id: str, user_values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user template values"""
        return self.workflow_agent.registry.validate_template(workflow_id, user_values)
