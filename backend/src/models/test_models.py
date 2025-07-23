# src/models/test_models.py
"""
Data Models for AI E2E Testing Agent
Defines all data structures used across the system
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum

# Enums for controlled values
class TestActionType(str, Enum):
    """Types of test actions that can be performed"""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    WAIT = "wait"
    VERIFY = "verify"
    SCREENSHOT = "screenshot"
    SCROLL = "scroll"
    SELECT = "select"
    HOVER = "hover"

class TestStatus(str, Enum):
    """Status values for test execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"

class IntentType(str, Enum):
    """Types of user intent"""
    LOGIN = "login"
    NAVIGATION = "navigation"
    FORM_INTERACTION = "form_interaction"
    DATA_VERIFICATION = "data_verification"
    WORKFLOW = "workflow"
    SEARCH = "search"
    CONFIGURATION = "configuration"

class ComplexityLevel(str, Enum):
    """Test complexity levels"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"

# Data Transfer Objects (DTOs)
@dataclass
class UserIntent:
    """Parsed user intent from Natural Language Processor"""
    intent_type: IntentType
    target_application: str
    primary_actions: List[str]
    test_objectives: List[str]
    complexity_level: ComplexityLevel
    estimated_steps: int
    requires_authentication: bool = True
    ui_patterns_expected: List[str] = field(default_factory=list)
    additional_context: Dict[str, Any] = field(default_factory=dict)
    
    # Workflow intelligence fields
    workflow_type: Optional[str] = None
    requires_template: bool = False
    extracted_values: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ApplicationAnalysis:
    """Application analysis from Test Strategy Agent"""
    app_type: str
    ui_patterns: List[str]
    expected_challenges: List[str]
    timing_requirements: str
    authentication_method: str = "form_based"

@dataclass
class TestApproach:
    """Test approach configuration"""
    primary_method: str
    timeout_strategy: str
    element_strategy: str
    authentication_handling: str
    retry_policy: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionPhase:
    """Individual phase in test execution plan"""
    phase: str
    actions: List[str]
    critical: bool = False
    timeout: int = 30000
    retry_attempts: int = 3

@dataclass
class TestStrategy:
    """Complete test strategy from Test Strategy Agent"""
    strategy_name: str
    application_analysis: ApplicationAnalysis
    test_approach: TestApproach
    execution_plan: List[ExecutionPhase]
    risk_assessment: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BrowserConfig:
    """Browser configuration for test execution"""
    headless: bool = True
    slow_mo: int = 1000
    timeout: int = 30000
    viewport_width: int = 1920
    viewport_height: int = 1080

@dataclass
class TestStep:
    """Individual test step with all execution details"""
    step_id: int
    action: TestActionType
    description: str
    target: str
    primary_selector: str
    fallback_selectors: List[str] = field(default_factory=list)
    timeout: int = 30000
    wait_condition: str = "networkidle"
    value: Optional[str] = None
    verification: Optional[str] = None
    critical: bool = False
    screenshot_after: bool = False
    retry_attempts: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestScript:
    """Complete test script from Test Generation Agent"""
    test_name: str
    setup_steps: List[Dict[str, Any]]
    test_steps: List[TestStep]
    cleanup_steps: List[Dict[str, Any]]
    estimated_duration: int = 0
    requirements: List[str] = field(default_factory=list)

@dataclass
class StepExecutionResult:
    """Result of executing a single test step"""
    step_id: int
    action: TestActionType
    description: str
    target: str
    status: TestStatus
    start_time: str
    end_time: Optional[str] = None
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    selector_used: Optional[str] = None
    retry_count: int = 0
    healing_applied: bool = False
    execution_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestExecutionSummary:
    """Summary statistics for test execution"""
    total_steps: int
    passed: int
    failed: int
    skipped: int
    success_rate: float
    total_duration: float
    average_step_duration: float
    healing_success_rate: float = 0.0

@dataclass
class TestResults:
    """Complete test execution results"""
    test_name: str
    start_time: str
    end_time: Optional[str] = None
    status: TestStatus = TestStatus.PENDING
    step_results: List[StepExecutionResult] = field(default_factory=list)
    summary: Optional[TestExecutionSummary] = None
    screenshots: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

@dataclass
class AgentResult:
    """Result from individual agent execution"""
    agent_name: str
    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestExecutionResult:
    """Complete result from AI Controller execution"""
    execution_id: str
    user_input: str
    start_time: str
    end_time: Optional[str] = None
    status: TestStatus = TestStatus.PENDING
    agent_results: Dict[str, AgentResult] = field(default_factory=dict)
    test_results: Optional[TestResults] = None
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

# Element Detection Models
@dataclass
class ElementSelector:
    """Element selector with confidence and metadata"""
    selector: str
    selector_type: str  # css, xpath, text, etc.
    confidence: float
    source: str  # primary, ai_generated, fallback
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ElementDetectionResult:
    """Result of element detection attempt"""
    found: bool
    selector_used: Optional[ElementSelector] = None
    fallback_attempted: bool = False
    ai_assistance_used: bool = False
    error: Optional[str] = None
    detection_time: float = 0.0

@dataclass
class SelfHealingResult:
    """Result of self-healing attempt"""
    success: bool
    strategy_used: str
    original_error: str
    healing_action: str
    new_selector: Optional[str] = None
    healing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

# Configuration Models
@dataclass
class AgentConfiguration:
    """Configuration for individual agents"""
    temperature: float
    timeout: int = 30
    retry_attempts: int = 3
    enable_learning: bool = True

@dataclass
class SystemConfiguration:
    """Overall system configuration"""
    azure_openai: Dict[str, Any]
    browser_config: Dict[str, Any]
    agents: Dict[str, AgentConfiguration]
    storage: Dict[str, Any]
    reporting: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)

# Utility functions for data validation and conversion
def validate_test_step(step_data: Dict[str, Any]) -> TestStep:
    """Validate and convert dictionary to TestStep"""
    required_fields = ['step_id', 'action', 'description', 'target', 'primary_selector']
    
    for field in required_fields:
        if field not in step_data:
            raise ValueError(f"Missing required field: {field}")
    
    # Convert action to enum
    if isinstance(step_data['action'], str):
        step_data['action'] = TestActionType(step_data['action'])
    
    return TestStep(**step_data)

def calculate_test_summary(step_results: List[StepExecutionResult]) -> TestExecutionSummary:
    """Calculate test execution summary from step results"""
    total_steps = len(step_results)
    
    if total_steps == 0:
        return TestExecutionSummary(
            total_steps=0,
            passed=0,
            failed=0,
            skipped=0,
            success_rate=0.0,
            total_duration=0.0,
            average_step_duration=0.0
        )
    
    passed = sum(1 for step in step_results if step.status == TestStatus.COMPLETED)
    failed = sum(1 for step in step_results if step.status == TestStatus.FAILED)
    skipped = sum(1 for step in step_results if step.status == TestStatus.SKIPPED)
    
    success_rate = (passed / total_steps) * 100
    
    # Calculate durations (simplified - would need actual time parsing)
    total_duration = total_steps * 5.0  # Estimated execution time per step
    average_step_duration = total_duration / total_steps if total_steps > 0 else 0.0
    
    healing_attempts = sum(1 for step in step_results if step.healing_applied)
    healing_success_rate = (healing_attempts / total_steps) * 100 if total_steps > 0 else 0.0
    
    return TestExecutionSummary(
        total_steps=total_steps,
        passed=passed,
        failed=failed,
        skipped=skipped,
        success_rate=round(success_rate, 2),
        total_duration=total_duration,
        average_step_duration=round(average_step_duration, 2),
        healing_success_rate=round(healing_success_rate, 2)
    )

def create_user_intent_from_dict(data: Dict[str, Any]) -> UserIntent:
    """Create UserIntent from dictionary with validation"""
    
    # Convert string enums
    if 'intent_type' in data and isinstance(data['intent_type'], str):
        data['intent_type'] = IntentType(data['intent_type'])
    
    if 'complexity_level' in data and isinstance(data['complexity_level'], str):
        data['complexity_level'] = ComplexityLevel(data['complexity_level'])
    
    return UserIntent(**data)

def create_test_strategy_from_dict(data: Dict[str, Any]) -> TestStrategy:
    """Create TestStrategy from dictionary with validation"""
    
    # Convert nested objects
    if 'application_analysis' in data:
        data['application_analysis'] = ApplicationAnalysis(**data['application_analysis'])
    
    if 'test_approach' in data:
        data['test_approach'] = TestApproach(**data['test_approach'])
    
    if 'execution_plan' in data:
        data['execution_plan'] = [ExecutionPhase(**phase) for phase in data['execution_plan']]
    
    return TestStrategy(**data)

def create_test_script_from_dict(data: Dict[str, Any]) -> TestScript:
    """Create TestScript from dictionary with validation"""
    
    # Convert test steps
    if 'test_steps' in data:
        test_steps = []
        for step_data in data['test_steps']:
            if isinstance(step_data, dict):
                test_steps.append(validate_test_step(step_data))
            else:
                test_steps.append(step_data)
        data['test_steps'] = test_steps
    
    return TestScript(**data)

# Example usage and testing
if __name__ == "__main__":
    # Test data model creation
    print("Testing data models...")
    
    # Test UserIntent creation
    intent_data = {
        "intent_type": "login",
        "target_application": "Cisco Catalyst Centre",
        "primary_actions": ["navigate", "enter_credentials", "verify_login"],
        "test_objectives": ["successful_authentication", "dashboard_access"],
        "complexity_level": "simple",
        "estimated_steps": 3,
        "requires_authentication": True,
        "ui_patterns_expected": ["forms", "navigation"]
    }
    
    user_intent = create_user_intent_from_dict(intent_data)
    print(f"✅ UserIntent created: {user_intent.intent_type}")
    
    # Test TestStep creation
    step_data = {
        "step_id": 1,
        "action": "click",
        "description": "Click login button",
        "target": "Login button",
        "primary_selector": "#login-btn",
        "fallback_selectors": ["button[type='submit']", "input[value='Login']"],
        "critical": True
    }
    
    test_step = validate_test_step(step_data)
    print(f"✅ TestStep created: {test_step.action}")
    
    print("All data models working correctly!")