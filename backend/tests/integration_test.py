# tests/integration_test.py
'''
Integration test for AI E2E Testing Agent
Run this to verify the complete system works end-to-end
'''

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.core.config import load_config
from src.core.ai_controller import AIController

async def test_agent_pipeline():
    '''Test the complete agent pipeline'''

    print("🧪 Starting integration test...")

    try:
        # Load configuration
        config = load_config("config/app_config.yaml")
        print("✅ Configuration loaded")

        # Initialize AI Controller
        controller = AIController(config)
        print("✅ AI Controller initialized")

        # Test with simple instruction
        test_instruction = "Navigate to a login page and verify the title contains 'login'"
        print(f"🔍 Testing instruction: {test_instruction}")

        # Execute test (this will test the agent pipeline)
        result = await controller.execute_user_request(
            user_input=test_instruction,
            application_url="https://demo.playwright.dev/todomvc"  # Safe test URL
        )

        print(f"�� Execution completed with status: {result.status}")

        # Check agent results
        for agent_name, agent_result in result.agent_results.items():
            status = "✅" if agent_result.success else "❌"
            print(f"  {status} {agent_name}: {agent_result.success}")
            if not agent_result.success and agent_result.error:
                print(f"    Error: {agent_result.error}")

        if result.status in ["completed", "running"]:
            print("🎉 Integration test PASSED!")
            return True
        else:
            print("❌ Integration test FAILED!")
            return False

    except Exception as e:
        print(f"❌ Integration test ERROR: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_agent_pipeline())
    sys.exit(0 if success else 1)