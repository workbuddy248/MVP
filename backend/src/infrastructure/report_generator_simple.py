# src/infrastructure/report_generator_simple.py
"""
Simplified Report Generator 
Generates comprehensive test execution reports without Azure AI dependency
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Simplified Report Generator - No Azure AI Required
    Generates comprehensive test execution reports using rule-based logic
    """
    
    def __init__(self):
        # No Azure client needed - purely rule-based generation
        self.report_templates = self._load_report_templates()
        
    def _load_report_templates(self) -> Dict[str, str]:
        """Load report templates for different scenarios"""
        return {
            "success_summary": "✅ Test execution completed successfully with {success_rate}% success rate",
            "partial_success": "⚠️ Test execution completed with {success_rate}% success rate - some steps failed",
            "failure_summary": "❌ Test execution failed with {success_rate}% success rate",
            "error_summary": "💥 Test execution encountered critical errors and could not complete"
        }
    
    def generate_report(self, test_results: Dict[str, Any], execution_id: str) -> Dict[str, Any]:
        """
        Generate a comprehensive test report using rule-based analysis
        
        Args:
            test_results: Results from test execution
            execution_id: Unique execution identifier
            
        Returns:
            Comprehensive test report with insights and recommendations
        """
        try:
            logger.info(f"📊 Generating simplified report for execution: {execution_id}")
            
            # Analyze test results
            analysis = self._analyze_test_results(test_results)
            
            # Generate insights based on analysis
            insights = self._generate_insights(analysis, test_results)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(analysis, test_results)
            
            # Create comprehensive report
            report = {
                "execution_id": execution_id,
                "generated_at": datetime.now().isoformat(),
                "overall_status": analysis["overall_status"],
                "summary": self._generate_summary(analysis, test_results),
                "insights": insights,
                "recommendations": recommendations,
                "test_details": self._generate_test_details(test_results),
                "artifacts": self._collect_artifacts(test_results),
                "metadata": self._generate_metadata(),
                "performance_analysis": self._analyze_performance(test_results),
                "failure_analysis": self._analyze_failures(test_results) if analysis["has_failures"] else None
            }
            
            logger.info(f"✅ Simplified report generated successfully for {execution_id}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Simplified report generation failed: {e}")
            # Return basic error report
            return self._generate_error_report(execution_id, str(e))
    
    def _analyze_test_results(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results to determine overall status and key metrics"""
        
        analysis = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "success_rate": 0.0,
            "has_failures": False,
            "has_errors": False,
            "overall_status": "UNKNOWN",
            "execution_time": "Unknown",
            "critical_failures": 0,
            "healing_attempts": 0,
            "healing_successes": 0
        }
        
        try:
            # Analyze based on different result structures
            if "summary" in test_results and test_results["summary"]:
                # Use summary if available
                summary = test_results["summary"]
                analysis.update({
                    "total_tests": summary.get("total_steps", summary.get("total_tests", 0)),
                    "passed": summary.get("passed", 0),
                    "failed": summary.get("failed", 0),
                    "skipped": summary.get("skipped", 0),
                    "success_rate": summary.get("success_rate", 0.0)
                })
            
            elif "step_results" in test_results:
                # Analyze individual step results
                step_results = test_results.get("step_results", [])
                analysis["total_tests"] = len(step_results)
                
                for step in step_results:
                    status = step.get("status", "unknown").lower()
                    if status in ["completed", "passed", "success"]:
                        analysis["passed"] += 1
                    elif status in ["failed", "failure"]:
                        analysis["failed"] += 1
                        if step.get("critical", False):
                            analysis["critical_failures"] += 1
                    elif status in ["skipped", "skip"]:
                        analysis["skipped"] += 1
                    elif status in ["error"]:
                        analysis["errors"] += 1
                    
                    # Check for healing attempts
                    if step.get("healing_applied", False):
                        analysis["healing_attempts"] += 1
                        if status in ["completed", "passed", "success"]:
                            analysis["healing_successes"] += 1
            
            elif "agent_results" in test_results:
                # Analyze agent-based results
                agent_results = test_results.get("agent_results", {})
                analysis["total_tests"] = len(agent_results)
                
                for agent_name, result in agent_results.items():
                    if result.get("success", False):
                        analysis["passed"] += 1
                    else:
                        analysis["failed"] += 1
            
            # Calculate derived metrics
            if analysis["total_tests"] > 0:
                analysis["success_rate"] = round((analysis["passed"] / analysis["total_tests"]) * 100, 1)
            
            analysis["has_failures"] = analysis["failed"] > 0 or analysis["errors"] > 0
            analysis["has_errors"] = analysis["errors"] > 0
            
            # Determine overall status
            if analysis["has_errors"] or test_results.get("status") == "error":
                analysis["overall_status"] = "ERROR"
            elif analysis["success_rate"] >= 90:
                analysis["overall_status"] = "SUCCESS"
            elif analysis["success_rate"] >= 50:
                analysis["overall_status"] = "PARTIAL_SUCCESS"
            else:
                analysis["overall_status"] = "FAILURE"
            
            # Extract execution time
            start_time = test_results.get("start_time")
            end_time = test_results.get("end_time")
            if start_time and end_time:
                try:
                    start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration = end - start
                    analysis["execution_time"] = f"{duration.total_seconds():.1f}s"
                except:
                    analysis["execution_time"] = "Unknown"
            
        except Exception as e:
            logger.warning(f"Analysis error: {e}")
        
        return analysis
    
    def _generate_summary(self, analysis: Dict[str, Any], test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary"""
        
        status = analysis["overall_status"]
        success_rate = analysis["success_rate"]
        
        # Select appropriate summary template
        if status == "SUCCESS":
            summary_text = self.report_templates["success_summary"].format(success_rate=success_rate)
            status_icon = "✅"
        elif status == "PARTIAL_SUCCESS":
            summary_text = self.report_templates["partial_success"].format(success_rate=success_rate)
            status_icon = "⚠️"
        elif status == "FAILURE":
            summary_text = self.report_templates["failure_summary"].format(success_rate=success_rate)
            status_icon = "❌"
        else:
            summary_text = self.report_templates["error_summary"]
            status_icon = "💥"
        
        return {
            "status_icon": status_icon,
            "summary_text": summary_text,
            "success_rate": f"{success_rate}%",
            "total_tests": analysis["total_tests"],
            "passed": analysis["passed"],
            "failed": analysis["failed"],
            "skipped": analysis["skipped"],
            "execution_time": analysis["execution_time"],
            "environment": self._detect_environment(test_results)
        }
    
    def _generate_insights(self, analysis: Dict[str, Any], test_results: Dict[str, Any]) -> List[str]:
        """Generate rule-based insights from test results"""
        
        insights = []
        
        # Success rate insights
        if analysis["success_rate"] == 100:
            insights.append("🎉 Perfect execution - all tests passed successfully")
        elif analysis["success_rate"] >= 90:
            insights.append("✅ Excellent execution with minimal failures")
        elif analysis["success_rate"] >= 70:
            insights.append("⚠️ Good execution but room for improvement")
        elif analysis["success_rate"] >= 50:
            insights.append("📈 Mixed results - significant issues detected")
        else:
            insights.append("🚨 Poor execution - major issues require attention")
        
        # Healing insights
        if analysis["healing_attempts"] > 0:
            healing_rate = (analysis["healing_successes"] / analysis["healing_attempts"]) * 100
            insights.append(f"🔧 Self-healing activated {analysis['healing_attempts']} times with {healing_rate:.0f}% success rate")
        
        # Critical failure insights
        if analysis["critical_failures"] > 0:
            insights.append(f"⚠️ {analysis['critical_failures']} critical failures detected - immediate attention required")
        
        # Pattern detection
        patterns = self._detect_patterns(test_results)
        insights.extend(patterns)
        
        # Performance insights
        perf_insights = self._generate_performance_insights(test_results)
        insights.extend(perf_insights)
        
        return insights
    
    def _generate_recommendations(self, analysis: Dict[str, Any], test_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on test results"""
        
        recommendations = []
        
        # Failure-based recommendations
        if analysis["has_failures"]:
            recommendations.append("🔍 Review failed test steps and check application logs for root cause analysis")
            
            if analysis["critical_failures"] > 0:
                recommendations.append("🚨 Address critical failures immediately as they block core functionality")
        
        # Success-based recommendations
        if analysis["success_rate"] >= 90:
            recommendations.append("📈 Consider expanding test coverage to include more edge cases")
            recommendations.append("🔄 Add performance benchmarks to monitor application speed")
        
        # Healing recommendations
        if analysis["healing_attempts"] > analysis["healing_successes"]:
            recommendations.append("🔧 Review self-healing strategies for improved automatic recovery")
        
        # Environment-specific recommendations
        env_recs = self._generate_environment_recommendations(test_results)
        recommendations.extend(env_recs)
        
        # Generic best practices
        if analysis["total_tests"] < 5:
            recommendations.append("📊 Consider adding more comprehensive test scenarios")
        
        if "screenshots" in test_results and not test_results.get("screenshots"):
            recommendations.append("📸 Enable screenshot capture for better debugging and documentation")
        
        return recommendations
    
    def _generate_test_details(self, test_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate detailed test step information"""
        
        details = []
        
        # Process step results if available
        if "step_results" in test_results:
            for step in test_results["step_results"]:
                detail = {
                    "test_name": step.get("description", f"Step {step.get('step_id', 'Unknown')}"),
                    "status": self._normalize_status(step.get("status", "unknown")),
                    "duration": self._calculate_step_duration(step),
                    "action": step.get("action", "unknown"),
                    "target": step.get("target", ""),
                    "error_message": step.get("error") if step.get("status", "").lower() == "failed" else None,
                    "screenshot": step.get("screenshot_path"),
                    "healing_applied": step.get("healing_applied", False),
                    "selector_used": step.get("selector_used")
                }
                details.append(detail)
        
        # Process agent results if available
        elif "agent_results" in test_results:
            for agent_name, result in test_results["agent_results"].items():
                detail = {
                    "test_name": agent_name.replace('_', ' ').title(),
                    "status": "passed" if result.get("success", False) else "failed",
                    "duration": "N/A",
                    "error_message": result.get("error") if not result.get("success", False) else None
                }
                details.append(detail)
        
        return details
    
    def _collect_artifacts(self, test_results: Dict[str, Any]) -> Dict[str, List[str]]:
        """Collect test artifacts and evidence"""
        
        artifacts = {
            "screenshots": [],
            "logs": [],
            "reports": [],
            "videos": []
        }
        
        # Collect screenshots
        if "screenshots" in test_results:
            artifacts["screenshots"] = test_results["screenshots"]
        
        # Collect step screenshots
        if "step_results" in test_results:
            for step in test_results["step_results"]:
                if step.get("screenshot_path"):
                    artifacts["screenshots"].append(step["screenshot_path"])
        
        # Collect logs
        if "logs" in test_results:
            artifacts["logs"] = test_results["logs"]
        
        # Add standard artifacts
        artifacts["logs"].append("execution.log")
        artifacts["reports"].append("test_report.json")
        
        return artifacts
    
    def _generate_metadata(self) -> Dict[str, Any]:
        """Generate report metadata"""
        
        return {
            "framework": "Playwright",
            "generator": "Simplified Report Generator v1.0",
            "browser": "Chromium",
            "platform": "Cross-platform",
            "report_version": "1.0",
            "generated_by": "AI Test Automation Platform"
        }
    
    def _analyze_performance(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance metrics"""
        
        performance = {
            "total_execution_time": "Unknown",
            "average_step_time": "Unknown",
            "fastest_step": "Unknown",
            "slowest_step": "Unknown",
            "performance_grade": "N/A"
        }
        
        try:
            if "step_results" in test_results:
                step_times = []
                for step in test_results["step_results"]:
                    duration = self._calculate_step_duration_seconds(step)
                    if duration > 0:
                        step_times.append(duration)
                
                if step_times:
                    avg_time = sum(step_times) / len(step_times)
                    performance.update({
                        "average_step_time": f"{avg_time:.1f}s",
                        "fastest_step": f"{min(step_times):.1f}s",
                        "slowest_step": f"{max(step_times):.1f}s"
                    })
                    
                    # Performance grading
                    if avg_time < 5:
                        performance["performance_grade"] = "A - Excellent"
                    elif avg_time < 15:
                        performance["performance_grade"] = "B - Good"
                    elif avg_time < 30:
                        performance["performance_grade"] = "C - Average"
                    else:
                        performance["performance_grade"] = "D - Needs Improvement"
            
            # Calculate total execution time
            start_time = test_results.get("start_time")
            end_time = test_results.get("end_time")
            if start_time and end_time:
                try:
                    start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration = end - start
                    performance["total_execution_time"] = f"{duration.total_seconds():.1f}s"
                except:
                    pass
        
        except Exception as e:
            logger.debug(f"Performance analysis error: {e}")
        
        return performance
    
    def _analyze_failures(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze failure patterns and root causes"""
        
        failure_analysis = {
            "total_failures": 0,
            "failure_categories": {},
            "common_patterns": [],
            "root_causes": [],
            "suggested_fixes": []
        }
        
        failures = []
        
        # Collect failures from step results
        if "step_results" in test_results:
            for step in test_results["step_results"]:
                if step.get("status", "").lower() in ["failed", "error"]:
                    failures.append({
                        "step": step.get("description", "Unknown"),
                        "error": step.get("error", "Unknown error"),
                        "action": step.get("action", "unknown")
                    })
        
        # Collect failures from agent results
        if "agent_results" in test_results:
            for agent_name, result in test_results["agent_results"].items():
                if not result.get("success", False):
                    failures.append({
                        "step": agent_name,
                        "error": result.get("error", "Unknown error"),
                        "action": "agent_execution"
                    })
        
        failure_analysis["total_failures"] = len(failures)
        
        # Categorize failures
        categories = {}
        patterns = []
        root_causes = []
        fixes = []
        
        for failure in failures:
            error = failure["error"].lower()
            
            # Categorize by error type
            if "timeout" in error:
                categories["timeout"] = categories.get("timeout", 0) + 1
                patterns.append("Timeout-related failures detected")
                root_causes.append("Application or network latency issues")
                fixes.append("Increase timeout values or optimize application performance")
            
            elif "element not found" in error or "selector" in error:
                categories["selector_issues"] = categories.get("selector_issues", 0) + 1
                patterns.append("Element selector failures")
                root_causes.append("UI changes or dynamic content loading issues")
                fixes.append("Update element selectors or add wait conditions")
            
            elif "network" in error or "connection" in error:
                categories["network"] = categories.get("network", 0) + 1
                patterns.append("Network connectivity issues")
                root_causes.append("Network infrastructure or service availability")
                fixes.append("Check network connectivity and service status")
            
            elif "authentication" in error or "login" in error:
                categories["authentication"] = categories.get("authentication", 0) + 1
                patterns.append("Authentication failures")
                root_causes.append("Invalid credentials or authentication service issues")
                fixes.append("Verify credentials and authentication configuration")
            
            elif "azure" in error or "openai" in error:
                categories["ai_service"] = categories.get("ai_service", 0) + 1
                patterns.append("AI service integration issues")
                root_causes.append("Azure OpenAI service connectivity or configuration")
                fixes.append("Check Azure OpenAI credentials and service availability")
            
            else:
                categories["other"] = categories.get("other", 0) + 1
        
        failure_analysis.update({
            "failure_categories": categories,
            "common_patterns": list(set(patterns)),
            "root_causes": list(set(root_causes)),
            "suggested_fixes": list(set(fixes))
        })
        
        return failure_analysis
    
    def _detect_patterns(self, test_results: Dict[str, Any]) -> List[str]:
        """Detect patterns in test execution"""
        
        patterns = []
        
        # Check for Cisco Catalyst Centre specific patterns
        if "cisco" in str(test_results).lower() or "catalyst" in str(test_results).lower():
            patterns.append("🏢 Cisco Catalyst Centre application detected - legacy app optimizations active")
        
        # Check for browser-specific patterns
        if "step_results" in test_results:
            screenshot_count = sum(1 for step in test_results["step_results"] if step.get("screenshot_path"))
            if screenshot_count > 0:
                patterns.append(f"📸 {screenshot_count} screenshots captured for debugging")
        
        return patterns
    
    def _generate_performance_insights(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate performance-related insights"""
        
        insights = []
        
        # Analyze execution time
        start_time = test_results.get("start_time")
        end_time = test_results.get("end_time")
        
        if start_time and end_time:
            try:
                start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration = end - start
                total_seconds = duration.total_seconds()
                
                if total_seconds > 300:  # 5 minutes
                    insights.append("⏰ Long execution time detected - consider optimizing test steps or application performance")
                elif total_seconds < 30:  # 30 seconds
                    insights.append("⚡ Fast execution time - excellent performance")
                
            except:
                pass
        
        return insights
    
    def _generate_environment_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate environment-specific recommendations"""
        
        recommendations = []
        
        # Browser recommendations
        recommendations.append("🌐 Consider testing across multiple browsers for compatibility")
        
        # Legacy application recommendations
        if self._is_legacy_application(test_results):
            recommendations.append("🏗️ Legacy application detected - ensure adequate timeouts and stability checks")
            recommendations.append("📱 Consider modernizing application UI for better automation reliability")
        
        return recommendations
    
    def _detect_environment(self, test_results: Dict[str, Any]) -> str:
        """Detect test environment from results"""
        
        # Check for environment indicators
        test_str = str(test_results).lower()
        
        if "localhost" in test_str or "127.0.0.1" in test_str:
            return "Local Development"
        elif "staging" in test_str or "test" in test_str:
            return "Staging/Test"
        elif "prod" in test_str or "production" in test_str:
            return "Production"
        else:
            return "Unknown Environment"
    
    def _is_legacy_application(self, test_results: Dict[str, Any]) -> bool:
        """Detect if testing a legacy application"""
        
        test_str = str(test_results).lower()
        legacy_indicators = ["cisco", "catalyst", "dna", "java", "legacy"]
        
        return any(indicator in test_str for indicator in legacy_indicators)
    
    def _normalize_status(self, status: str) -> str:
        """Normalize status values"""
        
        status_lower = status.lower()
        
        if status_lower in ["completed", "passed", "success"]:
            return "passed"
        elif status_lower in ["failed", "failure"]:
            return "failed"
        elif status_lower in ["skipped", "skip"]:
            return "skipped"
        elif status_lower in ["error"]:
            return "error"
        else:
            return status_lower
    
    def _calculate_step_duration(self, step: Dict[str, Any]) -> str:
        """Calculate human-readable step duration"""
        
        try:
            start_time = step.get("start_time")
            end_time = step.get("end_time")
            
            if start_time and end_time:
                start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration = end - start
                return f"{duration.total_seconds():.1f}s"
        except:
            pass
        
        return "N/A"
    
    def _calculate_step_duration_seconds(self, step: Dict[str, Any]) -> float:
        """Calculate step duration in seconds"""
        
        try:
            start_time = step.get("start_time")
            end_time = step.get("end_time")
            
            if start_time and end_time:
                start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration = end - start
                return duration.total_seconds()
        except:
            pass
        
        return 0.0
    
    def _generate_error_report(self, execution_id: str, error_message: str) -> Dict[str, Any]:
        """Generate basic error report when report generation fails"""
        
        return {
            "execution_id": execution_id,
            "generated_at": datetime.now().isoformat(),
            "overall_status": "ERROR",
            "summary": {
                "status_icon": "💥",
                "summary_text": "Report generation failed",
                "success_rate": "0%",
                "total_tests": 0,
                "passed": 0,
                "failed": 1,
                "execution_time": "Unknown",
                "environment": "Unknown"
            },
            "insights": [
                "🚨 Report generation encountered an error",
                f"📝 Error details: {error_message}"
            ],
            "recommendations": [
                "🔍 Check test execution logs for detailed error information",
                "🔧 Verify test configuration and retry execution"
            ],
            "test_details": [],
            "artifacts": {"screenshots": [], "logs": [], "reports": []},
            "metadata": self._generate_metadata(),
            "error": error_message
        }
    
    # Additional utility methods for enhanced reporting
    
    def generate_console_report(self, test_results: Dict[str, Any]) -> str:
        """Generate a console-friendly text report"""
        
        try:
            report = self.generate_report(test_results, test_results.get("execution_id", "unknown"))
            
            console_report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    TEST EXECUTION REPORT                     ║
╠══════════════════════════════════════════════════════════════╣
║ Execution ID: {report['execution_id']:<44} ║
║ Status: {report['summary']['status_icon']} {report['overall_status']:<48} ║
║ Success Rate: {report['summary']['success_rate']:<44} ║
║ Total Tests: {report['summary']['total_tests']:<45} ║
║ Passed: {report['summary']['passed']:<48} ║
║ Failed: {report['summary']['failed']:<48} ║
║ Execution Time: {report['summary']['execution_time']:<40} ║
╠══════════════════════════════════════════════════════════════╣
║                         INSIGHTS                             ║
╠══════════════════════════════════════════════════════════════╣
"""
            
            for insight in report['insights'][:3]:  # Show top 3 insights
                console_report += f"║ {insight[:58]:<58} ║\n"
            
            console_report += """╠══════════════════════════════════════════════════════════════╣
║                     RECOMMENDATIONS                         ║
╠══════════════════════════════════════════════════════════════╣
"""
            
            for rec in report['recommendations'][:3]:  # Show top 3 recommendations
                console_report += f"║ {rec[:58]:<58} ║\n"
            
            console_report += "╚══════════════════════════════════════════════════════════════╝"
            
            return console_report
            
        except Exception as e:
            return f"Console report generation failed: {e}"
    
    def save_report_to_file(self, report: Dict[str, Any], output_path: str = None) -> str:
        """Save report to JSON file"""
        
        try:
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"test_reports/report_{report['execution_id']}_{timestamp}.json"
            
            # Ensure directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"📄 Report saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            return ""

if __name__ == "__main__":
    print("Simplified Report Generator implementation completed!")
    print("✅ Rule-based report generation")
    print("✅ No Azure AI dependency")
    print("✅ Comprehensive analysis and insights")
    print("✅ Performance and failure analysis")
    print("\nNext: Fix basic login test issues...")