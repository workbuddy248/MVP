# src/workflow_definitions/tdd_parser.py
"""
TDD File Parser - Converts .TDD files into structured workflow definitions
Supports multiple workflow types for Cisco Catalyst Centre automation
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TDDField:
    """Represents a field extracted from TDD file"""
    field_id: str
    label: str
    field_type: str
    required: bool
    default_value: Any
    description: str
    validation: Dict[str, Any]
    options: Optional[List[str]] = None

@dataclass
class TDDStep:
    """Represents a test step from TDD file"""
    step_id: int
    action: str
    description: str
    selector: str
    value: Optional[str]
    verification: str
    critical: bool

@dataclass
class WorkflowDefinition:
    """Complete workflow definition parsed from TDD"""
    workflow_id: str
    workflow_name: str
    description: str
    category: str
    prerequisites: List[str]
    fields: List[TDDField]
    steps: List[TDDStep]
    estimated_duration: int

class TDDParser:
    """
    Parses .TDD files and converts them into structured workflow definitions
    Supports various Cisco Catalyst Centre workflow patterns
    """
    
    def __init__(self):
        self.field_patterns = {
            'text': r'(?i)(name|title|label|identifier|id)(?:\s+field)?',
            'number': r'(?i)(asn|vlan|port|count|size|timeout|delay)',
            'boolean': r'(?i)(enable|disable|allow|block|active|inactive)',
            'dropdown': r'(?i)(type|mode|protocol|hierarchy|site|location)',
            'url': r'(?i)(url|endpoint|address|host)',
            'password': r'(?i)(password|secret|key|token)',
            'email': r'(?i)(email|mail|contact)',
            'ip': r'(?i)(ip|address|subnet|gateway|dns)',
        }
        
        self.action_patterns = {
            'navigate': r'(?i)(navigate|go\s+to|open|visit)',
            'click': r'(?i)(click|select|choose|press)',
            'type': r'(?i)(type|enter|input|fill)',
            'wait': r'(?i)(wait|pause|delay)',
            'verify': r'(?i)(verify|check|validate|assert|confirm)',
            'screenshot': r'(?i)(screenshot|capture|image)',
        }
        
        self.workflow_categories = {
            'fabric': ['fabric', 'network fabric', 'sda'],
            'device_group': ['device group', 'group', 'device management'],
            'network_hierarchy': ['hierarchy', 'site hierarchy', 'network structure'],
            'device_provisioning': ['provision', 'deployment', 'device setup'],
            'vlan': ['vlan', 'virtual lan', 'network segmentation'],
            'policy': ['policy', 'access control', 'security policy'],
            'template': ['template', 'configuration template'],
        }

    def parse_tdd_file(self, file_path: Path) -> WorkflowDefinition:
        """Parse a single TDD file into a WorkflowDefinition"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Extract workflow metadata
            workflow_info = self._extract_workflow_info(content, file_path.stem)
            
            # Extract fields and their properties
            fields = self._extract_fields(content)
            
            # Extract test steps
            steps = self._extract_steps(content)
            
            # Extract prerequisites
            prerequisites = self._extract_prerequisites(content, workflow_info['workflow_id'])
            
            return WorkflowDefinition(
                workflow_id=workflow_info['workflow_id'],
                workflow_name=workflow_info['workflow_name'],
                description=workflow_info['description'],
                category=workflow_info['category'],
                prerequisites=prerequisites,
                fields=fields,
                steps=steps,
                estimated_duration=workflow_info['estimated_duration']
            )
            
        except Exception as e:
            logger.error(f"Failed to parse TDD file {file_path}: {e}")
            raise

    def _extract_workflow_info(self, content: str, filename: str) -> Dict[str, Any]:
        """Extract basic workflow information"""
        # Extract title/name
        title_match = re.search(r'(?i)(?:title|name|workflow):\s*(.+)', content)
        title = title_match.group(1).strip() if title_match else filename.replace('_', ' ').title()
        
        # Extract description
        desc_match = re.search(r'(?i)(?:description|summary|purpose):\s*(.+)', content)
        description = desc_match.group(1).strip() if desc_match else f"Automated test for {title}"
        
        # Determine workflow category
        category = self._determine_category(content, filename)
        
        # Generate workflow ID
        workflow_id = filename.lower().replace(' ', '_').replace('-', '_')
        
        # Estimate duration based on content complexity
        step_count = len(re.findall(r'(?i)step\s+\d+', content))
        estimated_duration = max(300, step_count * 30)  # Minimum 5 minutes
        
        return {
            'workflow_id': workflow_id,
            'workflow_name': title,
            'description': description,
            'category': category,
            'estimated_duration': estimated_duration
        }

    def _determine_category(self, content: str, filename: str) -> str:
        """Determine workflow category based on content and filename"""
        content_lower = content.lower()
        filename_lower = filename.lower()
        
        for category, keywords in self.workflow_categories.items():
            for keyword in keywords:
                if keyword in content_lower or keyword in filename_lower:
                    return category
        
        return 'general'

    def _extract_fields(self, content: str) -> List[TDDField]:
        """Extract field definitions from TDD content"""
        fields = []
        field_counter = 1
        
        # Look for field patterns in various formats
        field_patterns = [
            r'(?i)(?:field|input|parameter|value)[\s:]*([^:\n]+):\s*([^\n]+)',
            r'(?i)([a-zA-Z_][a-zA-Z0-9_\s]+):\s*\[([^\]]+)\]',
            r'(?i)enter\s+([^:\n]+):\s*([^\n]+)',
            r'(?i)provide\s+([^:\n]+):\s*([^\n]+)',
        ]
        
        # Global fields that appear in most workflows
        global_fields = [
            TDDField(
                field_id="target_url",
                label="Target URL",
                field_type="url",
                required=True,
                default_value="https://catalyst.cisco.com",
                description="Cisco Catalyst Centre URL",
                validation={"pattern": r"^https?://.*"}
            ),
            TDDField(
                field_id="username",
                label="Username",
                field_type="text",
                required=True,
                default_value="admin",
                description="Login username",
                validation={"min_length": 3, "max_length": 50}
            ),
            TDDField(
                field_id="password",
                label="Password",
                field_type="password",
                required=True,
                default_value="admin123",
                description="Login password",
                validation={"min_length": 6}
            )
        ]
        
        fields.extend(global_fields)
        
        for pattern in field_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                field_name = match[0].strip()
                field_value = match[1].strip() if len(match) > 1 else ""
                
                # Skip if already processed
                if any(f.label.lower() == field_name.lower() for f in fields):
                    continue
                
                field = self._create_field_definition(field_name, field_value, field_counter)
                if field:
                    fields.append(field)
                    field_counter += 1
        
        # Add common workflow-specific fields if not found
        content_lower = content.lower()
        
        if 'fabric' in content_lower:
            fabric_fields = [
                TDDField(
                    field_id="fabric_name",
                    label="Fabric Name",
                    field_type="text",
                    required=True,
                    default_value="Test-Fabric-001",
                    description="Name for the network fabric",
                    validation={"pattern": r"^[a-zA-Z0-9_-]+$", "max_length": 64}
                ),
                TDDField(
                    field_id="bgp_asn",
                    label="BGP ASN",
                    field_type="number",
                    required=True,
                    default_value="65001",
                    description="BGP Autonomous System Number",
                    validation={"min": 1, "max": 65535}
                )
            ]
            fields.extend([f for f in fabric_fields if not any(ef.field_id == f.field_id for ef in fields)])
        
        if 'device' in content_lower and 'group' in content_lower:
            device_group_fields = [
                TDDField(
                    field_id="group_name",
                    label="Device Group Name",
                    field_type="text",
                    required=True,
                    default_value="Test-Group-001",
                    description="Name for the device group",
                    validation={"pattern": r"^[a-zA-Z0-9_-]+$", "max_length": 64}
                )
            ]
            fields.extend([f for f in device_group_fields if not any(ef.field_id == f.field_id for ef in fields)])
        
        return fields

    def _create_field_definition(self, field_name: str, field_value: str, counter: int) -> Optional[TDDField]:
        """Create a field definition from extracted text"""
        field_id = re.sub(r'[^a-zA-Z0-9_]', '_', field_name.lower()).strip('_')
        
        # Determine field type
        field_type = self._determine_field_type(field_name, field_value)
        
        # Extract default value and options
        default_value, options = self._extract_field_value_and_options(field_value, field_type)
        
        # Create validation rules
        validation = self._create_validation_rules(field_type, field_name)
        
        return TDDField(
            field_id=field_id,
            label=field_name.title(),
            field_type=field_type,
            required=True,  # Default to required
            default_value=default_value,
            description=f"Value for {field_name}",
            validation=validation,
            options=options
        )

    def _determine_field_type(self, field_name: str, field_value: str) -> str:
        """Determine field type based on name and value patterns"""
        combined_text = f"{field_name} {field_value}".lower()
        
        for field_type, pattern in self.field_patterns.items():
            if re.search(pattern, combined_text):
                return field_type
        
        # Additional heuristics
        if 'true' in field_value.lower() or 'false' in field_value.lower():
            return 'boolean'
        
        if re.search(r'\d+\.\d+\.\d+\.\d+', field_value):
            return 'ip'
        
        if '|' in field_value or 'choose' in field_value.lower():
            return 'dropdown'
        
        return 'text'  # Default

    def _extract_field_value_and_options(self, field_value: str, field_type: str) -> Tuple[Any, Optional[List[str]]]:
        """Extract default value and options from field value string"""
        options = None
        
        # Handle dropdown options
        if '|' in field_value:
            parts = [part.strip() for part in field_value.split('|')]
            options = parts
            default_value = parts[0] if parts else ""
        
        # Handle boolean values
        elif field_type == 'boolean':
            default_value = 'true' in field_value.lower()
        
        # Handle numeric values
        elif field_type == 'number':
            numbers = re.findall(r'\d+', field_value)
            default_value = numbers[0] if numbers else "1"
        
        # Handle text values
        else:
            # Remove common prefixes/suffixes
            cleaned_value = re.sub(r'(?i)^(enter|input|provide|type)\s+', '', field_value)
            cleaned_value = re.sub(r'(?i)\s+(here|value|field)$', '', cleaned_value)
            default_value = cleaned_value.strip() or "test_value"
        
        return default_value, options

    def _create_validation_rules(self, field_type: str, field_name: str) -> Dict[str, Any]:
        """Create validation rules based on field type and name"""
        validation = {}
        
        if field_type == 'text':
            validation.update({"min_length": 1, "max_length": 255})
            
            if 'name' in field_name.lower():
                validation["pattern"] = r"^[a-zA-Z0-9_-]+$"
        
        elif field_type == 'number':
            validation.update({"min": 1, "max": 999999})
            
            if 'asn' in field_name.lower():
                validation.update({"min": 1, "max": 65535})
            elif 'vlan' in field_name.lower():
                validation.update({"min": 1, "max": 4094})
        
        elif field_type == 'url':
            validation["pattern"] = r"^https?://.*"
        
        elif field_type == 'email':
            validation["pattern"] = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        
        elif field_type == 'ip':
            validation["pattern"] = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        
        return validation

    def _extract_steps(self, content: str) -> List[TDDStep]:
        """Extract test steps from TDD content"""
        steps = []
        
        # Pattern to match step definitions
        step_patterns = [
            r'(?i)step\s+(\d+)[\s:]*([^\n]+)',
            r'(?i)(\d+)\.?\s+([^\n]+)',
            r'(?i)action\s+(\d+)[\s:]*([^\n]+)',
        ]
        
        step_id = 1
        for pattern in step_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                step_num = int(match[0]) if match[0].isdigit() else step_id
                step_desc = match[1].strip()
                
                # Skip if already processed
                if any(s.step_id == step_num for s in steps):
                    continue
                
                step = self._create_step_definition(step_num, step_desc)
                if step:
                    steps.append(step)
                    step_id = max(step_id, step_num) + 1
        
        # If no steps found, create basic workflow steps
        if not steps:
            steps = self._create_default_steps(content)
        
        return sorted(steps, key=lambda x: x.step_id)

    def _create_step_definition(self, step_id: int, description: str) -> Optional[TDDStep]:
        """Create a step definition from description"""
        # Determine action type
        action = self._determine_action_type(description)
        
        # Extract selector information
        selector = self._extract_selector(description, action)
        
        # Extract value if any
        value = self._extract_step_value(description, action)
        
        # Create verification statement
        verification = self._create_verification(description, action)
        
        # Determine if step is critical
        critical = action in ['navigate', 'click', 'type'] or 'login' in description.lower()
        
        return TDDStep(
            step_id=step_id,
            action=action,
            description=description,
            selector=selector,
            value=value,
            verification=verification,
            critical=critical
        )

    def _determine_action_type(self, description: str) -> str:
        """Determine step action type from description"""
        desc_lower = description.lower()
        
        for action, pattern in self.action_patterns.items():
            if re.search(pattern, desc_lower):
                return action
        
        # Additional heuristics
        if any(word in desc_lower for word in ['login', 'sign in', 'authenticate']):
            return 'type'  # Usually involves typing credentials
        
        if any(word in desc_lower for word in ['submit', 'save', 'apply', 'create']):
            return 'click'
        
        return 'wait'  # Default action

    def _extract_selector(self, description: str, action: str) -> str:
        """Extract CSS selector hints from step description"""
        desc_lower = description.lower()
        
        # Common selector patterns based on description
        selector_map = {
            'login': "input[type='text'], input[name*='user']",
            'password': "input[type='password']",
            'username': "input[type='text'], input[name*='user']",
            'submit': "button[type='submit'], input[type='submit']",
            'save': "button:contains('Save'), input[value*='Save']",
            'create': "button:contains('Create'), input[value*='Create']",
            'next': "button:contains('Next'), input[value*='Next']",
            'menu': "nav, ul.nav, div.navbar",
            'link': "a[href]",
            'button': "button, input[type='button']",
            'dropdown': "select, div.dropdown",
            'checkbox': "input[type='checkbox']",
            'radio': "input[type='radio']",
        }
        
        for keyword, selector in selector_map.items():
            if keyword in desc_lower:
                return selector
        
        # Default selectors based on action
        action_selectors = {
            'navigate': "",
            'click': "button, a, input[type='submit']",
            'type': "input[type='text'], textarea",
            'wait': "",
            'verify': "",
            'screenshot': "",
        }
        
        return action_selectors.get(action, "")

    def _extract_step_value(self, description: str, action: str) -> Optional[str]:
        """Extract input value from step description"""
        if action != 'type':
            return None
        
        # Look for quoted values
        quoted_match = re.search(r'["\']([^"\']+)["\']', description)
        if quoted_match:
            return quoted_match.group(1)
        
        # Look for specific value patterns
        value_patterns = [
            r'(?i)enter\s+([^\s]+)',
            r'(?i)type\s+([^\s]+)',
            r'(?i)input\s+([^\s]+)',
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1)
        
        return None

    def _create_verification(self, description: str, action: str) -> str:
        """Create verification statement for the step"""
        if action == 'navigate':
            return "Page loads successfully and expected elements are visible"
        elif action == 'click':
            return "Element is clicked and expected response occurs"
        elif action == 'type':
            return "Value is entered correctly in the field"
        elif action == 'wait':
            return "Expected condition is met"
        elif action == 'verify':
            return description
        else:
            return f"Step '{description}' completes successfully"

    def _create_default_steps(self, content: str) -> List[TDDStep]:
        """Create default workflow steps when none are explicitly defined"""
        steps = [
            TDDStep(1, "navigate", "Navigate to application URL", "", "target_url", 
                   "Application page loads successfully", True),
            TDDStep(2, "type", "Enter username", "input[type='text'], input[name*='user']", "username",
                   "Username is entered correctly", True),
            TDDStep(3, "type", "Enter password", "input[type='password']", "password",
                   "Password is entered correctly", True),
            TDDStep(4, "click", "Click login button", "button[type='submit'], input[type='submit']", None,
                   "Login is successful", True),
        ]
        
        # Add workflow-specific steps based on content
        content_lower = content.lower()
        step_id = 5
        
        if 'fabric' in content_lower:
            steps.extend([
                TDDStep(step_id, "click", "Navigate to fabric section", "a:contains('Fabric'), nav a[href*='fabric']", None,
                       "Fabric section is accessible", True),
                TDDStep(step_id + 1, "click", "Click create fabric", "button:contains('Create'), button:contains('Add')", None,
                       "Create fabric dialog opens", True),
                TDDStep(step_id + 2, "type", "Enter fabric name", "input[name*='name'], input[id*='name']", "fabric_name",
                       "Fabric name is entered", True),
                TDDStep(step_id + 3, "click", "Save fabric", "button:contains('Save'), button:contains('Create')", None,
                       "Fabric is created successfully", True),
            ])
        
        return steps

    def _extract_prerequisites(self, content: str, workflow_id: str) -> List[str]:
        """Extract workflow prerequisites from content"""
        prerequisites = []
        content_lower = content.lower()
        
        # Explicit prerequisite patterns
        prereq_patterns = [
            r'(?i)prerequisite[s]?:\s*([^\n]+)',
            r'(?i)requires?:\s*([^\n]+)',
            r'(?i)depends?\s+on:\s*([^\n]+)',
            r'(?i)before\s+running:\s*([^\n]+)',
        ]
        
        for pattern in prereq_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                prereq_items = [item.strip() for item in match.split(',')]
                prerequisites.extend(prereq_items)
        
        # Implicit prerequisites based on workflow type
        if 'device' in workflow_id and 'group' in workflow_id:
            prerequisites.append('network_hierarchy')
            if 'fabric' not in workflow_id:
                prerequisites.append('create_fabric')
        
        elif 'fabric' in workflow_id:
            prerequisites.append('network_hierarchy')
        
        # Common prerequisite: authentication
        if not any('login' in p.lower() for p in prerequisites):
            prerequisites.insert(0, 'authentication')
        
        return list(set(prerequisites))  # Remove duplicates

    def parse_all_tdd_files(self, tdd_directory: Path) -> Dict[str, WorkflowDefinition]:
        """Parse all TDD files in a directory"""
        workflows = {}
        
        if not tdd_directory.exists():
            logger.warning(f"TDD directory does not exist: {tdd_directory}")
            return workflows
        
        tdd_files = list(tdd_directory.glob("*.tdd")) + list(tdd_directory.glob("*.tdd.md"))
        
        if not tdd_files:
            logger.warning(f"No TDD files found in: {tdd_directory}")
            return workflows
        
        for tdd_file in tdd_files:
            try:
                workflow = self.parse_tdd_file(tdd_file)
                workflows[workflow.workflow_id] = workflow
                logger.info(f"Successfully parsed TDD file: {tdd_file.name}")
            except Exception as e:
                logger.error(f"Failed to parse TDD file {tdd_file.name}: {e}")
        
        return workflows

    def generate_template_json(self, workflow: WorkflowDefinition) -> Dict[str, Any]:
        """Generate template JSON from workflow definition"""
        return {
            "workflow_id": workflow.workflow_id,
            "workflow_name": workflow.workflow_name,
            "description": workflow.description,
            "category": workflow.category,
            "estimated_duration": workflow.estimated_duration,
            "dependencies": workflow.prerequisites,
            "fields": [
                {
                    "field_id": field.field_id,
                    "label": field.label,
                    "type": field.field_type,
                    "required": field.required,
                    "default_value": field.default_value,
                    "description": field.description,
                    "validation": field.validation,
                    "options": field.options
                }
                for field in workflow.fields
            ],
            "steps": [
                {
                    "step_id": step.step_id,
                    "action": step.action,
                    "description": step.description,
                    "selector": step.selector,
                    "value": step.value,
                    "verification": step.verification,
                    "critical": step.critical
                }
                for step in workflow.steps
            ]
        }
