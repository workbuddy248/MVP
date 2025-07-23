# main.py
"""
AI E2E Testing Agent - Main Application Entry Point
Run this file to execute tests from natural language instructions
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.ai_controller import AIController
from src.core.config import load_config, setup_logging
from src.models.test_models import TestExecutionResult

# Initialize CLI and console
app = typer.Typer(help="AI-powered E2E Testing Agent for Legacy Java Applications")
console = Console()

@app.command()
def test(
    instructions: str = typer.Option(..., "--instructions", "-i", 
                                   help="Test instructions in natural language"),
    url: Optional[str] = typer.Option(None, "--url", "-u", 
                                     help="Target application URL"),
    username: Optional[str] = typer.Option(None, "--username", 
                                          help="Login username"),
    password: Optional[str] = typer.Option(None, "--password", 
                                          help="Login password"),
    config_file: str = typer.Option("config/app_config.yaml", "--config", "-c", 
                                   help="Configuration file path"),
    headless: bool = typer.Option(True, "--headless/--headed", 
                                 help="Run browser in headless mode"),
    verbose: bool = typer.Option(False, "--verbose", "-v", 
                                help="Enable verbose logging"),
    output_dir: str = typer.Option("./test_results", "--output", "-o", 
                                  help="Output directory for results")
):
    """
    Execute AI-generated E2E tests from natural language instructions
    
    Example usage:
    python main.py -i "Login with admin/cisco123 and verify dashboard loads" -u "https://catalyst-centre.com" --headed
    """
    
    # Display startup banner
    console.print(Panel.fit(
        "🤖 AI E2E Testing Agent\n"
        "Transforming natural language into automated tests",
        title="Starting Test Execution",
        border_style="blue"
    ))
    
    try:
        # Load configuration
        config = load_config(config_file)
        
        # Override config with CLI parameters
        if headless is not None:
            config["browser_config"]["headless"] = headless
        
        # Setup logging
        log_level = "DEBUG" if verbose else "INFO"
        setup_logging(log_level, output_dir)
        
        # Prepare credentials if provided
        user_credentials = None
        if username and password:
            user_credentials = {"username": username, "password": password}
        elif username or password:
            console.print("⚠️  Both username and password must be provided", style="yellow")
        
        # Execute the test
        result = asyncio.run(execute_test_request(
            config=config,
            instructions=instructions,
            url=url,
            user_credentials=user_credentials,
            output_dir=output_dir
        ))
        
        # Display results
        display_execution_results(result)
        
        # Exit with appropriate code
        sys.exit(0 if result.status in ["completed", "running"] else 1)
        
    except KeyboardInterrupt:
        console.print("\n⚠️  Test execution interrupted by user", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Fatal error: {str(e)}", style="red")
        if verbose:
            console.print_exception()
        sys.exit(1)

@app.command()
def validate(
    config_file: str = typer.Option("config/app_config.yaml", "--config", "-c", 
                                   help="Configuration file to validate")
):
    """Validate configuration and Azure OpenAI connection"""
    
    console.print("🔍 Validating configuration and connections...\n")
    
    try:
        # Load and validate config
        config = load_config(config_file)
        console.print("✅ Configuration file loaded successfully")
        
        # Test Azure OpenAI connection
        result = asyncio.run(test_azure_connection(config))
        
        if result:
            console.print("✅ Azure OpenAI connection successful")
            console.print("🎉 All validations passed! Ready to run tests.")
        else:
            console.print("❌ Azure OpenAI connection failed")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"❌ Validation failed: {str(e)}", style="red")
        sys.exit(1)

@app.command()
def init(
    project_name: str = typer.Option("my-e2e-tests", "--name", "-n", 
                                    help="Project name"),
    directory: str = typer.Option(".", "--dir", "-d", 
                                 help="Directory to create project in")
):
    """Initialize a new E2E testing project with configuration templates"""
    
    project_path = Path(directory) / project_name
    
    console.print(f"🚀 Initializing new E2E testing project: {project_name}")
    
    try:
        # Create project structure
        create_project_structure(project_path)
        
        console.print(f"✅ Project created at: {project_path}")
        console.print("\n📝 Next steps:")
        console.print("1. Copy your Azure OpenAI credentials to config/.env")
        console.print("2. Update config/app_config.yaml with your application details")
        console.print("3. Run: python main.py validate")
        console.print("4. Start testing: python main.py test -i 'your test instructions'")
        
    except Exception as e:
        console.print(f"❌ Project initialization failed: {str(e)}", style="red")
        sys.exit(1)

async def execute_test_request(
    config: Dict[str, Any],
    instructions: str,
    url: Optional[str] = None,
    user_credentials: Optional[Dict[str, str]] = None,
    output_dir: str = "./test_results"
) -> TestExecutionResult:
    """Execute test request using AI Controller"""
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Initialize AI Controller
    console.print("🧠 Initializing AI Controller...")
    ai_controller = AIController(config)
    
    # Display execution details
    console.print(f"\n📋 Test Details:")
    console.print(f"  Instructions: {instructions}")
    if url:
        console.print(f"  Target URL: {url}")
    if user_credentials:
        console.print(f"  Username: {user_credentials['username']}")
        console.print(f"  Password: {'*' * len(user_credentials['password'])}")
    
    # Execute with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("Executing AI agent pipeline...", total=None)
        
        # Execute the test request
        result = await ai_controller.execute_user_request(
            user_input=instructions,
            application_url=url,
            user_credentials=user_credentials
        )
        
        progress.update(task, description="✅ Execution completed")
    
    return result

async def test_azure_connection(config: Dict[str, Any]) -> bool:
    """Test Azure OpenAI connection"""
    
    try:
        from src.core.azure_client import AzureOpenAIClient
        
        client = AzureOpenAIClient(config["azure_openai"])
        
        # Simple test call
        response = await client.call_agent(
            agent_name="ConnectionTest",
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Connection successful' if you can read this.",
            response_format="text"
        )
        
        return response.success and "successful" in response.content.lower()
        
    except Exception as e:
        console.print(f"Connection test error: {e}", style="red")
        return False

def display_execution_results(result: TestExecutionResult):
    """Display test execution results in formatted tables"""
    
    console.print("\n" + "="*60)
    console.print("📊 EXECUTION RESULTS", style="bold blue")
    console.print("="*60)
    
    # Main summary
    status_color = "green" if result.status == "completed" else "red"
    console.print(f"\n🎯 Status: [{status_color}]{result.status.upper()}[/{status_color}]")
    console.print(f"🆔 Execution ID: {result.execution_id}")
    console.print(f"⏱️  Duration: {result.start_time} to {result.end_time or 'In Progress'}")
    
    # Agent results table
    if result.agent_results:
        console.print("\n🤖 Agent Execution Results:")
        
        agent_table = Table(show_header=True, header_style="bold cyan")
        agent_table.add_column("Agent", style="cyan")
        agent_table.add_column("Status", justify="center")
        agent_table.add_column("Details")
        
        for agent_name, agent_result in result.agent_results.items():
            status_emoji = "✅" if agent_result.success else "❌"
            status_text = "SUCCESS" if agent_result.success else "FAILED"
            status_style = "green" if agent_result.success else "red"
            
            details = "Completed successfully"
            if not agent_result.success and agent_result.error:
                details = agent_result.error[:50] + "..." if len(agent_result.error) > 50 else agent_result.error
            
            agent_table.add_row(
                agent_name,
                f"{status_emoji} [{status_style}]{status_text}[/{status_style}]",
                details
            )
        
        console.print(agent_table)
    
    # Test execution results
    if result.test_results:
        test_results = result.test_results
        console.print(f"\n🧪 Test Results: {test_results.test_name}")
        
        if test_results.summary:
            summary = test_results.summary
            
            # Summary table
            summary_table = Table(show_header=True, header_style="bold magenta")
            summary_table.add_column("Metric", style="magenta")
            summary_table.add_column("Value", justify="right")
            
            summary_table.add_row("Total Steps", str(summary.total_steps))
            summary_table.add_row("Passed", f"[green]{summary.passed}[/green]")
            summary_table.add_row("Failed", f"[red]{summary.failed}[/red]")
            summary_table.add_row("Success Rate", f"{summary.success_rate}%")
            
            console.print(summary_table)
        
        # Individual step results
        if test_results.step_results:
            console.print("\n📝 Step-by-Step Results:")
            for i, step in enumerate(test_results.step_results, 1):
                status_emoji = "✅" if step.status.value == "completed" else "❌"
                console.print(f"  {status_emoji} Step {i}: {step.description}")
                if step.error:
                    console.print(f"    Error: {step.error}", style="red")
    
    # Error information
    if result.error:
        console.print(f"\n❌ Error: {result.error}", style="red")
    
    console.print("\n" + "="*60)

def create_project_structure(project_path: Path):
    """Create new project structure with templates"""
    
    # Create directories
    directories = [
        "config",
        "test_results",
        "logs",
        "screenshots"
    ]
    
    for directory in directories:
        (project_path / directory).mkdir(parents=True, exist_ok=True)
    
    # Create configuration files
    config_content = """# AI E2E Testing Agent Configuration

azure_openai:
  endpoint: "${AZURE_ENDPOINT}"
  api_key: "${AZURE_OPENAI_API_KEY}"
  deployment_name: "gpt-4.1"
  api_version: "2024-07-01-preview"

application:
  name: "Your Application Name"
  type: "legacy_java"
  default_timeout: 30000

browser_config:
  type: "chromium"
  headless: true
  slow_mo: 1000

storage:
  base_path: "./test_data"

agents:
  nl_processor:
    temperature: 0.1
  test_strategy:
    temperature: 0.1
  test_generation:
    temperature: 0.1
"""
    
    readme_content = f"""# {project_path.name} - AI E2E Testing

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

2. Configure Azure OpenAI:
   - Copy your credentials to `config/.env`
   - Update `config/app_config.yaml`

3. Validate setup:
   ```bash
   python main.py validate
   ```

4. Run your first test:
   ```bash
   python main.py test -i "Login with admin credentials and verify dashboard"
   ```

## Example Commands

```bash
# Basic test
python main.py test -i "Navigate to login page and verify title"

# Test with credentials
python main.py test -i "Login and check dashboard" -u "https://app.com" --username admin --password secret

# Headed mode for debugging
python main.py test -i "Test checkout process" --headed -v
```
"""
    
    # Write files
    (project_path / "config" / "app_config.yaml").write_text(config_content)
    (project_path / "config" / ".env").write_text(env_content)
    (project_path / "README.md").write_text(readme_content)

if __name__ == "__main__":
    app()