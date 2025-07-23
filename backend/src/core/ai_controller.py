# src/core/ai_controller.py
"""
AI Controller - Central Agent Orchestrator
Implements the core architecture with sequential agent coordination
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from .azure_client import AzureOpenAIClient, PromptTemplates
from ..models.test_models import TestExecutionResult, AgentResult

logger = logging.getLogger(__name__)

@dataclass
class AgentExecutionContext:
    """Context passed between agents during execution"""
    user_input: str
    application_url: Optional[str] = None
    user_credentials: Optional[Dict[str, str]] = None
    execution_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.execution_metadata is None:
            self.execution_metadata = {}

class AIController:
    """
    Central AI Controller implementing your architecture design
    
    Responsibilities:
    1. Orchestrate sequential agent execution
    2. Manage execution context between agents
    3. Handle errors and fallbacks
    4. Coordinate with infrastructure layer
    
    Agent Flow:
    User Input → NL Processor → Test Strategy → Test Generation → Execution
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.azure_client = AzureOpenAIClient(config["azure_openai"])
        
        # Agent configurations
        self.agent_configs = config.get("agents", {})
        
        # Execution state
        self.current_context: Optional[AgentExecutionContext] = None
        self.execution_results: Dict[str, AgentResult] = {}
        
        logger.info("AI Controller initialized with sequential agent coordination")
    
    async def execute_user_request(self, user_input: str, 
                                 application_url: Optional[str] = None,
                                 user_credentials: Optional[Dict[str, str]] = None) -> TestExecutionResult:
        """
        Main entry point: Execute complete user request through agent pipeline
        
        Args:
            user_input: Natural language test instructions
            application_url: Target application URL (optional)
            user_credentials: Login credentials if needed (optional)
        
        Returns:
            TestExecutionResult: Complete execution results
        """
        
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"[{execution_id}] Starting user request execution")
        logger.info(f"[{execution_id}] User input: {user_input}")
        
        # Initialize execution context
        self.current_context = AgentExecutionContext(
            user_input=user_input,
            application_url=application_url,
            user_credentials=user_credentials,
            execution_metadata={
                "execution_id": execution_id,
                "start_time": datetime.now().isoformat(),
                "agent_sequence": []
            }
        )
        
        execution_result = TestExecutionResult(
            execution_id=execution_id,
            user_input=user_input,
            start_time=datetime.now().isoformat(),
            status="running"
        )
        
        try:
            # Sequential Agent Execution Pipeline
            
            # Agent 1: Natural Language Processing
            nl_result = await self._execute_nl_processor()
            execution_result.agent_results["nl_processor"] = nl_result
            
            if not nl_result.success:
                raise Exception(f"NL Processor failed: {nl_result.error}")
            
            # Agent 2: Test Strategy Planning
            strategy_result = await self._execute_test_strategy(nl_result.output)
            execution_result.agent_results["test_strategy"] = strategy_result
            
            if not strategy_result.success:
                raise Exception(f"Test Strategy failed: {strategy_result.error}")
            
            # Agent 3: Test Generation
            generation_result = await self._execute_test_generation(strategy_result.output)
            execution_result.agent_results["test_generation"] = generation_result
            
            if not generation_result.success:
                raise Exception(f"Test Generation failed: {generation_result.error}")
            
            # Agent 4: Test Execution (with Element Detection & Self-Healing)
            test_execution_result = await self._execute_test_execution(generation_result.output)
            execution_result.agent_results["test_execution"] = test_execution_result
            
            # Calculate overall success
            execution_result.status = "completed" if test_execution_result.success else "failed"
            execution_result.test_results = test_execution_result.output
            
            logger.info(f"[{execution_id}] Execution completed: {execution_result.status}")
            
        except Exception as e:
            logger.error(f"[{execution_id}] Execution failed: {e}")
            execution_result.status = "error"
            execution_result.error = str(e)
        
        finally:
            execution_result.end_time = datetime.now().isoformat()
            execution_result.execution_metadata = self.current_context.execution_metadata
        
        return execution_result
    
    async def _execute_nl_processor(self) -> AgentResult:
        """Execute Natural Language Processor Agent"""
        
        agent_name = "NLProcessor"
        logger.info(f"Executing {agent_name}")
        
        # Update execution context
        self.current_context.execution_metadata["agent_sequence"].append({
            "agent": agent_name,
            "start_time": datetime.now().isoformat()
        })
        
        try:
            # Prepare context-aware prompt
            context_info = ""
            if self.current_context.application_url:
                context_info += f"Target Application URL: {self.current_context.application_url}\n"
            if self.current_context.user_credentials:
                context_info += "Authentication credentials provided.\n"
            
            user_prompt = f"""
            User Instructions: {self.current_context.user_input}
            
            Context:
            {context_info}
            
            Parse this into structured test intent for execution.
            """
            
            # Call Azure OpenAI
            response = await self.azure_client.call_agent(
                agent_name=agent_name,
                system_prompt=PromptTemplates.nl_processor_prompt(),
                user_prompt=user_prompt,
                response_format="json",
                temperature=self.agent_configs.get("nl_processor", {}).get("temperature", 0.1)
            )
            
            if response.success:
                logger.info(f"{agent_name} completed successfully")
                return AgentResult(
                    agent_name=agent_name,
                    success=True,
                    output=response.content,
                    execution_time=datetime.now().isoformat()
                )
            else:
                return AgentResult(
                    agent_name=agent_name,
                    success=False,
                    error=response.error,
                    execution_time=datetime.now().isoformat()
                )
                
        except Exception as e:
            logger.error(f"{agent_name} execution failed: {e}")
            return AgentResult(
                agent_name=agent_name,
                success=False,
                error=str(e),
                execution_time=datetime.now().isoformat()
            )
    
    async def _execute_test_strategy(self, nl_output: Dict[str, Any]) -> AgentResult:
        """Execute Test Strategy Agent"""
        
        agent_name = "TestStrategy"
        logger.info(f"Executing {agent_name}")
        
        try:
            # Prepare strategy prompt with NL output
            user_prompt = f"""
            Parsed User Intent: {nl_output}
            
            Application Context:
            - Type: Legacy Java Web Application
            - URL: {self.current_context.application_url or "To be provided in execution"}
            - Authentication Required: {nl_output.get('requires_authentication', True)}
            - Expected UI Patterns: {nl_output.get('ui_patterns_expected', ['forms', 'tables'])}
            
            Create comprehensive test strategy considering:
            1. Login flow requirements (primary focus)
            2. Legacy application timing needs
            3. Element detection challenges
            4. Error handling requirements
            """
            
            response = await self.azure_client.call_agent(
                agent_name=agent_name,
                system_prompt=PromptTemplates.test_strategy_prompt(),
                user_prompt=user_prompt,
                response_format="json",
                temperature=self.agent_configs.get("test_strategy", {}).get("temperature", 0.1)
            )
            
            if response.success:
                logger.info(f"{agent_name} completed successfully")
                return AgentResult(
                    agent_name=agent_name,
                    success=True,
                    output=response.content,
                    execution_time=datetime.now().isoformat()
                )
            else:
                return AgentResult(
                    agent_name=agent_name,
                    success=False,
                    error=response.error,
                    execution_time=datetime.now().isoformat()
                )
                
        except Exception as e:
            logger.error(f"{agent_name} execution failed: {e}")
            return AgentResult(
                agent_name=agent_name,
                success=False,
                error=str(e),
                execution_time=datetime.now().isoformat()
            )
    
    async def _execute_test_generation(self, strategy_output: Dict[str, Any]) -> AgentResult:
        """Execute Test Generation Agent"""
        
        agent_name = "TestGeneration"
        logger.info(f"Executing {agent_name}")
        
        try:
            # Prepare generation prompt with strategy
            user_prompt = f"""
            Test Strategy: {strategy_output}
            
            Generate Playwright test script with these requirements:
            1. Handle authentication flow (login) as priority
            2. Use extended timeouts for legacy applications (180s minimum, 300s for navigation)
            3. Include multiple selector strategies for each element
            4. Add screenshot capture for debugging
            5. Implement proper wait conditions for dynamic content
            
            CRITICAL: ALL timeout values must be at least 180000ms (180 seconds).
            Never use timeouts less than 180000ms anywhere in the test.
            
            Target Application: {self.current_context.application_url or "Will be provided at runtime"}
            Credentials Available: {bool(self.current_context.user_credentials)}
            
            Focus on reliability over speed - legacy apps need patience.
            """
            
            response = await self.azure_client.call_agent(
                agent_name=agent_name,
                system_prompt=PromptTemplates.test_generation_prompt(),
                user_prompt=user_prompt,
                response_format="json",
                temperature=self.agent_configs.get("test_generation", {}).get("temperature", 0.1)
            )
            
            if response.success:
                # Validate and fix timeout values in test generation
                validated_content = self._validate_and_fix_timeouts(response.content)
                logger.info(f"{agent_name} completed successfully")
                return AgentResult(
                    agent_name=agent_name,
                    success=True,
                    output=validated_content,
                    execution_time=datetime.now().isoformat()
                )
            else:
                return AgentResult(
                    agent_name=agent_name,
                    success=False,
                    error=response.error,
                    execution_time=datetime.now().isoformat()
                )
                
        except Exception as e:
            logger.error(f"{agent_name} execution failed: {e}")
            return AgentResult(
                agent_name=agent_name,
                success=False,
                error=str(e),
                execution_time=datetime.now().isoformat()
            )
    
    async def _execute_test_execution(self, test_script: Dict[str, Any]) -> AgentResult:
        """Execute Test Execution Agent (with browser automation)"""
        
        agent_name = "TestExecution"
        logger.info(f"Executing {agent_name}")
        
        try:
            # Import test executor (will implement next)
            from ..automation.test_executor import TestExecutor
            
            # Initialize test executor
            executor = TestExecutor(
                browser_config=self.config["browser_config"],
                azure_client=self.azure_client
            )
            
            # Execute test with context
            execution_result = await executor.execute_test_script(
                test_script=test_script,
                application_url=self.current_context.application_url,
                user_credentials=self.current_context.user_credentials
            )
            
            return AgentResult(
                agent_name=agent_name,
                success=execution_result.get("status") == "completed",
                output=execution_result,
                execution_time=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"{agent_name} execution failed: {e}")
            
            return AgentResult(
                agent_name=agent_name,
                success=False,
                output={"error": str(e)},
                error=str(e),
                execution_time=datetime.now().isoformat()
            )
    
    def _validate_and_fix_timeouts(self, test_content: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix timeout values in test generation output"""
        if not isinstance(test_content, dict):
            return test_content
            
        # Fix timeouts in test_steps
        if "test_steps" in test_content and isinstance(test_content["test_steps"], list):
            for step in test_content["test_steps"]:
                if isinstance(step, dict) and "timeout" in step:
                    # Ensure minimum timeout of 180000ms (180 seconds)
                    if step["timeout"] < 180000:
                        print(f"⚠️ Fixed timeout: {step['timeout']}ms -> 180000ms for step: {step.get('description', 'unknown')}")
                        step["timeout"] = 180000
        
        # Fix timeouts in setup_steps
        if "setup_steps" in test_content and isinstance(test_content["setup_steps"], list):
            for step in test_content["setup_steps"]:
                if isinstance(step, dict) and "config" in step and isinstance(step["config"], dict):
                    if "timeout" in step["config"] and step["config"]["timeout"] < 180000:
                        print(f"⚠️ Fixed setup timeout: {step['config']['timeout']}ms -> 300000ms")
                        step["config"]["timeout"] = 300000
        
        return test_content
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of current execution"""
        if not self.current_context:
            return {"status": "no_execution"}
        
        return {
            "execution_id": self.current_context.execution_metadata.get("execution_id"),
            "start_time": self.current_context.execution_metadata.get("start_time"),
            "agents_executed": [
                agent["agent"] for agent in 
                self.current_context.execution_metadata.get("agent_sequence", [])
            ],
            "current_status": "in_progress" if self.current_context else "completed"
        }

# Testing and validation
if __name__ == "__main__":
    print("AI Controller implementation ready!")
    print("This implements the central orchestrator from your architecture diagram.")