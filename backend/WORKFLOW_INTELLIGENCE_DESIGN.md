# Workflow Intelligence Agent - Design Document

## 📋 Overview

This design introduces a **WorkflowIntelligenceAgent** that enhances the existing E2E testing system by recognizing complex Cisco Catalyst Centre workflows and expanding simple user instructions into complete multi-step test procedures with customizable templates.

## 🎯 Requirements Summary

- **5 MVP Workflows** for Cisco Catalyst Centre
- **Two-step process**: Detect workflow → Show template for user customization
- **Form-like templates** with field types and validation
- **Dependency handling**: Auto-include prerequisite workflows based on user confirmation
- **Dual detection**: Both keyword-based and intent-based workflow recognition
- **TDD file parsing**: Auto-generate workflow templates from existing .TDD files
- **Enhanced timeouts**: 300s for page loads, 180s for individual actions
- **Template enhancement**: Add dependent workflows and replace user-provided values

## 🏗️ Architecture Overview

```
User Input: "create fabric on catalyst.cisco.com"
         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                         │
│  ┌─────────────────┐    ┌────────────────────────────────────┐ │
│  │   NLProcessor   │    │   WorkflowIntelligenceAgent       │ │
│  │   (Enhanced)    │ ←→ │   - Workflow Detection             │ │
│  │                 │    │   - Template Generation           │ │
│  │                 │    │   - Dependency Resolution         │ │
│  └─────────────────┘    └────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         ↓
Template Response to User
         ↓
User Modifies & Resubmits
         ↓
┌─────────────────────────────────────────────────────────────────┐
│              Enhanced Test Generation Pipeline                  │
│  ┌─────────────────┐ → ┌─────────────────┐ → ┌──────────────┐ │
│  │ TestStrategy    │   │ ElementDetection│   │ TestGeneration│ │
│  │ (with timeouts) │   │     Agent       │   │   (enhanced) │ │
│  └─────────────────┘   └─────────────────┘   └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🧩 Component Design

### 1. WorkflowIntelligenceAgent

**Location**: `src/agents/workflow_intelligence_agent.py`

**Responsibilities**:
- Detect workflow types from user input
- Load workflow definitions from TDD files
- Generate customizable templates
- Resolve workflow dependencies
- Enhance templates with user values and dependencies

**Key Methods**:
```python
class WorkflowIntelligenceAgent:
    async def detect_workflow(self, user_input: str) -> WorkflowDetectionResult
    async def generate_template(self, workflow_type: str) -> WorkflowTemplate
    async def resolve_dependencies(self, workflow_type: str) -> List[str]
    async def enhance_template(self, template: dict, user_values: dict) -> EnhancedWorkflow
```

### 2. Workflow Definition System

**Location**: `src/workflow_definitions/`

**Structure**:
```
src/workflow_definitions/
├── tdd_parser.py          # Parse .TDD files into workflow configs
├── workflow_registry.py   # Central registry of all workflows
├── templates/
│   ├── create_fabric.json
│   ├── create_device_group.json
│   ├── network_hierarchy.json
│   ├── device_provisioning.json
│   └── configure_vlan.json
└── dependencies/
    └── workflow_dependencies.json
```

### 3. Enhanced NLProcessor

**Modifications**: Add workflow detection capabilities while maintaining existing functionality

**New Output Format**:
```python
{
    "intent_type": "workflow",  # New type
    "workflow_type": "create_fabric",
    "target_application": "Cisco Catalyst Centre",
    "detected_values": {
        "url": "https://catalyst.cisco.com",
        "fabric_name": "Production-Fabric"
    },
    "requires_template": True,
    # ... existing fields
}
```

### 4. Orchestration Layer

**Location**: `backend/app.py` (enhanced)

**Responsibilities**:
- Route between NLProcessor and WorkflowIntelligenceAgent
- Handle template generation and user interaction
- Coordinate enhanced test generation

## 📋 Workflow Template Structure

### Template Format (Form-like with Validation)

```json
{
    "workflow_id": "create_fabric",
    "workflow_name": "Create Network Fabric",
    "description": "Creates a new network fabric in Cisco Catalyst Centre",
    "dependencies": ["network_hierarchy"],
    "fields": [
        {
            "field_id": "fabric_name",
            "label": "Fabric Name",
            "type": "text",
            "required": true,
            "default_value": "Test-Fabric-001",
            "validation": {
                "min_length": 3,
                "max_length": 64,
                "pattern": "^[a-zA-Z0-9_-]+$"
            },
            "description": "Unique name for the fabric"
        },
        {
            "field_id": "bgp_asn",
            "label": "BGP ASN",
            "type": "number",
            "required": true,
            "default_value": "65001",
            "validation": {
                "min": 1,
                "max": 65535
            },
            "description": "BGP Autonomous System Number"
        },
        {
            "field_id": "site_hierarchy",
            "label": "Site Hierarchy",
            "type": "dropdown",
            "required": true,
            "default_value": "Global/USA/Campus1",
            "options": [
                "Global/USA/Campus1",
                "Global/USA/Campus2",
                "Global/Europe/London"
            ],
            "description": "Network site hierarchy location"
        },
        {
            "field_id": "enable_l3_handoff",
            "label": "Enable L3 Handoff",
            "type": "boolean",
            "required": false,
            "default_value": true,
            "description": "Enable Layer 3 handoff configuration"
        }
    ],
    "global_fields": [
        {
            "field_id": "target_url",
            "label": "Target URL",
            "type": "url",
            "required": true,
            "value": "https://catalyst.cisco.com"
        },
        {
            "field_id": "username",
            "label": "Username",
            "type": "text",
            "required": true,
            "default_value": "admin"
        },
        {
            "field_id": "password",
            "label": "Password",
            "type": "password",
            "required": true,
            "default_value": "admin123"
        }
    ]
}
```

### Dependency Resolution

**File**: `src/workflow_definitions/dependencies/workflow_dependencies.json`

```json
{
    "create_fabric": {
        "prerequisites": ["network_hierarchy"],
        "optional_dependencies": [],
        "validation_questions": [
            {
                "question": "Does the network hierarchy already exist in the system?",
                "field": "hierarchy_exists",
                "type": "boolean",
                "default": false,
                "if_false": "include_network_hierarchy"
            }
        ]
    },
    "create_device_group": {
        "prerequisites": ["network_hierarchy", "create_fabric"],
        "validation_questions": [
            {
                "question": "Is the target fabric already created?",
                "field": "fabric_exists", 
                "type": "boolean",
                "default": false,
                "if_false": "include_create_fabric"
            }
        ]
    }
}
```

## 🔄 User Experience Flow

### Step 1: Initial Input Processing
```
User: "create fabric on https://catalyst.cisco.com with name Production-Fabric"
         ↓
NLProcessor: Detects workflow intent
         ↓
WorkflowIntelligenceAgent: Identifies "create_fabric" workflow
         ↓
System: Generates template with detected values pre-filled
```

### Step 2: Template Presentation
```json
{
    "status": "template_required",
    "workflow_type": "create_fabric",
    "message": "I've detected a fabric creation workflow. Please review and customize the template:",
    "template": {
        // ... full template structure with pre-filled values
    },
    "dependency_questions": [
        {
            "question": "Does the network hierarchy already exist in the system?",
            "field": "hierarchy_exists",
            "type": "boolean",
            "default": false
        }
    ]
}
```

### Step 3: User Customization & Resubmission
```json
{
    "workflow_type": "create_fabric",
    "user_responses": {
        "fabric_name": "Production-Fabric-Modified",
        "bgp_asn": "65100",
        "hierarchy_exists": false,
        "target_url": "https://catalyst.cisco.com",
        "username": "testuser",
        "password": "testpass123"
    }
}
```

### Step 4: Enhanced Workflow Generation
```
WorkflowIntelligenceAgent: 
- Adds network_hierarchy workflow (since hierarchy_exists = false)
- Replaces all template values with user inputs
- Generates complete multi-workflow test sequence
         ↓
Enhanced Test Generation: Creates comprehensive test with proper timeouts
```

## ⚙️ Timeout Configuration

### Global Timeout Settings
```python
WORKFLOW_TIMEOUTS = {
    "page_load": 300000,      # 300s for page loads and dashboards
    "action_timeout": 180000, # 180s for individual actions
    "element_wait": 180000,   # 180s for element visibility
    "navigation": 300000,     # 300s for navigation between pages
    "form_submission": 180000 # 180s for form submissions
}
```

### Implementation in Test Steps
```python
{
    "step_id": 1,
    "action": "navigate",
    "timeout": 300000,  # Page load timeout
    "wait_condition": "networkidle"
},
{
    "step_id": 2,
    "action": "click",
    "timeout": 180000,  # Action timeout
    "wait_condition": "visible"
}
```

## 🔧 Integration Points

### 1. Enhanced NLProcessor Integration
- **Backward Compatibility**: Existing simple instructions continue to work
- **Workflow Detection**: New logic to identify workflow patterns
- **Response Enhancement**: Extended output format for workflow instructions

### 2. Existing Agent Pipeline
- **TestStrategyAgent**: Enhanced to handle multi-workflow sequences
- **ElementDetectionAgent**: Works with extended workflow-based test steps
- **TestGenerationAgent**: Enhanced timeout configuration and multi-workflow support

### 3. API Endpoints Enhancement
```python
# New endpoint for template generation
@app.post("/api/generate-template")
async def generate_workflow_template(request: WorkflowTemplateRequest)

# Enhanced existing endpoint
@app.post("/api/generate-test")  # Now handles both simple and workflow instructions
```

## 📁 File Structure

```
backend/
├── src/
│   ├── agents/
│   │   ├── workflow_intelligence_agent.py     # New
│   │   ├── nl_processor.py                    # Enhanced
│   │   └── ...existing agents...
│   ├── workflow_definitions/
│   │   ├── __init__.py
│   │   ├── tdd_parser.py                      # New
│   │   ├── workflow_registry.py               # New
│   │   ├── templates/                         # New
│   │   │   ├── create_fabric.json
│   │   │   ├── create_device_group.json
│   │   │   ├── network_hierarchy.json
│   │   │   ├── device_provisioning.json
│   │   │   └── configure_vlan.json
│   │   └── dependencies/                      # New
│   │       └── workflow_dependencies.json
│   ├── models/
│   │   ├── workflow_models.py                 # New
│   │   └── ...existing models...
│   └── core/
│       ├── orchestrator.py                    # New
│       └── ...existing core...
├── tdd_files/                                 # New - Your .TDD files
│   ├── create_fabric.tdd
│   ├── create_device_group.tdd
│   └── ...
└── ...existing structure...
```

## 🚀 Implementation Plan

### Phase 1: Foundation
1. Create workflow definition structure
2. Implement TDD file parser
3. Build workflow registry system
4. Create basic template generation

### Phase 2: Core Intelligence
1. Implement WorkflowIntelligenceAgent
2. Enhance NLProcessor with workflow detection
3. Build dependency resolution system
4. Create orchestration layer

### Phase 3: Integration
1. Enhance existing agents for multi-workflow support
2. Update timeout configurations globally
3. Modify API endpoints for template handling
4. Integrate with existing test generation pipeline

### Phase 4: User Experience
1. Update frontend for template display and editing
2. Implement form validation
3. Add dependency question handling
4. Test complete workflow end-to-end

## 🧪 Testing Strategy

### Unit Tests
- WorkflowIntelligenceAgent methods
- TDD parser functionality
- Template generation logic
- Dependency resolution

### Integration Tests
- NLProcessor + WorkflowIntelligenceAgent coordination
- Multi-workflow test generation
- Timeout configuration effectiveness
- Template customization flow

### End-to-End Tests
- Complete workflow: detection → template → customization → test generation
- All 5 MVP workflows with dependencies
- Backward compatibility with existing simple instructions

## 🔒 Backward Compatibility

- **Existing Instructions**: Continue to work unchanged
- **Simple Tests**: Still processed by original NLProcessor logic
- **API Compatibility**: Existing endpoints maintain same behavior
- **Agent Pipeline**: Enhanced but maintains original functionality

## 📊 Success Metrics

- **Workflow Detection Accuracy**: >95% for defined workflow patterns
- **Template Generation Speed**: <2 seconds per template
- **Test Execution Reliability**: >90% success rate with enhanced timeouts
- **User Experience**: Complete workflow from detection to test in <30 seconds

---

**Next Steps**: Upon approval of this design, implement Phase 1 components and provide .TDD file examples for parser development.
