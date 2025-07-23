"""
Main FastAPI backend application with proper Azure OpenAI integration
"""
import os
import uuid
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Import our core modules
from src.core.azure_client import AzureOpenAIClient
from src.core.config import setup_logging
from src.agents.nl_processor_simple import NLProcessor
from src.agents.test_strategy_agent_simple import TestStrategyAgent
from src.agents.test_generation_agent_simple import TestGenerationAgent
from src.agents.element_detection_agent_simple import ElementDetectionAgent
from src.automation.test_executor import TestExecutor
from src.infrastructure.report_generator_simple import ReportGenerator

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup logging
setup_logging(level="INFO", output_dir="logs")

import logging
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Test Automation Platform", version="1.0.0")

logger.info("AI E2E Testing Agent Web Interface started")

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates for frontend
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(os.path.dirname(current_dir), "frontend", "static")
template_dir = os.path.join(os.path.dirname(current_dir), "frontend")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=template_dir)

# Initialize Azure OpenAI client and orchestrator globally
azure_client = None
test_executor = None
orchestrator = None

# Singleton agents to prevent duplicate calls
nl_processor = None
strategy_agent = None
element_agent = None
test_gen_agent = None
report_generator = None

# Browser configuration for headed mode
browser_config = {
    "headless": False,  # Always run in headed mode
    "browser_type": "chromium",
    "slow_mo": 1000,  # Slow motion for debugging
    "timeout": 60000,
    "viewport": {"width": 1920, "height": 1080},
    "device_scale_factor": 1,
    "args": ["--start-maximized"]
}

def initialize_services():
    """Initialize Azure OpenAI client, test executor, and orchestrator"""
    global azure_client, test_executor, orchestrator, nl_processor, strategy_agent, element_agent, test_gen_agent, report_generator
    try:
        from pathlib import Path
        from src.core.orchestrator import TestOrchestrator
        from src.agents.nl_processor_simple import NLProcessor
        from src.agents.test_strategy_agent_simple import TestStrategyAgent
        from src.agents.element_detection_agent_simple import ElementDetectionAgent
        from src.agents.test_generation_agent_simple import TestGenerationAgent
        from src.infrastructure.report_generator_simple import ReportGenerator
        
        config_path = Path(__file__).parent / "src"
        
        azure_client = AzureOpenAIClient()
        test_executor = TestExecutor(browser_config, azure_client)
        
        # Initialize singleton agents to prevent duplicate calls
        nl_processor = NLProcessor(azure_client)
        strategy_agent = TestStrategyAgent(azure_client)
        element_agent = ElementDetectionAgent(azure_client)
        test_gen_agent = TestGenerationAgent(azure_client)
        report_generator = ReportGenerator(azure_client)
        
        # Initialize orchestrator with shared agents
        orchestrator = TestOrchestrator(azure_client, config_path, nl_processor)
        
        print("✅ Azure OpenAI client initialized successfully")
        print("✅ Test executor initialized with headed browser mode")
        print("✅ Workflow orchestrator initialized")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        raise Exception(f"Service initialization failed: {e}")

# Initialize services on startup
services_available = initialize_services()

# Request/Response models
class TestRequest(BaseModel):
    instructions: str
    url: str
    username: Optional[str] = None
    password: Optional[str] = None

class TestControl(BaseModel):
    action: str  # 'pause', 'resume', 'stop'

class TestStatus(BaseModel):
    execution_id: str
    status: str
    current_step: Optional[str] = None
    progress: int = 0
    results: Optional[Dict] = None

# Execution tracking
executions: Dict[str, Dict] = {}
websocket_connections: List[WebSocket] = []

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                # Remove disconnected clients
                self.disconnect(connection)

manager = WebSocketManager()

# API Routes

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/favicon.ico")
async def favicon():
    """Return empty favicon to avoid 404 errors"""
    return {"status": "no favicon"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "azure_client_available": services_available,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/test/start")
async def start_test(request: TestRequest):
    """Start a new test execution"""
    execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Initialize execution tracking
    executions[execution_id] = {
        "id": execution_id,
        "status": "running",
        "request": request.model_dump(),
        "current_step": "Initializing",
        "progress": 0,
        "start_time": datetime.now().isoformat(),
        "steps": [],
        "results": None,
        "paused": False
    }
    
    # Start the test execution in background
    asyncio.create_task(execute_test(execution_id, request))
    
    return {"execution_id": execution_id, "status": "started"}

@app.post("/api/test/{execution_id}/control")
async def control_test(execution_id: str, control: TestControl):
    """Control test execution (pause/resume/stop)"""
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    execution = executions[execution_id]
    
    if control.action == "pause":
        execution["paused"] = True
        execution["status"] = "paused"
        await manager.broadcast({
            "type": "status_update",
            "execution_id": execution_id,
            "status": "paused"
        })
    elif control.action == "resume":
        execution["paused"] = False
        execution["status"] = "running"
        await manager.broadcast({
            "type": "status_update",
            "execution_id": execution_id,
            "status": "running"
        })
    elif control.action == "stop":
        execution["status"] = "stopped"
        await manager.broadcast({
            "type": "status_update",
            "execution_id": execution_id,
            "status": "stopped"
        })
    
    return {"status": execution["status"]}

@app.get("/api/test/{execution_id}/status")
async def get_test_status(execution_id: str):
    """Get current test execution status"""
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    execution = executions[execution_id]
    return TestStatus(
        execution_id=execution_id,
        status=execution["status"],
        current_step=execution["current_step"],
        progress=execution["progress"],
        results=execution.get("results")
    )

@app.get("/api/test/list")
async def list_executions():
    """List all test executions"""
    return {"executions": list(executions.values())}

@app.post("/api/browser/session/end")
async def end_browser_session():
    """End the current browser session"""
    if services_available and test_executor:
        await test_executor.end_browser_session()
        return {"status": "Browser session ended successfully"}
    return {"status": "Test executor not available"}

@app.get("/api/browser/session/status")
async def get_browser_session_status():
    """Get the current browser session status"""
    if services_available and test_executor:
        return {
            "session_active": test_executor._session_active,
            "browser_available": test_executor.browser_pool.browser is not None
        }
    return {"session_active": False, "browser_available": False}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for keepalive
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Core test execution logic
async def execute_test(execution_id: str, request: TestRequest):
    """Execute the test with proper Azure client integration"""
    execution = executions[execution_id]
    
    try:
        # Step 1: Natural Language Processing
        await update_execution(execution_id, "Processing natural language instructions", 10)
        
        if not services_available or not azure_client:
            raise Exception("Azure services not available - cannot process instructions")
            
        # Use singleton nl_processor
        processed_instructions = await asyncio.to_thread(
            nl_processor.process_instructions, 
            request.instructions, 
            request.url
        )
        
        # Wait if paused
        await check_pause(execution_id)
        
        # Step 2: Test Strategy Generation
        await update_execution(execution_id, "Generating test strategy", 25)
        
        if services_available and azure_client:
            test_strategy = await asyncio.to_thread(
                strategy_agent.generate_strategy,
                processed_instructions,
                request.url
            )
        else:
            await asyncio.sleep(1.5)
            test_strategy = {
                "approach": "Page Object Model",
                "test_cases": [
                    {"name": "Login Test", "priority": "high"},
                    {"name": "Navigation Test", "priority": "medium"}
                ],
                "execution_order": ["setup", "login", "navigation", "cleanup"]
            }
        
        await check_pause(execution_id)
        
        # Step 3: Element Detection
        await update_execution(execution_id, "Detecting page elements", 40)
        
        if services_available and azure_client:
            detected_elements = await asyncio.to_thread(
                element_agent.detect_elements,
                request.url,
                processed_instructions.get("target_elements", [])
            )
        else:
            await asyncio.sleep(2)
            detected_elements = {
                "login_form": {"selector": "#loginForm", "type": "form"},
                "username_field": {"selector": "#username", "type": "input"},
                "password_field": {"selector": "#password", "type": "input"},
                "submit_button": {"selector": "#loginBtn", "type": "button"}
            }
        
        await check_pause(execution_id)
        
        # Step 4: Test Code Generation
        await update_execution(execution_id, "Generating test code", 60)
        
        if services_available and azure_client:
            # Pass user credentials to test generation
            generated_tests = await asyncio.to_thread(
                test_gen_agent.generate_test_code,
                test_strategy,
                detected_elements,
                request.url,
                {
                    "username": request.username or "testuser",
                    "password": request.password or "testpassword"
                }
            )
        else:
            await asyncio.sleep(2.5)
            generated_tests = {
                "test_file": "test_login.py",
                "test_code": """
def test_user_login():
    driver.get('""" + request.url + """')
    driver.find_element(By.ID, 'username').send_keys('""" + (request.username or 'testuser') + """')
    driver.find_element(By.ID, 'password').send_keys('password')
    driver.find_element(By.ID, 'loginBtn').click()
    assert 'dashboard' in driver.current_url
                """,
                "dependencies": ["selenium", "pytest"]
            }
        
        await check_pause(execution_id)
        
        # Step 5: Test Execution
        await update_execution(execution_id, "Executing tests", 80)
        
        # Initialize default test results
        test_results = {
            "total_tests": 1,
            "passed": 1,
            "failed": 0,
            "execution_time": "3.2s",
            "details": [
                {
                    "test_name": "test_user_login",
                    "status": "passed",
                    "duration": "3.2s",
                    "screenshot": "login_test_screenshot.png"
                }
            ]
        }
        
        if services_available and azure_client and test_executor:
            # Execute the actual test with headed browser
            try:
                test_results = await test_executor.execute_test_script(
                    test_script=generated_tests,
                    application_url=request.url,
                    user_credentials={
                        "username": request.username,
                        "password": request.password
                    } if request.username and request.password else None
                )
                logger.info(f"Real test execution completed for {execution_id}")
            except Exception as e:
                logger.error(f"Test execution failed: {e}")
                test_results = {
                    "total_tests": 1,
                    "passed": 0,
                    "failed": 1,
                    "execution_time": "3.2s",
                    "error": str(e),
                    "details": [
                        {
                            "test_name": "test_user_login",
                            "status": "failed",
                            "duration": "3.2s",
                            "error_message": str(e)
                        }
                    ]
                }
        else:
            logger.warning(f"Services not fully available - using mock test results for {execution_id}")
        
        await check_pause(execution_id)
        
        # Step 6: Report Generation
        await update_execution(execution_id, "Generating report", 95)
        
        if services_available and azure_client:
            final_report = await asyncio.to_thread(
                report_generator.generate_report,
                test_results,
                execution_id
            )
        else:
            await asyncio.sleep(1)
            final_report = {
                "execution_id": execution_id,
                "summary": "Test execution completed successfully",
                "total_tests": 1,
                "passed": 1,
                "failed": 0,
                "coverage": "85%",
                "recommendations": [
                    "Consider adding more edge case tests",
                    "Implement data-driven testing for multiple user scenarios"
                ]
            }
        
        # Final completion
        execution["status"] = "completed"
        execution["current_step"] = "Completed"
        execution["progress"] = 100
        execution["results"] = final_report
        execution["end_time"] = datetime.now().isoformat()
        
        await manager.broadcast({
            "type": "execution_complete",
            "execution_id": execution_id,
            "results": final_report
        })
        
    except Exception as e:
        execution["status"] = "failed"
        execution["error"] = str(e)
        execution["end_time"] = datetime.now().isoformat()
        
        await manager.broadcast({
            "type": "execution_failed",
            "execution_id": execution_id,
            "error": str(e)
        })

async def update_execution(execution_id: str, step: str, progress: int):
    """Update execution status and broadcast to clients"""
    execution = executions[execution_id]
    execution["current_step"] = step
    execution["progress"] = progress
    execution["steps"].append({
        "step": step,
        "timestamp": datetime.now().isoformat(),
        "progress": progress
    })
    
    await manager.broadcast({
        "type": "progress_update",
        "execution_id": execution_id,
        "step": step,
        "progress": progress
    })

async def check_pause(execution_id: str):
    """Check if execution is paused and wait if needed"""
    execution = executions[execution_id]
    while execution.get("paused", False) and execution["status"] != "stopped":
        await asyncio.sleep(0.5)
    
    if execution["status"] == "stopped":
        raise Exception("Execution was stopped by user")

# ============================================================================
# WORKFLOW INTELLIGENCE ENDPOINTS
# ============================================================================

class WorkflowDetectionRequest(BaseModel):
    user_request: str
    context: Optional[Dict[str, Any]] = {}

class WorkflowTemplateRequest(BaseModel):
    template_id: str
    field_values: Dict[str, Any]
    execution_options: Optional[Dict[str, Any]] = {}

@app.post("/api/detect-workflow")
async def detect_workflow(request: WorkflowDetectionRequest):
    """Detect if user request is a workflow and return template if found"""
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Workflow orchestrator not available")
        
        result = await orchestrator.process_user_request(
            user_input=request.user_request,
            context=request.context
        )
        
        return result
    except Exception as e:
        logger.error(f"Error detecting workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/submit-workflow")
async def submit_workflow(request: WorkflowTemplateRequest):
    """Submit a completed workflow template for execution"""
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Workflow orchestrator not available")
        
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        result = await orchestrator.process_template_submission(
            execution_id=execution_id,
            workflow_id=request.template_id,
            user_values=request.field_values,
            dependency_responses=request.execution_options.get("dependency_responses", {})
        )
        
        return result
    except Exception as e:
        logger.error(f"Error submitting workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflow-templates")
async def list_workflow_templates():
    """Get list of available workflow templates"""
    try:
        if not orchestrator or not orchestrator.workflow_agent:
            raise HTTPException(status_code=503, detail="Workflow system not available")
        
        templates = orchestrator.workflow_agent.registry.list_workflows()
        return {"templates": templates}
    except Exception as e:
        logger.error(f"Error listing workflow templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflow-template/{template_id}")
async def get_workflow_template(template_id: str):
    """Get a specific workflow template by ID"""
    try:
        if not orchestrator or not orchestrator.workflow_agent:
            logger.error("Workflow system not available")
            raise HTTPException(status_code=503, detail="Workflow system not available")
        
        logger.info(f"Retrieving workflow template: {template_id}")
        template = orchestrator.workflow_agent.registry.get_workflow(template_id)
        
        if not template:
            logger.error(f"Template {template_id} not found")
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        logger.info(f"Successfully retrieved template: {template_id}")
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
