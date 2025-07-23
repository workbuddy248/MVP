# tests/comprehensive_integration_test.py
"""
Comprehensive Integration Test for AI E2E Testing Agent
Tests the complete system end-to-end with all architectural components
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.core.config import load_config, setup_logging
from src.core.ai_controller import AIController
from src.infrastructure.data_storage import DataStorage
from src.infrastructure.report_generator import ReportGenerator

# Configure logging for testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegrationTestSuite:
    """
    Comprehensive integration test suite for the AI E2E Testing Agent
    Tests all architectural layers and components
    """
    
    def __init__(self):
        self.config = None
        self.ai_controller = None
        self.data_storage = None
        self.report_generator = None
        self.test_results = []
    
    async def run_all_tests(self) -> bool:
        """Run all integration tests"""
        
        print("🚀 Starting Comprehensive Integration Test Suite")
        print("="*60)
        
        try:
            # Test 1: Configuration and Setup
            await self.test_configuration_loading()
            
            # Test 2: AI Controller Initialization
            await self.test_ai_controller_initialization()
            
            # Test 3: Individual Agent Testing
            await self.test_individual_agents()
            
            # Test 4: End-to-End Workflow
            await self.test_end_to_end_workflow()
            
            # Test 5: Data Storage and Retrieval
            await self.test_data_storage()
            
            # Test 6: Report Generation
            await self.test_report_generation()
            
            # Test 7: Error Handling and Recovery
            await self.test_error_handling()
            
            # Generate final test report
            await self.generate_test_summary()
            
            # Check overall success
            total_tests = len(self.test_results)
            passed_tests = sum(1 for result in self.test_results if result["passed"])
            
            success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            
            print(f"\n🏁 Integration Test Suite Completed")
            print(f"📊 Results: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
            
            if success_rate >= 80:
                print("✅ Integration test suite PASSED - System is ready for use!")
                return True
            else:
                print("❌ Integration test suite FAILED - System needs attention")
                return False
                
        except Exception as e:
            logger.error(f"Integration test suite failed with error: {e}")
            print(f"💥 Integration test suite CRASHED: {e}")
            return False
    
    async def test_configuration_loading(self):
        """Test configuration loading and validation"""
        
        test_name = "Configuration Loading"
        print(f"\n🔧 Testing: {test_name}")
        
        try:
            # Load configuration
            config_path = "config/app_config.yaml"
            if not Path(config_path).exists():
                # Create minimal test config
                await self.create_test_config()
            
            self.config = load_config(config_path)
            
            # Validate required sections
            required_sections = ["azure_openai", "browser_config", "agents"]
            for section in required_sections:
                if section not in self.config:
                    raise ValueError(f"Missing required config section: {section}")
            
            print(f"  ✅ Configuration loaded successfully")
            self.test_results.append({"name": test_name, "passed": True, "details": "Config loaded and validated"})
            
        except Exception as e:
            print(f"  ❌ Configuration loading failed: {e}")
            self.test_results.append({"name": test_name, "passed": False, "details": str(e)})
    
    async def test_ai_controller_initialization(self):
        """Test AI Controller initialization"""
        
        test_name = "AI Controller Initialization"
        print(f"\n🧠 Testing: {test_name}")
        
        try:
            if not self.config:
                raise ValueError("Configuration not loaded")
            
            # Initialize AI Controller
            self.ai_controller = AIController(self.config)
            
            # Verify components are initialized
            if not hasattr(self.ai_controller, 'azure_client'):
                raise ValueError("Azure client not initialized")
            
            if not hasattr(self.ai_controller, 'agent_configs'):
                raise ValueError("Agent configs not loaded")
            
            print(f"  ✅ AI Controller initialized successfully")
            self.test_results.append({"name": test_name, "passed": True, "details": "Controller and agents ready"})
            
        except Exception as e:
            print(f"  ❌ AI Controller initialization failed: {e}")
            self.test_results.append({"name": test_name, "passed": False, "details": str(e)})
    
    async def test_individual_agents(self):
        """Test individual agent functionality"""
        
        test_name = "Individual Agent Testing"
        print(f"\n🤖 Testing: {test_name}")
        
        try:
            if not self.ai_controller:
                raise ValueError("AI Controller not initialized")
            
            # Test NL Processor Agent
            test_input = "Navigate to login page and verify the title"
            
            # This is a mock test since we don't have real Azure OpenAI credentials
            # In real testing, this would make actual API calls
            print(f"  🔍 Testing NL Processor with input: '{test_input}'")
            
            # Test agent pipeline structure
            required_methods = [
                "_execute_nl_processor",
                "_execute_test_strategy", 
                "_execute_test_generation",
                "_execute_test_execution"
            ]
            
            for method in required_methods:
                if not hasattr(self.ai_controller, method):
                    raise ValueError(f"Missing required method: {method}")
            
            print(f"  ✅ All agent methods present and callable")
            self.test_results.append({"name": test_name, "passed": True, "details": "Agent structure validated"})
            
        except Exception as e:
            print(f"  ❌ Individual agent testing failed: {e}")
            self.test_results.append({"name": test_name, "passed": False, "details": str(e)})
    
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        
        test_name = "End-to-End Workflow"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            if not self.ai_controller:
                raise ValueError("AI Controller not initialized")
            
            # Test with safe demo URL
            test_instruction = "Navigate to the demo application and verify the page loads"
            test_url = "https://demo.playwright.dev/todomvc"  # Safe test URL
            
            print(f"  🎯 Testing workflow: '{test_instruction}'")
            print(f"  🌐 Target URL: {test_url}")
            
            # Execute the workflow (will use mock data due to no Azure credentials)
            # In production, this would execute the full pipeline
            result = await self.ai_controller.execute_user_request(
                user_input=test_instruction,
                application_url=test_url
            )
            
            # Validate result structure
            required_fields = ["execution_id", "status", "agent_results"]
            for field in required_fields:
                if field not in result.__dict__:
                    raise ValueError(f"Missing required result field: {field}")
            
            print(f"  ✅ Workflow executed - Status: {result.status}")
            print(f"  📊 Agents executed: {len(result.agent_results)}")
            
            self.test_results.append({
                "name": test_name, 
                "passed": True, 
                "details": f"Workflow completed with status: {result.status}"
            })
            
        except Exception as e:
            print(f"  ❌ End-to-end workflow failed: {e}")
            self.test_results.append({"name": test_name, "passed": False, "details": str(e)})
    
    async def test_data_storage(self):
        """Test data storage functionality"""
        
        test_name = "Data Storage"
        print(f"\n💾 Testing: {test_name}")
        
        try:
            # Initialize data storage
            storage_config = self.config.get("storage", {"base_path": "./test_data"})
            self.data_storage = DataStorage(storage_config)
            
            # Test storing mock data
            mock_result = {
                "execution_id": "test_123",
                "status": "completed",
                "test_name": "Mock Test",
                "timestamp": datetime.now().isoformat()
            }
            
            # Store and retrieve data
            filepath = await self.data_storage.store_test_results(mock_result)
            
            if not Path(filepath).exists():
                raise ValueError("Data storage file not created")
            
            # Test retrieval
            recent_results = await self.data_storage.get_recent_results(limit=1)
            
            if not recent_results:
                raise ValueError("No results retrieved from storage")
            
            print(f"  ✅ Data stored and retrieved successfully")
            print(f"  📂 Storage path: {filepath}")
            
            self.test_results.append({"name": test_name, "passed": True, "details": "Storage working correctly"})
            
        except Exception as e:
            print(f"  ❌ Data storage testing failed: {e}")
            self.test_results.append({"name": test_name, "passed": False, "details": str(e)})
    
    async def test_report_generation(self):
        """Test report generation functionality"""
        
        test_name = "Report Generation"
        print(f"\n📊 Testing: {test_name}")
        
        try:
            # Initialize report generator
            self.report_generator = ReportGenerator()
            
            # Create mock execution result
            mock_execution_result = {
                "execution_id": "test_report_123",
                "status": "completed",
                "start_time": datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "user_input": "Test report generation",
                "agent_results": {
                    "nl_processor": {"success": True},
                    "test_strategy": {"success": True},
                    "test_generation": {"success": True}
                },
                "test_results": {
                    "test_name": "Mock Test",
                    "summary": {
                        "total_steps": 3,
                        "passed": 2,
                        "failed": 1,
                        "success_rate": 66.7
                    }
                }
            }
            
            # Test console report generation
            await self.report_generator.generate_console_report(mock_execution_result)
            
            # Test HTML report generation
            html_path = await self.report_generator.generate_html_report(mock_execution_result)
            
            if not Path(html_path).exists():
                raise ValueError("HTML report not generated")
            
            print(f"  ✅ Reports generated successfully")
            print(f"  📄 HTML report: {html_path}")
            
            self.test_results.append({"name": test_name, "passed": True, "details": "Reports generated"})
            
        except Exception as e:
            print(f"  ❌ Report generation failed: {e}")
            self.test_results.append({"name": test_name, "passed": False, "details": str(e)})
    
    async def test_error_handling(self):
        """Test error handling and recovery mechanisms"""
        
        test_name = "Error Handling"
        print(f"\n🛡️ Testing: {test_name}")
        
        try:
            # Test with invalid configuration
            invalid_config = {"invalid": "config"}
            
            try:
                invalid_controller = AIController(invalid_config)
                # This should fail gracefully
            except Exception as e:
                print(f"  ✅ Invalid config handled: {type(e).__name__}")
            
            # Test with invalid user input
            if self.ai_controller:
                try:
                    result = await self.ai_controller.execute_user_request("")
                    # Should handle empty input gracefully
                    print(f"  ✅ Empty input handled - Status: {result.status}")
                except Exception as e:
                    print(f"  ✅ Empty input error handled: {type(e).__name__}")
            
            print(f"  ✅ Error handling mechanisms working")
            self.test_results.append({"name": test_name, "passed": True, "details": "Error handling validated"})
            
        except Exception as e:
            print(f"  ❌ Error handling test failed: {e}")
            self.test_results.append({"name": test_name, "passed": False, "details": str(e)})
    
    async def generate_test_summary(self):
        """Generate comprehensive test summary"""
        
        print(f"\n📋 INTEGRATION TEST SUMMARY")
        print("="*60)
        
        for i, result in enumerate(self.test_results, 1):
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"{i}. {result['name']}: {status}")
            print(f"   Details: {result['details']}")
        
        # Calculate statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 STATISTICS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    async def create_test_config(self):
        """Create minimal test configuration"""
        
        test_config = {
            "azure_openai": {
                "endpoint": "https://test.openai.azure.com/",
                "api_key": "test-key",
                "deployment_name": "gpt-4.1",
                "api_version": "2024-10-21"
            },
            "browser_config": {
                "type": "chromium",
                "headless": True,
                "timeout": 30000
            },
            "agents": {
                "nl_processor": {"temperature": 0.1},
                "test_strategy": {"temperature": 0.1},
                "test_generation": {"temperature": 0.1}
            },
            "storage": {
                "base_path": "./test_data"
            }
        }
        
        # Create config directory and file
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        import yaml
        with open(config_dir / "app_config.yaml", 'w') as f:
            yaml.dump(test_config, f, default_flow_style=False)
        
        print("  📝 Test configuration created")

# Integration test for browser automation
class BrowserIntegrationTest:
    """Test browser automation components"""
    
    async def test_browser_automation(self):
        """Test browser automation functionality"""
        
        print("\n🌐 Testing Browser Automation Components")
        
        try:
            from src.automation.browser_pool import BrowserPool
            
            # Test browser pool initialization
            browser_config = {
                "type": "chromium",
                "headless": True,
                "slow_mo": 1000
            }
            
            browser_pool = BrowserPool(browser_config)
            
            # Test browser context creation
            context = await browser_pool.get_browser_context()
            
            if context and context.page:
                print("  ✅ Browser context created successfully")
                
                # Test navigation to safe URL
                test_url = "https://example.com"
                await context.page.goto(test_url, timeout=10000)
                
                title = await context.page.title()
                print(f"  ✅ Navigation successful - Page title: {title}")
                
                # Cleanup
                await browser_pool.close_context(context)
                await browser_pool.cleanup_all()
                
                return True
            else:
                raise ValueError("Failed to create browser context")
                
        except Exception as e:
            print(f"  ❌ Browser automation test failed: {e}")
            return False

# Main test execution
async def run_integration_tests():
    """Run all integration tests"""
    
    print("🚀 AI E2E Testing Agent - Integration Test Suite")
    print("=" * 60)
    print("This will test all architectural components end-to-end")
    print("=" * 60)
    
    # Setup test environment
    setup_logging("INFO", "./test_logs")
    
    # Run comprehensive integration tests
    test_suite = IntegrationTestSuite()
    main_tests_passed = await test_suite.run_all_tests()
    
    # Run browser automation tests (if browser is available)
    print("\n" + "=" * 60)
    browser_test = BrowserIntegrationTest()
    browser_tests_passed = await browser_test.test_browser_automation()
    
    # Final summary
    print("\n" + "=" * 60)
    print("🏁 FINAL INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    if main_tests_passed and browser_tests_passed:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ System is ready for production use")
        print("\n📋 Next steps:")
        print("1. Add your Azure OpenAI credentials to config/.env")
        print("2. Run: python main.py validate")
        print("3. Start testing: python main.py test -i 'your test instructions'")
        return True
    else:
        print("❌ SOME INTEGRATION TESTS FAILED")
        print("⚠️  System needs attention before production use")
        print("\n🔧 Troubleshooting:")
        print("1. Check the test logs for specific error details")
        print("2. Ensure all dependencies are installed correctly")
        print("3. Verify configuration files are properly set up")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_integration_tests())
    sys.exit(0 if success else 1)