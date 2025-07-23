# src/agents/workflow_intelligence_agent.py
"""
Workflow Intelligence Agent - Detects workflows and generates customizable templates
Handles complex workflow expansion and dependency resolution
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from ..models.workflow_models import (
    WorkflowDetectionResult, WorkflowTemplate, EnhancedWorkflow, 
    WorkflowValidationResult, WorkflowCategory, WorkflowKeywords,
    TimeoutConfig, DefaultValues
)
from ..workflow_definitions.workflow_registry import WorkflowRegistry
from ..core.azure_client import AzureOpenAIClient, AIResponse

logger = logging.getLogger(__name__)

class WorkflowIntelligenceAgent:
    """
    Intelligent workflow detection and template generation agent
    Integrates with NLProcessor to enhance workflow-based instructions
    """
    
    def __init__(self, azure_client: AzureOpenAIClient, config_path: Path):
        self.azure_client = azure_client
        self.config_path = config_path
        
        # Initialize workflow registry
        tdd_directory = config_path.parent / "tdd_files"
        templates_directory = config_path / "workflow_definitions" / "templates"
        self.registry = WorkflowRegistry(tdd_directory, templates_directory)
        
        # Load dependencies configuration
        deps_file = config_path / "workflow_definitions" / "dependencies" / "workflow_dependencies.json"
        self.dependencies_config = self._load_dependencies(deps_file)
        
        # Workflow detection patterns
        self.detection_patterns = self._build_detection_patterns()
        
        logger.info("WorkflowIntelligenceAgent initialized")

    def _load_dependencies(self, deps_file: Path) -> Dict[str, Any]:
        """Load workflow dependencies configuration"""
        try:
            if deps_file.exists():
                return json.loads(deps_file.read_text())
            else:
                logger.warning(f"Dependencies file not found: {deps_file}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load dependencies: {e}")
            return {}

    def _build_detection_patterns(self) -> Dict[str, List[str]]:
        """Build regex patterns for workflow detection"""
        patterns = {}
        
        # Get keywords from model
        keyword_groups = WorkflowKeywords.get_all_keywords()
        
        for category, keywords in keyword_groups.items():
            patterns[category] = []
            for keyword in keywords:
                # Create flexible patterns that match variations
                pattern = r'(?i)\b' + re.escape(keyword).replace(r'\ ', r'\s+') + r'\b'
                patterns[category].append(pattern)
                
                # Add action-based patterns
                action_patterns = [
                    f"create {keyword}",
                    f"setup {keyword}",
                    f"configure {keyword}",
                    f"deploy {keyword}",
                    f"add {keyword}",
                    f"build {keyword}"
                ]
                
                for action_pattern in action_patterns:
                    pattern = r'(?i)\b' + re.escape(action_pattern).replace(r'\ ', r'\s+') + r'\b'
                    patterns[category].append(pattern)
        
        return patterns

    async def detect_workflow(self, user_input: str, parsed_nl_result: Dict[str, Any]) -> WorkflowDetectionResult:
        """
        Detect workflow type from user input and NL processing result
        Combines keyword-based and AI-based detection
        """
        try:
            # First try keyword-based detection
            keyword_result = self._detect_workflow_keywords(user_input)
            
            # If keyword detection is confident, use it
            if keyword_result.detected and keyword_result.confidence_score > 0.7:
                logger.info(f"Workflow detected via keywords: {keyword_result.workflow_id}")
                return keyword_result
            
            # Otherwise use AI-enhanced detection
            ai_result = await self._detect_workflow_ai(user_input, parsed_nl_result)
            
            # Combine results
            if ai_result.detected and ai_result.confidence_score > keyword_result.confidence_score:
                logger.info(f"Workflow detected via AI: {ai_result.workflow_id}")
                return ai_result
            elif keyword_result.detected:
                logger.info(f"Workflow detected via keywords (fallback): {keyword_result.workflow_id}")
                return keyword_result
            else:
                logger.info("No workflow detected")
                return WorkflowDetectionResult(
                    detected=False,
                    workflow_id=None,
                    confidence_score=0.0,
                    extracted_values={},
                    intent_type="simple",
                    requires_template=False
                )
                
        except Exception as e:
            logger.error(f"Error in workflow detection: {e}")
            return WorkflowDetectionResult(
                detected=False,
                workflow_id=None,
                confidence_score=0.0,
                extracted_values={},
                intent_type="error",
                requires_template=False,
                error_message=str(e)
            )

    def _detect_workflow_keywords(self, user_input: str) -> WorkflowDetectionResult:
        """Detect workflow using keyword patterns with priority for specific matches"""
        user_input_lower = user_input.lower()
        best_match = None
        best_score = 0.0
        extracted_values = {}
        category_matches = {}
        
        # First pass: collect all matches for each category
        for category, patterns in self.detection_patterns.items():
            category_matches[category] = []
            for pattern in patterns:
                matches = re.finditer(pattern, user_input_lower)
                for match in matches:
                    match_length = len(match.group())
                    keyword_specificity = match_length  # Longer keywords are more specific
                    context_bonus = 0.1 if any(word in user_input_lower for word in ['create', 'setup', 'configure']) else 0
                    
                    # Calculate base score
                    base_score = (match_length / len(user_input_lower)) + context_bonus
                    
                    # Add specificity bonus for longer, more specific keywords
                    specificity_bonus = keyword_specificity * 0.01
                    
                    # Add category priority bonuses
                    priority_bonus = 0.0
                    if category == WorkflowCategory.INVENTORY:
                        # Prioritize inventory-specific terms
                        inventory_terms = ['inventory', 'import', 'bulk', 'csv', 'upload', 'file']
                        if any(term in match.group() for term in inventory_terms):
                            priority_bonus = 0.3
                    
                    total_score = base_score + specificity_bonus + priority_bonus
                    category_matches[category].append((total_score, match.group(), match_length))
        
        # Second pass: find the best match across all categories
        for category, matches in category_matches.items():
            if matches:
                # Get the best match for this category
                best_category_score = max(matches, key=lambda x: x[0])[0]
                
                if best_category_score > best_score:
                    best_score = best_category_score
                    best_match = category
        
        # Extract values from input
        if best_match:
            extracted_values = self._extract_values_from_input(user_input, best_match)
            
            # Find corresponding workflow ID
            workflow_id = self._category_to_workflow_id(best_match)
            
            return WorkflowDetectionResult(
                detected=True,
                workflow_id=workflow_id,
                confidence_score=min(best_score, 1.0),
                extracted_values=extracted_values,
                intent_type="workflow",
                requires_template=True
            )
        
        return WorkflowDetectionResult(
            detected=False,
            workflow_id=None,
            confidence_score=0.0,
            extracted_values={},
            intent_type="simple",
            requires_template=False
        )

    async def _detect_workflow_ai(self, user_input: str, parsed_nl_result: Dict[str, Any]) -> WorkflowDetectionResult:
        """Use AI to detect workflow with context from NL processing"""
        
        system_prompt = """You are an expert at identifying Cisco Catalyst Centre workflow patterns from user instructions.

Analyze the user input and determine if it represents a complex workflow that requires multiple steps beyond simple navigation/clicking.

Available workflow types:
- create_fabric: Setting up network fabric/SDA
- create_device_group: Creating device groups  
- network_hierarchy: Setting up site hierarchy
- device_provisioning: Provisioning/deploying devices
- configure_vlan: VLAN configuration

Output JSON format:
{
    "workflow_detected": boolean,
    "workflow_id": "workflow_type or null",
    "confidence_score": 0.0-1.0,
    "extracted_values": {
        "field_name": "extracted_value"
    },
    "reasoning": "brief explanation"
}

Look for:
- Complex multi-step processes
- Cisco-specific terminology
- Configuration/setup tasks
- Infrastructure management operations"""

        user_prompt = f"""
User Input: "{user_input}"

NL Processing Result: {json.dumps(parsed_nl_result, indent=2)}

Analyze if this represents a complex Cisco Catalyst Centre workflow requiring template customization.
"""
        
        try:
            response = await self.azure_client.call_agent(
                agent_name="WorkflowDetection",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                temperature=0.1
            )
            
            if response.success and response.content:
                result = response.content
                
                if result.get("workflow_detected", False):
                    ai_workflow_id = result.get("workflow_id")
                    # Apply category mapping for AI-detected workflows
                    mapped_workflow_id = self._map_ai_workflow_id(ai_workflow_id)
                    
                    return WorkflowDetectionResult(
                        detected=True,
                        workflow_id=mapped_workflow_id,
                        confidence_score=result.get("confidence_score", 0.5),
                        extracted_values=result.get("extracted_values", {}),
                        intent_type="workflow",
                        requires_template=True
                    )
            
        except Exception as e:
            logger.error(f"AI workflow detection failed: {e}")
        
        return WorkflowDetectionResult(
            detected=False,
            workflow_id=None,
            confidence_score=0.0,
            extracted_values={},
            intent_type="simple",
            requires_template=False
        )

    def _extract_values_from_input(self, user_input: str, category: str) -> Dict[str, Any]:
        """Extract field values from user input"""
        extracted = {}
        
        # URL extraction
        url_pattern = r'https?://[^\s]+'
        url_match = re.search(url_pattern, user_input)
        if url_match:
            extracted["target_url"] = url_match.group()
        
        # Name extraction (quoted strings or after "name", "called", etc.)
        name_patterns = [
            r'name["\s]+([^"\s]+)',
            r'called["\s]+([^"\s]+)',
            r'"([^"]+)"',
            r"'([^']+)'"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                name_value = match.group(1)
                
                # Assign to appropriate field based on category
                if category == WorkflowCategory.FABRIC:
                    extracted["fabric_name"] = name_value
                elif category == WorkflowCategory.DEVICE_GROUP:
                    extracted["group_name"] = name_value
                else:
                    extracted["name"] = name_value
                break
        
        # Number extraction (ASN, VLAN ID, etc.)
        number_pattern = r'(?:asn|vlan)[\s:]+(\d+)'
        number_match = re.search(number_pattern, user_input, re.IGNORECASE)
        if number_match:
            if "asn" in user_input.lower():
                extracted["bgp_asn"] = number_match.group(1)
            elif "vlan" in user_input.lower():
                extracted["vlan_id"] = number_match.group(1)
        
        return extracted

    def _category_to_workflow_id(self, category: str) -> str:
        """Convert category to workflow ID"""
        category_mapping = {
            WorkflowCategory.FABRIC: "create_fabric",
            WorkflowCategory.DEVICE_GROUP: "create_device_group",
            WorkflowCategory.NETWORK_HIERARCHY: "network_hierarchy",
            WorkflowCategory.DEVICE_PROVISIONING: "device_provisioning.tdd",
            WorkflowCategory.INVENTORY: "inventory_workflow",
            WorkflowCategory.VLAN: "configure_vlan"
        }
        return category_mapping.get(category, category)

    def _map_ai_workflow_id(self, ai_workflow_id: str) -> str:
        """Map AI-detected workflow IDs to correct template IDs"""
        ai_workflow_mapping = {
            "device_provisioning": "device_provisioning.tdd",
            "create_fabric": "create_fabric.tdd",
            "network_hierarchy": "network_hierarchy",
            "inventory_workflow": "inventory_workflow",
            "configure_vlan": "configure_vlan.tdd"
        }
        return ai_workflow_mapping.get(ai_workflow_id, ai_workflow_id)

    async def generate_template(self, workflow_id: str, extracted_values: Dict[str, Any] = None) -> WorkflowTemplate:
        """Generate customizable template for workflow"""
        try:
            # Get base template from registry
            base_template = self.registry.get_template(workflow_id)
            if not base_template:
                raise ValueError(f"Workflow template not found: {workflow_id}")
            
            # Pre-fill extracted values
            if extracted_values:
                self._prefill_template_values(base_template, extracted_values)
            
            # Get dependency questions
            dependency_questions = self._get_dependency_questions(workflow_id)
            
            # Create workflow template
            template = WorkflowTemplate(
                workflow_id=workflow_id,
                workflow_name=base_template["workflow_name"],
                description=base_template["description"],
                category=base_template.get("category", "general"),
                estimated_duration=base_template.get("estimated_duration", 300),
                dependencies=base_template.get("dependencies", []),
                fields=base_template["fields"],
                dependency_questions=dependency_questions,
                global_fields=DefaultValues.get_global_fields()
            )
            
            logger.info(f"Generated template for workflow: {workflow_id}")
            return template
            
        except Exception as e:
            logger.error(f"Failed to generate template for {workflow_id}: {e}")
            raise

    def _prefill_template_values(self, template: Dict[str, Any], values: Dict[str, Any]) -> None:
        """Pre-fill template fields with extracted values"""
        for field in template.get("fields", []):
            field_id = field["field_id"]
            if field_id in values:
                field["default_value"] = values[field_id]
                logger.debug(f"Pre-filled {field_id} with value: {values[field_id]}")

    def _get_dependency_questions(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get dependency validation questions for workflow"""
        workflow_deps = self.dependencies_config.get(workflow_id, {})
        return workflow_deps.get("validation_questions", [])

    async def resolve_dependencies(self, workflow_id: str, dependency_responses: Dict[str, Any]) -> List[str]:
        """Resolve workflow dependencies based on user responses"""
        try:
            included_workflows = []
            workflow_deps = self.dependencies_config.get(workflow_id, {})
            
            # Process validation questions
            for question in workflow_deps.get("validation_questions", []):
                field = question["field"]
                response = dependency_responses.get(field, question.get("default", False))
                
                # Check conditions
                if question.get("if_false") and not response:
                    action = question["if_false"]
                    if action.startswith("include_"):
                        dep_workflow = action.replace("include_", "")
                        if dep_workflow not in included_workflows:
                            included_workflows.append(dep_workflow)
                
                elif question.get("if_true") and response:
                    action = question["if_true"]
                    if action.startswith("include_"):
                        dep_workflow = action.replace("include_", "")
                        if dep_workflow not in included_workflows:
                            included_workflows.append(dep_workflow)
            
            # Always include authentication
            if "authentication" not in included_workflows:
                included_workflows.insert(0, "authentication")
            
            logger.info(f"Resolved dependencies for {workflow_id}: {included_workflows}")
            return included_workflows
            
        except Exception as e:
            logger.error(f"Failed to resolve dependencies for {workflow_id}: {e}")
            return ["authentication"]  # Minimum dependency

    async def enhance_template(self, workflow_id: str, user_values: Dict[str, Any], dependency_responses: Dict[str, Any]) -> EnhancedWorkflow:
        """Enhance template with user values and resolved dependencies"""
        try:
            # Resolve dependencies
            included_workflows = await self.resolve_dependencies(workflow_id, dependency_responses)
            
            # Validate user values
            validation_result = self.registry.validate_template(workflow_id, user_values)
            if not validation_result["valid"]:
                raise ValueError(f"Invalid template values: {', '.join(validation_result['errors'])}")
            
            validated_values = validation_result["validated_values"]
            
            # Generate complete test steps
            complete_steps = await self._generate_complete_steps(workflow_id, included_workflows, validated_values)
            
            # Calculate total duration
            total_duration = self._calculate_total_duration(included_workflows)
            
            enhanced = EnhancedWorkflow(
                main_workflow=workflow_id,
                included_workflows=included_workflows,
                user_values=validated_values,
                resolved_dependencies=dependency_responses,
                complete_test_steps=complete_steps,
                estimated_total_duration=total_duration
            )
            
            logger.info(f"Enhanced workflow {workflow_id} with {len(included_workflows)} dependencies")
            return enhanced
            
        except Exception as e:
            logger.error(f"Failed to enhance template for {workflow_id}: {e}")
            raise

    async def _generate_complete_steps(self, main_workflow: str, included_workflows: List[str], user_values: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate complete test steps combining all workflows"""
        complete_steps = []
        step_counter = 1
        
        # Add steps for each included workflow
        for workflow_id in included_workflows + [main_workflow]:
            workflow_template = self.registry.get_template(workflow_id)
            if not workflow_template:
                continue
            
            # Get workflow steps
            workflow_steps = workflow_template.get("steps", [])
            
            for step in workflow_steps:
                enhanced_step = step.copy()
                enhanced_step["step_id"] = step_counter
                enhanced_step["workflow_source"] = workflow_id
                
                # Apply timeout configuration
                enhanced_step["timeout"] = self._get_step_timeout(step["action"])
                
                # Replace value placeholders with user values
                if step.get("value") and step["value"] in user_values:
                    enhanced_step["value"] = user_values[step["value"]]
                
                # Enhance selector with AI if needed
                if not step.get("selector") and step["action"] in ["click", "type"]:
                    enhanced_step["selector"] = await self._enhance_selector_with_ai(step, workflow_id)
                
                complete_steps.append(enhanced_step)
                step_counter += 1
        
        return complete_steps

    def _get_step_timeout(self, action: str) -> int:
        """Get appropriate timeout for step action"""
        timeout_config = TimeoutConfig.get_timeout_config()
        
        if action == "navigate":
            return timeout_config["navigation"]
        elif action in ["click", "type", "select"]:
            return timeout_config["action_timeout"]
        elif action == "wait":
            return timeout_config["element_wait"]
        else:
            return timeout_config["action_timeout"]

    async def _enhance_selector_with_ai(self, step: Dict[str, Any], workflow_id: str) -> str:
        """Use AI to enhance selector for better element detection"""
        system_prompt = """Generate CSS selector for Cisco Catalyst Centre UI element.

Focus on:
- Robust selectors that work across different versions
- Multiple fallback options
- Cisco-specific UI patterns

Output only the CSS selector string."""

        user_prompt = f"""
Step: {step['description']}
Action: {step['action']}
Workflow: {workflow_id}

Generate primary CSS selector for this element.
"""
        
        try:
            response = await self.azure_client.call_agent(
                agent_name="SelectorEnhancement",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="text",
                temperature=0.1
            )
            
            if response.success and response.content:
                return response.content.strip()
                
        except Exception as e:
            logger.error(f"Failed to enhance selector: {e}")
        
        # Fallback selector
        return "button, a, input"

    def _calculate_total_duration(self, workflows: List[str]) -> int:
        """Calculate total estimated duration for all workflows"""
        total = 0
        for workflow_id in workflows:
            template = self.registry.get_template(workflow_id)
            if template:
                total += template.get("estimated_duration", 300)
        return total

    def list_available_workflows(self) -> List[Dict[str, Any]]:
        """List all available workflows"""
        return self.registry.list_workflows()

    def search_workflows(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search workflows by query"""
        return self.registry.search_workflows(query, category)

    def refresh_workflows(self) -> None:
        """Refresh workflow definitions from TDD files"""
        self.registry.refresh_workflows()
