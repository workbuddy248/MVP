# src/models/workflow_models.py
"""
Workflow-related data models and structures
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class WorkflowStatus(Enum):
    PENDING = "pending"
    TEMPLATE_REQUIRED = "template_required"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class FieldType(Enum):
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DROPDOWN = "dropdown"
    URL = "url"
    PASSWORD = "password"
    EMAIL = "email"
    IP = "ip"

@dataclass
class WorkflowDetectionResult:
    """Result of workflow detection from user input"""
    detected: bool
    workflow_id: Optional[str]
    confidence_score: float
    extracted_values: Dict[str, Any]
    intent_type: str
    requires_template: bool
    error_message: Optional[str] = None

@dataclass
class WorkflowTemplate:
    """Template structure for workflow customization"""
    workflow_id: str
    workflow_name: str
    description: str
    category: str
    estimated_duration: int
    dependencies: List[str]
    fields: List[Dict[str, Any]]
    dependency_questions: List[Dict[str, Any]]
    global_fields: List[Dict[str, Any]]

@dataclass
class WorkflowValidationResult:
    """Result of workflow template validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    validated_values: Dict[str, Any]

@dataclass
class EnhancedWorkflow:
    """Enhanced workflow with dependencies and user values"""
    main_workflow: str
    included_workflows: List[str]
    user_values: Dict[str, Any]
    resolved_dependencies: Dict[str, Any]
    complete_test_steps: List[Dict[str, Any]]
    estimated_total_duration: int

@dataclass
class WorkflowExecutionRequest:
    """Request structure for workflow execution"""
    workflow_id: str
    user_values: Dict[str, Any]
    dependency_responses: Dict[str, Any]
    test_type: str = "functional"
    timeout_config: Optional[Dict[str, int]] = None

@dataclass
class WorkflowExecutionResponse:
    """Response structure for workflow execution"""
    execution_id: str
    status: WorkflowStatus
    workflow_template: Optional[WorkflowTemplate]
    enhanced_workflow: Optional[EnhancedWorkflow]
    generated_test: Optional[Dict[str, Any]]
    error_message: Optional[str]
    next_action: str  # "customize_template", "execute_test", "show_results"

class WorkflowCategory:
    """Workflow category constants"""
    FABRIC = "fabric"
    DEVICE_GROUP = "device_group"
    NETWORK_HIERARCHY = "network_hierarchy"
    DEVICE_PROVISIONING = "device_provisioning"
    INVENTORY = "inventory"
    VLAN = "vlan"
    POLICY = "policy"
    TEMPLATE = "template"
    GENERAL = "general"

class WorkflowKeywords:
    """Common workflow detection keywords"""
    FABRIC_KEYWORDS = [
        "fabric", "network fabric", "sda", "software defined access",
        "create fabric", "setup fabric", "configure fabric"
    ]
    
    DEVICE_GROUP_KEYWORDS = [
        "device group", "group", "device management", "create group",
        "setup group", "device collection"
    ]
    
    HIERARCHY_KEYWORDS = [
        "hierarchy", "site hierarchy", "network structure", "site structure",
        "create hierarchy", "setup sites", "network topology", "area", "building",
        "create area", "add area", "setup area", "create building", "add building",
        "setup building", "network hierarchy", "global area", "site management",
        "area management", "building management", "campus", "floor"
    ]
    
    PROVISIONING_KEYWORDS = [
        "provision", "deployment", "device setup", "device provisioning",
        "deploy device", "configure device", "device deployment"
    ]
    
    VLAN_KEYWORDS = [
        "vlan", "virtual lan", "network segmentation", "create vlan",
        "configure vlan", "vlan setup", "network isolation"
    ]
    
    INVENTORY_KEYWORDS = [
        "inventory", "device inventory", "import devices", "device import",
        "import inventory", "add devices", "upload devices", "device file",
        "inventory file", "provision devices", "assign devices", "device assignment",
        "bulk import", "csv import", "device list", "inventory management"
    ]

    @classmethod
    def get_all_keywords(cls) -> Dict[str, List[str]]:
        """Get all workflow keywords grouped by category"""
        return {
            WorkflowCategory.FABRIC: cls.FABRIC_KEYWORDS,
            WorkflowCategory.DEVICE_GROUP: cls.DEVICE_GROUP_KEYWORDS,
            WorkflowCategory.NETWORK_HIERARCHY: cls.HIERARCHY_KEYWORDS,
            WorkflowCategory.DEVICE_PROVISIONING: cls.PROVISIONING_KEYWORDS,
            WorkflowCategory.INVENTORY: cls.INVENTORY_KEYWORDS,
            WorkflowCategory.VLAN: cls.VLAN_KEYWORDS,
        }

class WorkflowActions:
    """Standard workflow action types"""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    WAIT = "wait"
    VERIFY = "verify"
    SCREENSHOT = "screenshot"
    SELECT = "select"
    UPLOAD = "upload"
    DOWNLOAD = "download"

class TimeoutConfig:
    """Timeout configuration constants"""
    PAGE_LOAD_TIMEOUT = 300000  # 300 seconds
    ACTION_TIMEOUT = 180000     # 180 seconds
    ELEMENT_WAIT = 180000       # 180 seconds
    NAVIGATION_TIMEOUT = 300000 # 300 seconds
    FORM_SUBMISSION = 180000    # 180 seconds
    
    @classmethod
    def get_timeout_config(cls) -> Dict[str, int]:
        """Get complete timeout configuration"""
        return {
            "page_load": cls.PAGE_LOAD_TIMEOUT,
            "action_timeout": cls.ACTION_TIMEOUT,
            "element_wait": cls.ELEMENT_WAIT,
            "navigation": cls.NAVIGATION_TIMEOUT,
            "form_submission": cls.FORM_SUBMISSION
        }

class ValidationRules:
    """Common validation rule patterns"""
    
    @staticmethod
    def get_text_validation(min_length: int = 1, max_length: int = 255, pattern: Optional[str] = None) -> Dict[str, Any]:
        """Get text field validation rules"""
        rules = {"min_length": min_length, "max_length": max_length}
        if pattern:
            rules["pattern"] = pattern
        return rules
    
    @staticmethod
    def get_number_validation(min_val: int = 1, max_val: int = 999999) -> Dict[str, Any]:
        """Get number field validation rules"""
        return {"min": min_val, "max": max_val}
    
    @staticmethod
    def get_url_validation() -> Dict[str, Any]:
        """Get URL field validation rules"""
        return {"pattern": r"^https?://.*"}
    
    @staticmethod
    def get_email_validation() -> Dict[str, Any]:
        """Get email field validation rules"""
        return {"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"}
    
    @staticmethod
    def get_ip_validation() -> Dict[str, Any]:
        """Get IP address field validation rules"""
        return {"pattern": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"}

class DefaultValues:
    """Default values for common fields"""
    
    # Global defaults
    TARGET_URL = "https://catalyst.cisco.com"
    USERNAME = "admin"
    PASSWORD = "admin123"
    
    # Fabric defaults
    FABRIC_NAME = "Test-Fabric-001"
    BGP_ASN = "65001"
    
    # Device group defaults
    DEVICE_GROUP_NAME = "Test-Group-001"
    
    # VLAN defaults
    VLAN_ID = "100"
    VLAN_NAME = "Test-VLAN-100"
    
    # Network hierarchy defaults
    SITE_HIERARCHY = "Global/USA/Campus1"
    
    @classmethod
    def get_global_fields(cls) -> List[Dict[str, Any]]:
        """Get standard global fields for all workflows"""
        return [
            {
                "field_id": "target_url",
                "label": "Target URL",
                "type": "url",
                "required": True,
                "default_value": cls.TARGET_URL,
                "description": "Cisco Catalyst Centre URL",
                "validation": ValidationRules.get_url_validation()
            },
            {
                "field_id": "username",
                "label": "Username",
                "type": "text",
                "required": True,
                "default_value": cls.USERNAME,
                "description": "Login username",
                "validation": ValidationRules.get_text_validation(min_length=3, max_length=50)
            },
            {
                "field_id": "password",
                "label": "Password",
                "type": "password",
                "required": True,
                "default_value": cls.PASSWORD,
                "description": "Login password",
                "validation": ValidationRules.get_text_validation(min_length=6)
            }
        ]
