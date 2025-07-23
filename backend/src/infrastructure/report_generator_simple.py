# src/infrastructure/report_generator.py
"""
Report Generator
Generates comprehensive test execution reports
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any
from ..core.azure_client import AzureOpenAIClient

class ReportGenerator:
    """
    Agent responsible for generating test execution reports
    """
    
    def __init__(self, azure_client: AzureOpenAIClient):
        self.azure_client = azure_client
    
    def generate_report(self, test_results: Dict[str, Any], execution_id: str) -> Dict[str, Any]:
        """
        Generate a comprehensive test report
        
        Args:
            test_results: Results from test execution
            execution_id: Unique execution identifier
            
        Returns:
            Comprehensive test report
        """
        try:
            # Use Azure OpenAI for intelligent report generation
            system_prompt = self._get_report_generation_prompt()
            user_prompt = f"""
            Execution ID: {execution_id}
            Test Results: {json.dumps(test_results, indent=2)}
            
            Generate a comprehensive test execution report with insights and recommendations.
            """
            
            # Call Azure OpenAI
            response = self.azure_client.call_agent_sync(
                agent_name="ReportGenerator",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                temperature=0.2
            )
            
            if response.success:
                return response.content
            else:
                raise Exception(f"Azure OpenAI report generation failed: {response.error}")
                
        except Exception as e:
            print(f"Report Generator Azure call failed: {e}")
            raise Exception(f"Report generation failed: {e}")

    def _generate_report_prompt(self, test_results: Dict[str, Any], execution_id: str) -> str:
        """Generate prompt for report generation"""
        return f"""
        Generate a comprehensive test execution report for the following test results:
        
        Execution ID: {execution_id}
        Test Results: {test_results}
        
        Requirements:
        1. Analyze test execution data and provide insights
        2. Calculate success rates and performance metrics
        3. Identify patterns in failures and successes
        4. Provide actionable recommendations for improvement
        5. Create executive summary suitable for stakeholders
        6. Include technical details for developers
        
        Return JSON format:
        {{
            "execution_id": "{execution_id}",
            "generated_at": "ISO timestamp",
            "overall_status": "SUCCESS/PARTIAL_SUCCESS/FAILURE",
            "summary": {{
                "status_icon": "✅/⚠️/❌",
                "success_rate": "percentage",
                "total_tests": number,
                "passed": number,
                "failed": number,
                "execution_time": "duration",
                "environment": "description"
            }},
            "test_details": [
                {{
                    "test_name": "name",
                    "status": "passed/failed",
                    "duration": "time",
                    "screenshot": "path",
                    "error_message": "if failed"
                }}
            ],
            "insights": [
                "insight 1",
                "insight 2"
            ],
            "recommendations": [
                "recommendation 1",
                "recommendation 2"
            ],
            "artifacts": {{
                "screenshots": ["list"],
                "videos": ["list"],
                "logs": ["list"]
            }},
            "metadata": {{
                "framework": "Playwright",
                "browser": "browser_name",
                "platform": "platform_name",
                "report_version": "1.0"
            }}
        }}
        """
        
        # Add standard artifacts
        artifacts["logs"].append("execution.log")
        artifacts["reports"].append("test_report.json")
        
        return artifacts
    
    def _get_report_generation_prompt(self) -> str:
        """Get system prompt for report generation"""
        return """You are an expert test report analyst specializing in web automation testing.

Your task is to analyze test execution results and generate comprehensive, actionable reports.

Focus on:

1. Executive Summary:
   - Overall test execution status
   - Success rate and key metrics
   - High-level insights and trends

2. Detailed Analysis:
   - Individual test results breakdown
   - Failure analysis and root causes
   - Performance observations

3. Insights and Patterns:
   - Identify recurring issues
   - Performance bottlenecks
   - Stability patterns

4. Actionable Recommendations:
   - Immediate fixes for failures
   - Process improvements
   - Future test enhancements
   - Risk mitigation strategies

Output format:
{
    "execution_id": "unique identifier",
    "generated_at": "ISO timestamp",
    "overall_status": "SUCCESS|PARTIAL_SUCCESS|FAILURE",
    "summary": {
        "success_rate": "percentage",
        "total_tests": number,
        "passed": number,
        "failed": number,
        "execution_time": "duration",
        "environment": "test environment"
    },
    "insights": ["insight1", "insight2"],
    "recommendations": ["recommendation1", "recommendation2"],
    "test_details": [
        {
            "test_name": "test name",
            "status": "passed|failed",
            "duration": "execution time",
            "error_message": "error if failed"
        }
    ]
}

Provide clear, actionable insights that help teams improve their testing strategy."""
