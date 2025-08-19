#!/usr/bin/env python3
"""
StoryForge AI - Phase 6: Production Readiness Assessment
Final assessment to determine if system is ready for production deployment
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

class ProductionReadinessAssessment:
    """Production readiness assessment framework"""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assessment_results = {
            "overall_readiness": {},
            "critical_blockers": [],
            "deployment_risks": [],
            "readiness_checklist": {},
            "recommendations": [],
            "next_steps": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Load previous assessment results
        self._load_previous_assessments()
        
    def _load_previous_assessments(self):
        """Load results from previous phases"""
        try:
            # Load Phase 3 validation results
            phase3_path = os.path.join(self.project_root, "validation", "phase3_validation_report_corrected.json")
            if os.path.exists(phase3_path):
                with open(phase3_path, 'r') as f:
                    self.phase3_results = json.load(f)
            else:
                self.phase3_results = None
                
            # Load Phase 4 verification results
            phase4_path = os.path.join(self.project_root, "validation", "phase4_verification_report.json")
            if os.path.exists(phase4_path):
                with open(phase4_path, 'r') as f:
                    self.phase4_results = json.load(f)
            else:
                self.phase4_results = None
                
            # Load Phase 5 UAT results
            phase5_path = os.path.join(self.project_root, "validation", "phase5_uat_report.json")
            if os.path.exists(phase5_path):
                with open(phase5_path, 'r') as f:
                    self.phase5_results = json.load(f)
            else:
                self.phase5_results = None
                
        except Exception as e:
            print(f"Warning: Could not load previous assessment results: {e}")
            self.phase3_results = None
            self.phase4_results = None
            self.phase5_results = None
    
    def run_production_readiness_assessment(self) -> Dict[str, Any]:
        """Execute complete production readiness assessment"""
        print("=== PHASE 6: PRODUCTION READINESS ASSESSMENT ===\n")
        
        # 1. Analyze Previous Test Results
        print("📊 1. Analyzing Previous Test Results...")
        self._analyze_test_results()
        
        # 2. Evaluate Critical Blockers
        print("\n🚨 2. Evaluating Critical Blockers...")
        self._evaluate_critical_blockers()
        
        # 3. Assess Deployment Risks
        print("\n⚠️ 3. Assessing Deployment Risks...")
        self._assess_deployment_risks()
        
        # 4. Production Readiness Checklist
        print("\n✅ 4. Production Readiness Checklist...")
        self._evaluate_readiness_checklist()
        
        # 5. Generate Final Recommendation
        print("\n🎯 5. Final Production Recommendation...")
        self._generate_final_recommendation()
        
        # 6. Create Deployment Plan
        print("\n🚀 6. Next Steps and Deployment Plan...")
        self._create_deployment_plan()
        
        # Generate comprehensive report
        self._generate_final_report()
        
        return self.assessment_results
    
    def _analyze_test_results(self):
        """Analyze results from all previous testing phases"""
        analysis = {
            "phase3_validation": self._analyze_phase3_results(),
            "phase4_verification": self._analyze_phase4_results(),
            "phase5_uat": self._analyze_phase5_results(),
            "overall_trend": "declining"
        }
        
        # Calculate overall quality trend
        scores = []
        if analysis["phase3_validation"]["success_rate"] is not None:
            scores.append(analysis["phase3_validation"]["success_rate"])
        if analysis["phase4_verification"]["overall_score"] is not None:
            scores.append(analysis["phase4_verification"]["overall_score"])
        if analysis["phase5_uat"]["acceptance_rate"] is not None:
            scores.append(analysis["phase5_uat"]["acceptance_rate"])
        
        if len(scores) >= 2:
            if scores[-1] > scores[0]:
                analysis["overall_trend"] = "improving"
            elif scores[-1] == scores[0]:
                analysis["overall_trend"] = "stable"
            else:
                analysis["overall_trend"] = "declining"
        
        self.assessment_results["test_analysis"] = analysis
        
        # Print summary
        print(f"   Phase 3 Validation: {analysis['phase3_validation']['success_rate']:.1%} success rate")
        print(f"   Phase 4 Verification: {analysis['phase4_verification']['overall_score']:.1f}/100 overall score")
        print(f"   Phase 5 UAT: {analysis['phase5_uat']['acceptance_rate']:.1%} user acceptance")
        print(f"   Quality Trend: {analysis['overall_trend'].upper()}")
    
    def _analyze_phase3_results(self) -> Dict[str, Any]:
        """Analyze Phase 3 validation results"""
        if not self.phase3_results:
            return {"success_rate": None, "major_issues": ["Results not available"]}
        
        overall_metrics = self.phase3_results.get("overall_metrics", {})
        
        return {
            "success_rate": overall_metrics.get("overall_success_rate", 0),
            "total_tests": overall_metrics.get("total_tests", 0),
            "passed_tests": overall_metrics.get("total_passed", 0),
            "status": overall_metrics.get("validation_status", "UNKNOWN"),
            "major_issues": self._extract_phase3_issues()
        }
    
    def _extract_phase3_issues(self) -> List[str]:
        """Extract major issues from Phase 3 results"""
        issues = []
        
        if not self.phase3_results:
            return ["Phase 3 results not available"]
        
        # Check business logic issues
        business_logic = self.phase3_results.get("business_logic", {})
        if business_logic.get("story_generation", {}).get("success_rate", 0) < 0.8:
            issues.append("Story generation reliability below 80%")
        
        # Check system behavior issues
        system_behavior = self.phase3_results.get("system_behavior", {})
        if system_behavior.get("error_handling", {}).get("success_rate", 0) < 0.8:
            issues.append("Error handling needs improvement")
        
        return issues
    
    def _analyze_phase4_results(self) -> Dict[str, Any]:
        """Analyze Phase 4 verification results"""
        if not self.phase4_results:
            return {"overall_score": None, "major_issues": ["Results not available"]}
        
        overall_assessment = self.phase4_results.get("overall_assessment", {})
        
        return {
            "overall_score": overall_assessment.get("overall_score", 0),
            "grade": overall_assessment.get("grade", "F"),
            "production_ready": overall_assessment.get("production_ready", False),
            "critical_issues": overall_assessment.get("critical_issues", []),
            "major_issues": self._extract_phase4_issues()
        }
    
    def _extract_phase4_issues(self) -> List[str]:
        """Extract major issues from Phase 4 results"""
        if not self.phase4_results:
            return ["Phase 4 results not available"]
        
        overall_assessment = self.phase4_results.get("overall_assessment", {})
        critical_issues = overall_assessment.get("critical_issues", [])
        
        # Convert critical issues to more readable format
        readable_issues = []
        for issue in critical_issues:
            if "story generation" in issue.lower():
                readable_issues.append("Story generation quality insufficient")
            elif "character integration" in issue.lower():
                readable_issues.append("Character name integration problems")
            elif "unknown segments" in issue.lower():
                readable_issues.append("'For Unknown' segments still present")
            elif "narrative quality" in issue.lower():
                readable_issues.append("Narrative content quality poor")
            else:
                readable_issues.append(issue)
        
        return readable_issues
    
    def _analyze_phase5_results(self) -> Dict[str, Any]:
        """Analyze Phase 5 UAT results"""
        if not self.phase5_results:
            return {"acceptance_rate": None, "major_issues": ["Results not available"]}
        
        overall_acceptance = self.phase5_results.get("overall_acceptance", {})
        
        return {
            "acceptance_rate": overall_acceptance.get("acceptance_rate", 0),
            "user_acceptance_status": overall_acceptance.get("user_acceptance_status", "UNKNOWN"),
            "ready_for_production": overall_acceptance.get("ready_for_production", False),
            "critical_user_issues": self._extract_phase5_issues(),
            "user_feedback": self._extract_user_feedback()
        }
    
    def _extract_phase5_issues(self) -> List[str]:
        """Extract critical user issues from Phase 5 results"""
        if not self.phase5_results:
            return ["Phase 5 results not available"]
        
        feedback_summary = self.phase5_results.get("user_feedback_summary", {})
        critical_issues = feedback_summary.get("critical_issues", [])
        
        # Convert to readable format
        readable_issues = []
        for issue in critical_issues:
            if "story_generation" in issue:
                readable_issues.append("Users cannot successfully generate stories")
            else:
                readable_issues.append(f"Critical user issue in {issue}")
        
        return readable_issues
    
    def _extract_user_feedback(self) -> List[str]:
        """Extract key user feedback themes"""
        if not self.phase5_results:
            return ["No user feedback available"]
        
        # Extract actual user feedback from test scenarios
        feedback_themes = []
        test_scenarios = self.phase5_results.get("test_scenarios", [])
        
        for scenario in test_scenarios:
            user_feedback = scenario.get("user_feedback", {}).get("overall", "")
            if user_feedback:
                if "unacceptable" in user_feedback.lower():
                    feedback_themes.append(f"User frustrated with {scenario.get('name', 'system')}")
                elif "problems" in user_feedback.lower() or "issues" in user_feedback.lower():
                    feedback_themes.append(f"User reports problems with {scenario.get('name', 'system')}")
        
        return feedback_themes if feedback_themes else ["Mixed user feedback"]
    
    def _evaluate_critical_blockers(self):
        """Evaluate critical blockers preventing production deployment"""
        blockers = []
        
        # Critical blocker 1: User acceptance failure
        if self.phase5_results:
            acceptance_rate = self.phase5_results.get("overall_acceptance", {}).get("acceptance_rate", 0)
            if acceptance_rate < 0.8:
                blockers.append({
                    "type": "USER_ACCEPTANCE",
                    "severity": "CRITICAL",
                    "description": f"User acceptance rate only {acceptance_rate:.1%} (minimum: 80%)",
                    "impact": "Users will not adopt the system in production",
                    "resolution_required": True
                })
        
        # Critical blocker 2: Quality gates failure
        if self.phase4_results:
            quality_gates = self.phase4_results.get("quality_gates", {})
            overall_pass = quality_gates.get("overall_pass", False)
            if not overall_pass:
                critical_failures = len(quality_gates.get("critical_failures", []))
                blockers.append({
                    "type": "QUALITY_GATES",
                    "severity": "CRITICAL",
                    "description": f"{critical_failures} critical quality gates failed",
                    "impact": "System does not meet minimum quality standards",
                    "resolution_required": True
                })
        
        # Critical blocker 3: Core functionality issues
        if self.phase3_results:
            business_logic = self.phase3_results.get("business_logic", {})
            story_gen_success = business_logic.get("story_generation", {}).get("success_rate", 0)
            if story_gen_success < 0.8:
                blockers.append({
                    "type": "CORE_FUNCTIONALITY",
                    "severity": "CRITICAL", 
                    "description": f"Story generation only {story_gen_success:.1%} reliable",
                    "impact": "Core feature does not work reliably for users",
                    "resolution_required": True
                })
        
        # Critical blocker 4: Character integration issues
        character_issues_found = False
        if self.phase4_results:
            critical_issues = self.phase4_results.get("overall_assessment", {}).get("critical_issues", [])
            for issue in critical_issues:
                if "character" in issue.lower() or "unknown" in issue.lower():
                    character_issues_found = True
                    break
        
        if character_issues_found:
            blockers.append({
                "type": "CHARACTER_INTEGRATION",
                "severity": "CRITICAL",
                "description": "Character names not properly integrated, 'For Unknown' segments present",
                "impact": "Stories contain placeholder text instead of character names",
                "resolution_required": True
            })
        
        self.assessment_results["critical_blockers"] = blockers
        
        # Print critical blockers
        if blockers:
            print(f"   🚨 {len(blockers)} CRITICAL BLOCKERS IDENTIFIED:")
            for i, blocker in enumerate(blockers, 1):
                print(f"      {i}. {blocker['type']}: {blocker['description']}")
        else:
            print("   ✅ No critical blockers identified")
    
    def _assess_deployment_risks(self):
        """Assess risks associated with production deployment"""
        risks = []
        
        # High risk: Performance issues
        if self.phase4_results:
            performance = self.phase4_results.get("performance_verification", {})
            if performance.get("response_time", {}).get("score", 0) < 60:  # Less than 60/100
                risks.append({
                    "type": "PERFORMANCE",
                    "probability": "HIGH",
                    "impact": "MEDIUM",
                    "description": "Response times may be too slow for production use",
                    "mitigation": "Optimize performance before deployment"
                })
        
        # Medium risk: Security vulnerabilities
        if self.phase4_results:
            security = self.phase4_results.get("security_verification", {})
            security_score = sum(result.get("score", 0) for result in security.values()) / len(security) if security else 0
            if security_score < 80:
                risks.append({
                    "type": "SECURITY",
                    "probability": "MEDIUM",
                    "impact": "HIGH",
                    "description": "Security measures may be insufficient for production",
                    "mitigation": "Conduct security audit and implement additional measures"
                })
        
        # High risk: User dissatisfaction
        if self.phase5_results:
            user_satisfaction = self.phase5_results.get("user_feedback_summary", {}).get("user_satisfaction_levels", [])
            unsatisfied_count = sum(1 for level in user_satisfaction if "unsatisfied" in level)
            if unsatisfied_count > 0:
                risks.append({
                    "type": "USER_SATISFACTION",
                    "probability": "HIGH",
                    "impact": "HIGH",
                    "description": "Users report significant dissatisfaction with system",
                    "mitigation": "Address user concerns before production deployment"
                })
        
        # Medium risk: Reliability issues
        if self.phase4_results:
            reliability = self.phase4_results.get("reliability_verification", {})
            reliability_score = sum(result.get("score", 0) for result in reliability.values()) / len(reliability) if reliability else 0
            if reliability_score < 75:
                risks.append({
                    "type": "RELIABILITY",
                    "probability": "MEDIUM",
                    "impact": "MEDIUM",
                    "description": "System reliability may not meet production standards",
                    "mitigation": "Improve error handling and system stability"
                })
        
        self.assessment_results["deployment_risks"] = risks
        
        # Print deployment risks
        if risks:
            print(f"   ⚠️ {len(risks)} DEPLOYMENT RISKS IDENTIFIED:")
            for i, risk in enumerate(risks, 1):
                print(f"      {i}. {risk['type']} ({risk['probability']} probability, {risk['impact']} impact)")
                print(f"         {risk['description']}")
        else:
            print("   ✅ No significant deployment risks identified")
    
    def _evaluate_readiness_checklist(self):
        """Evaluate production readiness checklist"""
        checklist = {
            "functionality": self._check_functionality(),
            "performance": self._check_performance(), 
            "security": self._check_security(),
            "reliability": self._check_reliability(),
            "user_acceptance": self._check_user_acceptance(),
            "documentation": self._check_documentation(),
            "deployment": self._check_deployment_readiness()
        }
        
        self.assessment_results["readiness_checklist"] = checklist
        
        # Calculate overall readiness score
        scores = [item["score"] for item in checklist.values()]
        overall_score = sum(scores) / len(scores) if scores else 0
        
        passed_items = sum(1 for item in checklist.values() if item["status"] == "PASS")
        total_items = len(checklist)
        
        print(f"   📋 Production Readiness Checklist: {passed_items}/{total_items} items passed")
        print(f"   📊 Overall Readiness Score: {overall_score:.1f}/100")
        
        for category, result in checklist.items():
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            print(f"      {status_icon} {category.title()}: {result['score']:.1f}/100 ({result['status']})")
    
    def _check_functionality(self) -> Dict[str, Any]:
        """Check functional requirements readiness"""
        if not self.phase4_results:
            return {"score": 0, "status": "FAIL", "details": "No verification results available"}
        
        functional = self.phase4_results.get("functional_verification", {})
        if not functional:
            return {"score": 0, "status": "FAIL", "details": "No functional verification data"}
        
        # Calculate average score from functional tests
        scores = []
        for test_result in functional.values():
            if isinstance(test_result, dict) and "score" in test_result:
                scores.append(test_result["score"])
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        status = "PASS" if avg_score >= 80 else "WARN" if avg_score >= 60 else "FAIL"
        
        return {
            "score": avg_score,
            "status": status,
            "details": f"Average functional test score: {avg_score:.1f}/100"
        }
    
    def _check_performance(self) -> Dict[str, Any]:
        """Check performance requirements readiness"""
        if not self.phase4_results:
            return {"score": 0, "status": "FAIL", "details": "No performance verification data"}
        
        performance = self.phase4_results.get("performance_verification", {})
        if not performance:
            return {"score": 0, "status": "FAIL", "details": "No performance verification data"}
        
        scores = []
        for test_result in performance.values():
            if isinstance(test_result, dict) and "score" in test_result:
                scores.append(test_result["score"])
        
        avg_score = sum(scores) / len(scores) if scores else 0
        status = "PASS" if avg_score >= 70 else "WARN" if avg_score >= 50 else "FAIL"
        
        return {
            "score": avg_score,
            "status": status,
            "details": f"Average performance score: {avg_score:.1f}/100"
        }
    
    def _check_security(self) -> Dict[str, Any]:
        """Check security requirements readiness"""
        if not self.phase4_results:
            return {"score": 0, "status": "FAIL", "details": "No security verification data"}
        
        security = self.phase4_results.get("security_verification", {})
        if not security:
            return {"score": 0, "status": "FAIL", "details": "No security verification data"}
        
        scores = []
        for test_result in security.values():
            if isinstance(test_result, dict) and "score" in test_result:
                scores.append(test_result["score"])
        
        avg_score = sum(scores) / len(scores) if scores else 0
        status = "PASS" if avg_score >= 80 else "WARN" if avg_score >= 60 else "FAIL"
        
        return {
            "score": avg_score,
            "status": status,
            "details": f"Average security score: {avg_score:.1f}/100"
        }
    
    def _check_reliability(self) -> Dict[str, Any]:
        """Check reliability requirements readiness"""
        if not self.phase4_results:
            return {"score": 0, "status": "FAIL", "details": "No reliability verification data"}
        
        reliability = self.phase4_results.get("reliability_verification", {})
        if not reliability:
            return {"score": 0, "status": "FAIL", "details": "No reliability verification data"}
        
        scores = []
        for test_result in reliability.values():
            if isinstance(test_result, dict) and "score" in test_result:
                scores.append(test_result["score"])
        
        avg_score = sum(scores) / len(scores) if scores else 0
        status = "PASS" if avg_score >= 75 else "WARN" if avg_score >= 60 else "FAIL"
        
        return {
            "score": avg_score,
            "status": status,
            "details": f"Average reliability score: {avg_score:.1f}/100"
        }
    
    def _check_user_acceptance(self) -> Dict[str, Any]:
        """Check user acceptance readiness"""
        if not self.phase5_results:
            return {"score": 0, "status": "FAIL", "details": "No user acceptance testing data"}
        
        acceptance_rate = self.phase5_results.get("overall_acceptance", {}).get("acceptance_rate", 0)
        score = acceptance_rate * 100
        
        status = "PASS" if score >= 80 else "WARN" if score >= 60 else "FAIL"
        
        return {
            "score": score,
            "status": status,
            "details": f"User acceptance rate: {acceptance_rate:.1%}"
        }
    
    def _check_documentation(self) -> Dict[str, Any]:
        """Check documentation readiness"""
        # Basic documentation check based on file existence
        doc_files = ["README.md", "TESTING.md"]
        existing_docs = []
        
        for doc_file in doc_files:
            if os.path.exists(os.path.join(self.project_root, doc_file)):
                existing_docs.append(doc_file)
        
        doc_score = (len(existing_docs) / len(doc_files)) * 100
        status = "PASS" if doc_score >= 80 else "WARN" if doc_score >= 50 else "FAIL"
        
        return {
            "score": doc_score,
            "status": status,
            "details": f"Documentation coverage: {len(existing_docs)}/{len(doc_files)} files"
        }
    
    def _check_deployment_readiness(self) -> Dict[str, Any]:
        """Check deployment readiness"""
        # Check for deployment-related files and configurations
        deployment_items = []
        
        # Check for basic deployment files
        deployment_files = ["requirements.txt", "config.yaml", "api_server.py"]
        for file in deployment_files:
            if os.path.exists(os.path.join(self.project_root, file)):
                deployment_items.append(file)
        
        # Check for validation reports
        validation_reports = [
            "validation/phase3_validation_report_corrected.json",
            "validation/phase4_verification_report.json", 
            "validation/phase5_uat_report.json"
        ]
        
        for report in validation_reports:
            if os.path.exists(os.path.join(self.project_root, report)):
                deployment_items.append(report)
        
        total_items = len(deployment_files) + len(validation_reports)
        deployment_score = (len(deployment_items) / total_items) * 100
        
        status = "PASS" if deployment_score >= 80 else "WARN" if deployment_score >= 60 else "FAIL"
        
        return {
            "score": deployment_score,
            "status": status,
            "details": f"Deployment readiness: {len(deployment_items)}/{total_items} items ready"
        }
    
    def _generate_final_recommendation(self):
        """Generate final production deployment recommendation"""
        # Analyze critical blockers
        critical_blockers = self.assessment_results.get("critical_blockers", [])
        has_critical_blockers = len(critical_blockers) > 0
        
        # Analyze readiness checklist
        readiness_checklist = self.assessment_results.get("readiness_checklist", {})
        passed_checks = sum(1 for item in readiness_checklist.values() if item.get("status") == "PASS")
        total_checks = len(readiness_checklist)
        readiness_rate = passed_checks / total_checks if total_checks > 0 else 0
        
        # Analyze user acceptance
        user_acceptance_ready = False
        if self.phase5_results:
            user_acceptance_ready = self.phase5_results.get("overall_acceptance", {}).get("ready_for_production", False)
        
        # Generate recommendation
        if has_critical_blockers:
            recommendation = "DO NOT DEPLOY"
            confidence = "HIGH"
            reasoning = f"System has {len(critical_blockers)} critical blockers that must be resolved before production deployment"
        elif readiness_rate < 0.6:
            recommendation = "DO NOT DEPLOY"
            confidence = "HIGH"
            reasoning = f"System fails {total_checks - passed_checks} of {total_checks} readiness checks"
        elif not user_acceptance_ready:
            recommendation = "DO NOT DEPLOY"
            confidence = "HIGH"
            reasoning = "User acceptance testing failed - users are not satisfied with current system"
        elif readiness_rate < 0.8:
            recommendation = "DEPLOY WITH CAUTION"
            confidence = "MEDIUM"
            reasoning = f"System passes {passed_checks}/{total_checks} readiness checks but has some concerns"
        else:
            recommendation = "READY TO DEPLOY"
            confidence = "HIGH"
            reasoning = "System passes all critical readiness requirements"
        
        final_recommendation = {
            "recommendation": recommendation,
            "confidence": confidence,
            "reasoning": reasoning,
            "readiness_score": readiness_rate * 100,
            "critical_blockers_count": len(critical_blockers),
            "readiness_checks_passed": f"{passed_checks}/{total_checks}"
        }
        
        self.assessment_results["overall_readiness"] = final_recommendation
        
        # Print final recommendation
        print(f"   🎯 FINAL RECOMMENDATION: {recommendation}")
        print(f"   📊 Confidence Level: {confidence}")
        print(f"   📈 Overall Readiness Score: {readiness_rate * 100:.1f}/100")
        print(f"   🔍 Reasoning: {reasoning}")
    
    def _create_deployment_plan(self):
        """Create next steps and deployment plan"""
        next_steps = []
        
        # Steps based on critical blockers
        critical_blockers = self.assessment_results.get("critical_blockers", [])
        for blocker in critical_blockers:
            if blocker["type"] == "USER_ACCEPTANCE":
                next_steps.append({
                    "priority": "CRITICAL",
                    "action": "Address user experience issues",
                    "description": "Fix story generation reliability and character name integration",
                    "estimated_effort": "2-3 weeks",
                    "success_criteria": "User acceptance rate > 80%"
                })
            elif blocker["type"] == "QUALITY_GATES":
                next_steps.append({
                    "priority": "CRITICAL", 
                    "action": "Resolve quality gate failures",
                    "description": "Fix character integration and eliminate 'For Unknown' segments",
                    "estimated_effort": "1-2 weeks",
                    "success_criteria": "All critical quality gates pass"
                })
            elif blocker["type"] == "CORE_FUNCTIONALITY":
                next_steps.append({
                    "priority": "CRITICAL",
                    "action": "Fix core story generation",
                    "description": "Improve story generation reliability and content quality",
                    "estimated_effort": "2-4 weeks", 
                    "success_criteria": "Story generation success rate > 80%"
                })
            elif blocker["type"] == "CHARACTER_INTEGRATION":
                next_steps.append({
                    "priority": "CRITICAL",
                    "action": "Complete character name integration",
                    "description": "Ensure character names appear correctly in all generated content",
                    "estimated_effort": "1 week",
                    "success_criteria": "No 'For Unknown' segments in output"
                })
        
        # Additional improvement steps
        if not critical_blockers:
            next_steps.append({
                "priority": "HIGH",
                "action": "Performance optimization",
                "description": "Improve response times and system efficiency",
                "estimated_effort": "1-2 weeks",
                "success_criteria": "Average response time < 10 seconds"
            })
        
        # Always include validation step
        next_steps.append({
            "priority": "HIGH" if critical_blockers else "MEDIUM",
            "action": "Re-run validation suite",
            "description": "Execute full validation suite after implementing fixes",
            "estimated_effort": "2-3 days",
            "success_criteria": "All validation phases pass with > 80% success rate"
        })
        
        # Deployment preparation
        if not critical_blockers:
            next_steps.append({
                "priority": "MEDIUM",
                "action": "Prepare production deployment",
                "description": "Set up production environment and deployment procedures",
                "estimated_effort": "3-5 days",
                "success_criteria": "Production environment ready and tested"
            })
        
        self.assessment_results["next_steps"] = next_steps
        
        # Print next steps
        print(f"   📋 NEXT STEPS ({len(next_steps)} actions required):")
        for i, step in enumerate(next_steps, 1):
            print(f"      {i}. {step['priority']}: {step['action']}")
            print(f"         Description: {step['description']}")
            print(f"         Estimated Effort: {step['estimated_effort']}")
            print(f"         Success Criteria: {step['success_criteria']}")
    
    def _generate_final_report(self):
        """Generate comprehensive final assessment report"""
        report_path = os.path.join(self.project_root, "validation", "phase6_production_readiness_final_report.json")
        
        # Add executive summary
        executive_summary = {
            "assessment_date": datetime.now().isoformat(),
            "overall_recommendation": self.assessment_results["overall_readiness"]["recommendation"],
            "readiness_score": self.assessment_results["overall_readiness"]["readiness_score"],
            "critical_blockers": len(self.assessment_results["critical_blockers"]),
            "key_findings": self._generate_key_findings(),
            "business_impact": self._assess_business_impact()
        }
        
        self.assessment_results["executive_summary"] = executive_summary
        
        # Save comprehensive report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.assessment_results, f, indent=2)
        
        print(f"\n=== PHASE 6 PRODUCTION READINESS SUMMARY ===")
        print(f"🎯 Final Recommendation: {executive_summary['overall_recommendation']}")
        print(f"📊 Overall Readiness Score: {executive_summary['readiness_score']:.1f}/100")
        print(f"🚨 Critical Blockers: {executive_summary['critical_blockers']}")
        print(f"📋 Next Steps Required: {len(self.assessment_results['next_steps'])}")
        
        if executive_summary["key_findings"]:
            print(f"🔍 Key Findings:")
            for finding in executive_summary["key_findings"][:3]:
                print(f"   • {finding}")
        
        print(f"\n📄 Comprehensive assessment report saved to: {report_path}")
    
    def _generate_key_findings(self) -> List[str]:
        """Generate key findings from the assessment"""
        findings = []
        
        # User acceptance finding
        if self.phase5_results:
            acceptance_rate = self.phase5_results.get("overall_acceptance", {}).get("acceptance_rate", 0)
            if acceptance_rate == 0:
                findings.append("Zero user acceptance - all UAT scenarios failed")
            elif acceptance_rate < 0.5:
                findings.append(f"Very low user acceptance rate ({acceptance_rate:.1%})")
        
        # Character integration finding
        critical_blockers = self.assessment_results.get("critical_blockers", [])
        for blocker in critical_blockers:
            if blocker["type"] == "CHARACTER_INTEGRATION":
                findings.append("Character names not properly integrated - placeholder text remains")
                break
        
        # Story generation finding
        for blocker in critical_blockers:
            if blocker["type"] == "CORE_FUNCTIONALITY":
                findings.append("Core story generation functionality unreliable")
                break
        
        # Performance finding
        if self.phase4_results:
            performance = self.phase4_results.get("performance_verification", {})
            if performance.get("response_time", {}).get("score", 0) < 50:
                findings.append("Performance issues may affect user experience")
        
        # Quality trend finding
        test_analysis = self.assessment_results.get("test_analysis", {})
        if test_analysis.get("overall_trend") == "declining":
            findings.append("Quality metrics show declining trend across test phases")
        
        return findings
    
    def _assess_business_impact(self) -> str:
        """Assess business impact of current system state"""
        critical_blockers = len(self.assessment_results.get("critical_blockers", []))
        
        if critical_blockers >= 3:
            return "HIGH RISK - System not viable for production use, major user experience issues"
        elif critical_blockers >= 1:
            return "MEDIUM RISK - System has critical issues that would impact user adoption"
        else:
            return "LOW RISK - System meets basic requirements but may need optimization"


def main():
    """Run Phase 6 Production Readiness Assessment"""
    try:
        print("StoryForge AI - Phase 6: Production Readiness Assessment")
        print("=" * 60)
        print("Final assessment to determine production deployment readiness")
        print()
        
        assessment = ProductionReadinessAssessment()
        results = assessment.run_production_readiness_assessment()
        
        return results
        
    except Exception as e:
        print(f"❌ Production readiness assessment error: {str(e)}")
        return None


if __name__ == "__main__":
    main()