# src/workflow_definitions/workflow_registry.py
"""
Workflow Registry - Central management of all workflow definitions
Handles loading, caching, and retrieval of workflow templates
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import asdict
from .tdd_parser import TDDParser, WorkflowDefinition

logger = logging.getLogger(__name__)

class WorkflowRegistry:
    """
    Central registry for all workflow definitions
    Manages loading from TDD files and template generation
    """
    
    def __init__(self, tdd_directory: Path, templates_directory: Path):
        self.tdd_directory = tdd_directory
        self.templates_directory = templates_directory
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.parser = TDDParser()
        
        # Create directories if they don't exist
        self.templates_directory.mkdir(parents=True, exist_ok=True)
        
        # Load existing workflows
        self.load_workflows()

    def load_workflows(self) -> None:
        """Load all workflows from TDD files and existing templates"""
        logger.info("Loading workflows from TDD files...")
        
        # First load any existing manual templates
        self._load_manual_templates()
        
        # Parse TDD files
        self.workflows = self.parser.parse_all_tdd_files(self.tdd_directory)
        
        # Generate and save templates (but don't overwrite manual ones)
        for workflow_id, workflow in self.workflows.items():
            # Only generate template if it doesn't already exist
            if workflow_id not in self.templates:
                template = self.parser.generate_template_json(workflow)
                self.templates[workflow_id] = template
                
                # Save template to file
                template_file = self.templates_directory / f"{workflow_id}.json"
                template_file.write_text(json.dumps(template, indent=2))
            else:
                logger.info(f"Manual template exists for {workflow_id}, skipping auto-generation")
            
        logger.info(f"Loaded {len(self.workflows)} workflows")

    def _load_manual_templates(self) -> None:
        """Load manually created template files"""
        for template_file in self.templates_directory.glob("*.json"):
            if template_file.stem not in self.templates:
                try:
                    # Skip empty files
                    if template_file.stat().st_size == 0:
                        logger.warning(f"Skipping empty template file: {template_file}")
                        continue
                        
                    template_data = json.loads(template_file.read_text())
                    self.templates[template_file.stem] = template_data
                    logger.info(f"Loaded manual template: {template_file.stem}")
                except Exception as e:
                    logger.error(f"Failed to load template {template_file}: {e}")

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition by ID"""
        return self.workflows.get(workflow_id)

    def get_template(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow template by ID"""
        return self.templates.get(workflow_id)

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all available workflows"""
        return [
            {
                "workflow_id": workflow_id,
                "workflow_name": template.get("workflow_name", workflow_id),
                "description": template.get("description", ""),
                "category": template.get("category", "general"),
                "estimated_duration": template.get("estimated_duration", 300)
            }
            for workflow_id, template in self.templates.items()
        ]

    def search_workflows(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search workflows by query and optional category"""
        query_lower = query.lower()
        results = []
        
        for workflow_id, template in self.templates.items():
            # Skip if category filter doesn't match
            if category and template.get("category") != category:
                continue
            
            # Search in various fields
            searchable_text = " ".join([
                workflow_id,
                template.get("workflow_name", ""),
                template.get("description", ""),
                template.get("category", "")
            ]).lower()
            
            if query_lower in searchable_text:
                results.append({
                    "workflow_id": workflow_id,
                    "workflow_name": template.get("workflow_name", workflow_id),
                    "description": template.get("description", ""),
                    "category": template.get("category", "general"),
                    "relevance_score": self._calculate_relevance(query_lower, searchable_text)
                })
        
        # Sort by relevance score
        return sorted(results, key=lambda x: x["relevance_score"], reverse=True)

    def _calculate_relevance(self, query: str, text: str) -> float:
        """Calculate relevance score for search results"""
        if query == text:
            return 1.0
        
        # Count exact matches
        exact_matches = text.count(query)
        
        # Count word matches
        query_words = query.split()
        text_words = text.split()
        word_matches = sum(1 for word in query_words if word in text_words)
        
        # Calculate score
        score = (exact_matches * 0.5 + word_matches * 0.3) / max(len(query_words), 1)
        return min(score, 1.0)

    def get_workflow_dependencies(self, workflow_id: str) -> List[str]:
        """Get dependencies for a specific workflow"""
        template = self.get_template(workflow_id)
        return template.get("dependencies", []) if template else []

    def get_categories(self) -> List[str]:
        """Get all available workflow categories"""
        categories = set()
        for template in self.templates.values():
            categories.add(template.get("category", "general"))
        return sorted(list(categories))

    def validate_template(self, workflow_id: str, user_values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user-provided values against template"""
        template = self.get_template(workflow_id)
        if not template:
            return {"valid": False, "errors": [f"Workflow {workflow_id} not found"]}
        
        errors = []
        validated_values = {}
        
        # Validate each field
        for field in template.get("fields", []):
            field_id = field["field_id"]
            field_label = field["label"]
            field_type = field["type"]
            required = field.get("required", False)
            validation = field.get("validation", {})
            
            value = user_values.get(field_id)
            
            # Check required fields
            if required and (value is None or value == ""):
                errors.append(f"{field_label} is required")
                continue
            
            # Skip validation if field is not provided and not required
            if value is None:
                continue
            
            # Type-specific validation
            if field_type == "number":
                try:
                    numeric_value = float(value)
                    if "min" in validation and numeric_value < validation["min"]:
                        errors.append(f"{field_label} must be at least {validation['min']}")
                    if "max" in validation and numeric_value > validation["max"]:
                        errors.append(f"{field_label} must be at most {validation['max']}")
                    validated_values[field_id] = numeric_value
                except ValueError:
                    errors.append(f"{field_label} must be a valid number")
            
            elif field_type == "text":
                if "min_length" in validation and len(str(value)) < validation["min_length"]:
                    errors.append(f"{field_label} must be at least {validation['min_length']} characters")
                if "max_length" in validation and len(str(value)) > validation["max_length"]:
                    errors.append(f"{field_label} must be at most {validation['max_length']} characters")
                if "pattern" in validation:
                    import re
                    if not re.match(validation["pattern"], str(value)):
                        errors.append(f"{field_label} format is invalid")
                validated_values[field_id] = str(value)
            
            elif field_type == "boolean":
                if isinstance(value, bool):
                    validated_values[field_id] = value
                elif str(value).lower() in ["true", "false"]:
                    validated_values[field_id] = str(value).lower() == "true"
                else:
                    errors.append(f"{field_label} must be true or false")
            
            elif field_type == "dropdown":
                options = field.get("options", [])
                if options and value not in options:
                    errors.append(f"{field_label} must be one of: {', '.join(options)}")
                validated_values[field_id] = value
            
            else:
                validated_values[field_id] = value
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "validated_values": validated_values
        }

    def refresh_workflows(self) -> None:
        """Refresh workflows by re-parsing TDD files"""
        logger.info("Refreshing workflow definitions...")
        self.workflows.clear()
        self.templates.clear()
        self.load_workflows()

    def add_custom_template(self, workflow_id: str, template: Dict[str, Any]) -> bool:
        """Add a custom workflow template"""
        try:
            # Validate template structure
            required_fields = ["workflow_id", "workflow_name", "fields"]
            for field in required_fields:
                if field not in template:
                    logger.error(f"Custom template missing required field: {field}")
                    return False
            
            # Save template
            self.templates[workflow_id] = template
            template_file = self.templates_directory / f"{workflow_id}.json"
            template_file.write_text(json.dumps(template, indent=2))
            
            logger.info(f"Added custom template: {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add custom template {workflow_id}: {e}")
            return False

    def remove_template(self, workflow_id: str) -> bool:
        """Remove a workflow template"""
        try:
            if workflow_id in self.templates:
                del self.templates[workflow_id]
            
            if workflow_id in self.workflows:
                del self.workflows[workflow_id]
            
            # Remove template file
            template_file = self.templates_directory / f"{workflow_id}.json"
            if template_file.exists():
                template_file.unlink()
            
            logger.info(f"Removed template: {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove template {workflow_id}: {e}")
            return False

    def export_templates(self, export_path: Path) -> bool:
        """Export all templates to a directory"""
        try:
            export_path.mkdir(parents=True, exist_ok=True)
            
            for workflow_id, template in self.templates.items():
                export_file = export_path / f"{workflow_id}.json"
                export_file.write_text(json.dumps(template, indent=2))
            
            logger.info(f"Exported {len(self.templates)} templates to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export templates: {e}")
            return False

    def import_templates(self, import_path: Path) -> int:
        """Import templates from a directory"""
        imported_count = 0
        
        if not import_path.exists():
            logger.error(f"Import path does not exist: {import_path}")
            return 0
        
        for template_file in import_path.glob("*.json"):
            try:
                template_data = json.loads(template_file.read_text())
                workflow_id = template_file.stem
                
                if self.add_custom_template(workflow_id, template_data):
                    imported_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to import template {template_file}: {e}")
        
        logger.info(f"Imported {imported_count} templates from {import_path}")
        return imported_count
