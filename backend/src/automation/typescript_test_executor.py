# src/automation/typescript_test_executor.py
"""
TypeScript Test Executor
Executes generated TypeScript Playwright test files using npx playwright test
"""

import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List

class TypeScriptTestExecutor:
    """Executor for TypeScript Playwright test files"""
    
    def __init__(self, e2e_path: str = None, timeout: int = 600):
        self.e2e_path = e2e_path or "/Users/varsaraf/Downloads/MVP/backend/e2e"
        self.timeout = timeout
        print(f"✅ [TypeScriptTestExecutor] Initialized with path: {self.e2e_path}")
    
    async def execute_typescript_test(self, test_file_path: str, session_dir: str, application_url: str, 
                          user_credentials: Dict[str, str] = None) -> Dict[str, Any]:
        """Execute a TypeScript Playwright test file"""
        try:
            print(f"🚀 [TypeScriptTestExecutor] Starting test execution: {test_file_path}")
            
            if not os.path.exists(test_file_path):
                return {"success": False, "error": f"Test file not found: {test_file_path}"}
            
            # Ensure dependencies are set up for automated execution
            await self._setup_dependencies()
            
            # Extract session ID from test filename for artifact management
            test_filename = os.path.basename(test_file_path)
            session_id = test_filename.split('_')[0] if '_' in test_filename else None
            
            # Use the provided session_dir or calculate it (should be e2e_path for new structure)
            if not session_dir:
                session_dir = os.path.dirname(test_file_path)
                if session_dir == self.e2e_path:
                    session_dir = self.e2e_path
            
            test_env = await self._prepare_test_environment(application_url, user_credentials)
            test_result = await self._run_playwright_test(test_file_path, session_dir, test_env)
            results = await self._parse_test_results(session_dir, session_id)
            artifacts = await self._collect_artifacts(session_dir, session_id)
            
            return {
                "success": test_result["exit_code"] == 0,
                "exit_code": test_result["exit_code"],
                "stdout": test_result["stdout"],
                "stderr": test_result["stderr"],
                "results": results,
                "artifacts": artifacts,
                "test_file": test_file_path,
                "session_dir": session_dir,
                "executed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ [TypeScriptTestExecutor] Test execution failed: {e}")
            return {"success": False, "error": str(e), "test_file": test_file_path}
    
    async def _setup_dependencies(self):
        """Setup required dependencies for test execution"""
        try:
            # Ensure e2e directory exists
            if not os.path.exists(self.e2e_path):
                os.makedirs(self.e2e_path, exist_ok=True)
            
            # Check if package.json exists in e2e directory
            package_json_path = os.path.join(self.e2e_path, "package.json")
            if not os.path.exists(package_json_path):
                print(f"⚠️ [TypeScriptTestExecutor] package.json not found at: {package_json_path}")
            
            # Check and install npm dependencies in e2e directory
            node_modules_path = os.path.join(self.e2e_path, "node_modules")
            if not os.path.exists(node_modules_path):
                print(f"📦 [TypeScriptTestExecutor] Installing npm dependencies in e2e directory...")
                await self._run_command(["npm", "install"], cwd=self.e2e_path)
            
            # Set up environment for browser installation to use system cache
            browser_env = os.environ.copy()
            browser_env["PLAYWRIGHT_BROWSERS_PATH"] = os.path.expanduser("~/Library/Caches/ms-playwright")
            
            # Install Playwright browsers using system cache (much faster)
            print(f"🌐 [TypeScriptTestExecutor] Installing Playwright browsers from cache...")
            await self._run_command(["npx", "playwright", "install", "chromium"], 
                                  cwd=self.e2e_path, env=browser_env)
            
            print(f"✅ [TypeScriptTestExecutor] Dependencies ready")
            
        except Exception as e:
            print(f"❌ [TypeScriptTestExecutor] Failed to setup dependencies: {e}")
            raise
    
    async def _prepare_test_environment(self, application_url: str, 
                                       user_credentials: Dict[str, str] = None) -> Dict[str, str]:
        """Prepare environment variables for test execution"""
        test_env = os.environ.copy()
        
        test_env["TEST_URL"] = application_url
        if user_credentials:
            test_env["TEST_USERNAME"] = user_credentials.get("username", "")
            test_env["TEST_PASSWORD"] = user_credentials.get("password", "")
        
        # Use system cache for browsers
        test_env["PLAYWRIGHT_BROWSERS_PATH"] = os.path.expanduser("~/Library/Caches/ms-playwright")
        test_env["CI"] = "false"
        test_env["NODE_ENV"] = "test"
        
        print(f"🔧 [TypeScriptTestExecutor] Environment prepared with URL: {application_url}")
        print(f"🌐 [TypeScriptTestExecutor] Using browser cache: {test_env['PLAYWRIGHT_BROWSERS_PATH']}")
        return test_env
    
    async def _run_playwright_test(self, test_file_path: str, session_dir: str, 
                                  test_env: Dict[str, str]) -> Dict[str, Any]:
        """Run the Playwright test using npx playwright test"""
        try:
            # Since test files are now directly in e2e folder, get just the filename
            test_filename = os.path.basename(test_file_path)
            
            # Extract session ID from filename (format: sessionId_testType.spec.ts)
            session_id = test_filename.split('_')[0] if '_' in test_filename else 'unknown'
            
            cmd = [
                "npx", "playwright", "test", 
                test_filename,  # Test file is directly in e2e folder
                "--config", "playwright.config.ts",  # Config is in e2e folder
                "--reporter", "html",
                "--output", f"test-results-{session_id}"  # Output to session-specific results folder
            ]
            
            print(f"🎬 [TypeScriptTestExecutor] Running command: {' '.join(cmd)}")
            print(f"📁 [TypeScriptTestExecutor] Working directory: {self.e2e_path}")
            print(f"📄 [TypeScriptTestExecutor] Test file: {test_filename}")
            print(f"🆔 [TypeScriptTestExecutor] Session ID: {session_id}")
            
            result = await self._run_command(cmd, cwd=self.e2e_path, env=test_env, timeout=self.timeout)
            
            if result["exit_code"] == 0:
                print(f"✅ [TypeScriptTestExecutor] Test execution completed successfully")
            else:
                print(f"⚠️ [TypeScriptTestExecutor] Test execution completed with issues")
            
            return result
            
        except Exception as e:
            print(f"❌ [TypeScriptTestExecutor] Playwright test execution failed: {e}")
            return {"exit_code": -1, "stdout": "", "stderr": str(e)}
    
    async def _run_command(self, cmd: List[str], cwd: str = None, 
                          env: Dict[str, str] = None, timeout: int = None) -> Dict[str, Any]:
        """Run a shell command asynchronously"""
        try:
            print(f"🔧 [TypeScriptTestExecutor] Executing: {' '.join(cmd)} in {cwd}")
            print(f"🌍 [TypeScriptTestExecutor] Environment: PATH={env.get('PATH', 'Not set')[:100]}..." if env else "🌍 [TypeScriptTestExecutor] No custom environment")
            print(f"⏱️ [TypeScriptTestExecutor] Timeout: {timeout or self.timeout} seconds")
            
            process = await asyncio.create_subprocess_exec(
                *cmd, cwd=cwd, env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout or self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise Exception(f"Command timed out after {timeout or self.timeout} seconds")
            
            stdout_text = stdout.decode('utf-8') if stdout else ""
            stderr_text = stderr.decode('utf-8') if stderr else ""
            
            if process.returncode != 0:
                print(f"⚠️ [TypeScriptTestExecutor] Command failed with exit code {process.returncode}")
                print(f"📤 STDOUT: {stdout_text[:1000]}{'...' if len(stdout_text) > 1000 else ''}")
                print(f"📤 STDERR: {stderr_text[:1000]}{'...' if len(stderr_text) > 1000 else ''}")
            else:
                print(f"✅ [TypeScriptTestExecutor] Command completed successfully")
                print(f"📤 STDOUT (first 500 chars): {stdout_text[:500]}{'...' if len(stdout_text) > 500 else ''}")
            
            return {
                "exit_code": process.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text
            }
            
        except Exception as e:
            print(f"❌ [TypeScriptTestExecutor] Command execution failed: {e}")
            return {"exit_code": -1, "stdout": "", "stderr": str(e)}
    
    async def _parse_test_results(self, session_dir: str, session_id: str = None) -> Dict[str, Any]:
        """Parse test results"""
        try:
            # If no session_id provided, session_dir should be e2e_path
            if not session_id and session_dir == self.e2e_path:
                # Look for any test-results-* folder in e2e directory
                test_results_folders = [d for d in os.listdir(self.e2e_path) 
                                      if d.startswith('test-results-') and os.path.isdir(os.path.join(self.e2e_path, d))]
                if test_results_folders:
                    # Use the most recent one
                    test_results_folder = sorted(test_results_folders)[-1]
                    html_report_path = os.path.join(self.e2e_path, test_results_folder, "index.html")
                else:
                    html_report_path = os.path.join(self.e2e_path, "test-results", "index.html")
            else:
                # Use session-specific results folder
                results_folder = f"test-results-{session_id}" if session_id else "test-results"
                html_report_path = os.path.join(self.e2e_path, results_folder, "index.html")
            
            results_summary = {
                "html_report_available": os.path.exists(html_report_path),
                "html_report_path": html_report_path if os.path.exists(html_report_path) else None,
                "parsed_at": datetime.now().isoformat()
            }
            
            if not results_summary["html_report_available"]:
                print(f"⚠️ [TypeScriptTestExecutor] HTML report not found at: {html_report_path}")
            else:
                print(f"📊 [TypeScriptTestExecutor] HTML report available at: {html_report_path}")
            
            return results_summary
            
        except Exception as e:
            print(f"❌ [TypeScriptTestExecutor] Failed to parse test results: {e}")
            return {"error": str(e), "parsed_at": datetime.now().isoformat()}
    
    async def _collect_artifacts(self, session_dir: str, session_id: str = None) -> List[Dict[str, Any]]:
        """Collect test artifacts"""
        artifacts = []
        
        try:
            # Build artifact directories based on new session ID structure
            if session_id:
                artifact_dirs = [
                    os.path.join(self.e2e_path, f"test-results-{session_id}"),
                    os.path.join(self.e2e_path, "screenshots"),
                    self.e2e_path
                ]
            else:
                # Fallback to old structure or generic locations
                artifact_dirs = [
                    os.path.join(session_dir, "test-results"),
                    os.path.join(session_dir, "screenshots"),
                    session_dir
                ]
            
            for artifact_dir in artifact_dirs:
                if os.path.exists(artifact_dir):
                    for root, dirs, files in os.walk(artifact_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            file_ext = os.path.splitext(file)[1].lower()
                            
                            if file_ext in ['.png', '.jpg', '.jpeg', '.webm', '.zip', '.html', '.json']:
                                artifacts.append({
                                    "type": self._get_artifact_type(file_ext),
                                    "name": file,
                                    "path": file_path,
                                    "size": os.path.getsize(file_path),
                                    "created": datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                                })
            
            print(f"📎 [TypeScriptTestExecutor] Collected {len(artifacts)} artifacts")
            return artifacts
            
        except Exception as e:
            print(f"❌ [TypeScriptTestExecutor] Failed to collect artifacts: {e}")
            return []
    
    def _get_artifact_type(self, file_ext: str) -> str:
        """Determine artifact type from file extension"""
        type_map = {
            '.png': 'screenshot', '.jpg': 'screenshot', '.jpeg': 'screenshot',
            '.webm': 'video', '.zip': 'trace', '.html': 'report', '.json': 'data'
        }
        return type_map.get(file_ext, 'unknown')
