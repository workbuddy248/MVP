#!/usr/bin/env python3
"""
Web Frontend for AI Eclass TestGenerationRequest(BaseModel):
    instructions: str
    cluster_ip: Optional[str] = None
    base_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    headless: bool = False  # Default to visible browser

class TestExecutionRequest(BaseModel):
    instructions: str
    cluster_ip: Optional[str] = None
    base_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    headless: bool = False  # Default to visible browsert
FastAPI-based web interface for test execution and monitoring
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.ai_controller import AIController
from src.core.config import load_config, setup_logging
from src.models.test_models import TestExecutionResult

# Initialize FastAPI app
app = FastAPI(
    title="AI E2E Testing Agent",
    description="Transform natural language commands into automated Playwright tests",
    version="1.0.0"
)

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global state for execution management
active_executions: Dict[str, Dict[str, Any]] = {}
execution_websockets: Dict[str, List[WebSocket]] = {}

# Pydantic models for API
class TestRequest(BaseModel):
    instructions: str
    cluster_ip: Optional[str] = None
    base_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    headless: bool = True

class TestExecutionRequest(BaseModel):
    instructions: str
    cluster_ip: Optional[str] = None
    base_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    headless: bool = True

class ExecutionControl(BaseModel):
    execution_id: str
    action: str  # 'pause', 'resume', 'stop'

class ExecutionStatus(BaseModel):
    execution_id: str
    status: str
    progress: int
    current_step: str
    start_time: str
    results: Optional[Dict[str, Any]] = None

# Setup logging
logger = logging.getLogger(__name__)

# Load configuration on startup
config = None

@app.on_event("startup")
async def startup_event():
    global config
    try:
        # Map user's environment variables to expected ones
        if "AZURE_ENDPOINT" in os.environ and "AZURE_OPENAI_CLIENT_SECRET" in os.environ:
            os.environ["AZURE_OPENAI_ENDPOINT"] = os.environ["AZURE_ENDPOINT"]
            os.environ["AZURE_OPENAI_API_KEY"] = os.environ["AZURE_OPENAI_CLIENT_SECRET"]
            
        config = load_config("config/app_config.yaml")
        setup_logging("INFO", "./logs")
        logging.info("AI E2E Testing Agent Web Interface started")
        
        # Check if we have real credentials
        if (config["azure_openai"]["endpoint"] != "https://demo.openai.azure.com/" and 
            config["azure_openai"]["api_key"] != "demo-key-placeholder"):
            logging.info("Real Azure OpenAI credentials detected - Full functionality available")
        else:
            logging.info("Executing real test automation with Azure OpenAI")
            
    except Exception as e:
        logging.warning(f"Configuration not fully loaded: {e}")
        logging.warning("Some features may be limited without proper Azure OpenAI configuration")
        
        # Create minimal config for demo mode
        config = {
            "azure_openai": {
                "endpoint": "https://demo.openai.azure.com/",
                "api_key": "demo-key-placeholder",
                "deployment_name": "gpt-4.1"
            },
            "browser_config": {
                "headless": False,  # Default to visible browser
                "default_timeout": 180000,  # 3 minutes
                "navigation_timeout": 300000  # 5 minutes
            }
        }
        setup_logging("INFO", "./logs")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main frontend interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/execute")
async def execute_test(request: TestExecutionRequest):
    """Start test execution with the provided parameters."""
    try:
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"[{execution_id}] Starting test execution")
        
        # Initialize execution state
        active_executions[execution_id] = {
            "id": execution_id,
            "status": "initializing",
            "progress": 0,
            "current_step": "Starting execution...",
            "start_time": datetime.now().isoformat(),
            "instructions": request.instructions,
            "target_url": request.cluster_ip or request.base_url,
            "paused": False,
            "stop_requested": False
        }
        
        # Start background execution
        asyncio.create_task(run_test_execution(
            execution_id,
            request.instructions,
            request.cluster_ip or request.base_url,
            {"username": request.username, "password": request.password} if request.username else None,
            request.headless
        ))
        
        return {"execution_id": execution_id, "status": "started"}
        
    except Exception as e:
        logger.error(f"Failed to start execution: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")

@app.post("/api/control")
async def control_execution(control: ExecutionControl):
    """Control test execution (pause, resume, stop)"""
    
    execution_id = control.execution_id
    
    if execution_id not in active_executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    execution = active_executions[execution_id]
    
    if control.action == "pause":
        execution["paused"] = True
        execution["status"] = "paused"
        await broadcast_status_update(execution_id)
        return {"status": "paused"}
    
    elif control.action == "resume":
        execution["paused"] = False
        execution["status"] = "running"
        await broadcast_status_update(execution_id)
        return {"status": "resumed"}
    
    elif control.action == "stop":
        execution["stop_requested"] = True
        execution["status"] = "stopping"
        await broadcast_status_update(execution_id)
        return {"status": "stopping"}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

@app.get("/api/status/{execution_id}")
async def get_execution_status(execution_id: str):
    """Get current execution status"""
    
    if execution_id not in active_executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    execution = active_executions[execution_id]
    
    return ExecutionStatus(
        execution_id=execution_id,
        status=execution["status"],
        progress=execution["progress"],
        current_step=execution["current_step"],
        start_time=execution["start_time"],
        results=execution.get("results")
    )

@app.get("/api/executions")
async def list_executions():
    """List all executions"""
    
    executions = []
    for exec_id, execution in active_executions.items():
        executions.append({
            "execution_id": exec_id,
            "status": execution["status"],
            "progress": execution["progress"],
            "start_time": execution["start_time"],
            "instructions": execution["instructions"][:100] + "..." if len(execution["instructions"]) > 100 else execution["instructions"]
        })
    
    return {"executions": executions}

@app.websocket("/ws/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    """WebSocket endpoint for real-time updates"""
    
    await websocket.accept()
    
    # Add to websocket list for this execution
    if execution_id not in execution_websockets:
        execution_websockets[execution_id] = []
    execution_websockets[execution_id].append(websocket)
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            # Echo back for keepalive
            await websocket.send_text(f"echo: {data}")
    
    except WebSocketDisconnect:
        # Remove websocket from list
        if execution_id in execution_websockets:
            execution_websockets[execution_id].remove(websocket)
            if not execution_websockets[execution_id]:
                del execution_websockets[execution_id]

async def broadcast_status_update(execution_id: str):
    """Broadcast status update to all connected websockets"""
    
    if execution_id not in execution_websockets:
        return
    
    if execution_id not in active_executions:
        return
    
    execution = active_executions[execution_id]
    
    status_update = {
        "type": "status_update",
        "execution_id": execution_id,
        "status": execution["status"],
        "progress": execution["progress"],
        "current_step": execution["current_step"],
        "timestamp": datetime.now().isoformat()
    }
    
    # Send to all connected websockets for this execution
    disconnected_sockets = []
    for websocket in execution_websockets[execution_id]:
        try:
            await websocket.send_text(json.dumps(status_update))
        except:
            disconnected_sockets.append(websocket)
    
    # Clean up disconnected sockets
    for socket in disconnected_sockets:
        execution_websockets[execution_id].remove(socket)

async def run_test_execution(
    execution_id: str,
    instructions: str,
    target_url: Optional[str],
    user_credentials: Optional[Dict[str, str]],
    headless: bool = False  # Default to visible browser
):
    """Run the actual test execution in background"""
    
    execution = active_executions[execution_id]
    
    try:
        # Update config with headless setting
        global config
        config["browser_config"]["headless"] = headless
        
        # Initialize AI Controller
        execution["current_step"] = "Initializing AI Controller..."
        execution["progress"] = 10
        await broadcast_status_update(execution_id)
        
        ai_controller = AIController(config)
        
        # Check for pause/stop before starting
        await check_execution_control(execution_id)
        
        execution["status"] = "running"
        execution["current_step"] = "Executing AI agent pipeline..."
        execution["progress"] = 20
        await broadcast_status_update(execution_id)
            
        # Execute the test with periodic control checks
        result = await execute_with_control_checks(
            ai_controller, execution_id, instructions, target_url, user_credentials
        )
        
        # Update final results
        execution["status"] = "completed" if result.status == "completed" else "failed"
        execution["progress"] = 100
        execution["current_step"] = "Execution completed"
        execution["results"] = {
            "status": result.status,
            "execution_id": result.execution_id,
            "agent_results": {name: asdict(agent) for name, agent in result.agent_results.items()},
            "test_results": asdict(result.test_results) if result.test_results else None,
            "error": result.error
        }
        
        await broadcast_status_update(execution_id)
        
    except Exception as e:
        logging.error(f"Execution {execution_id} failed: {e}")
        execution["status"] = "failed"
        execution["current_step"] = f"Error: {str(e)}"
        execution["progress"] = 100
        execution["results"] = {"error": str(e)}
        await broadcast_status_update(execution_id)

async def execute_with_control_checks(
    ai_controller: AIController,
    execution_id: str,
    instructions: str,
    target_url: Optional[str],
    user_credentials: Optional[Dict[str, str]]
) -> TestExecutionResult:
    """Execute test with periodic checks for pause/stop controls"""
    
    # Custom execution wrapper that checks for controls
    class ControlledAIController:
        def __init__(self, controller, exec_id):
            self.controller = controller
            self.exec_id = exec_id
        
        async def execute_user_request(self, user_input, application_url=None, user_credentials=None):
            # Start the actual execution
            execution_task = asyncio.create_task(
                self.controller.execute_user_request(user_input, application_url, user_credentials)
            )
            
            # Periodic control check
            while not execution_task.done():
                await check_execution_control(self.exec_id)
                await asyncio.sleep(1)  # Check every second
            
            return await execution_task
    
    controlled_controller = ControlledAIController(ai_controller, execution_id)
    
    return await controlled_controller.execute_user_request(
        instructions, target_url, user_credentials
    )

async def check_execution_control(execution_id: str):
    """Check if execution should be paused or stopped"""
    
    if execution_id not in active_executions:
        return
    
    execution = active_executions[execution_id]
    
    # Handle stop request
    if execution.get("stop_requested", False):
        raise Exception("Execution stopped by user")
    
    # Handle pause request
    while execution.get("paused", False):
        await asyncio.sleep(1)  # Wait while paused
        if execution.get("stop_requested", False):
            raise Exception("Execution stopped by user")

if __name__ == "__main__":
    uvicorn.run(
        "web_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
