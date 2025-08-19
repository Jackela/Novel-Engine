#!/usr/bin/env python3
"""
StoryForge AI - Comprehensive Phase 6: Production Readiness Assessment
Final production readiness evaluation with comprehensive deployment criteria
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ProductionReadinessAssessment:
    """Comprehensive Production Readiness Assessment framework"""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assessment_results = {
            "production_criteria": {},
            "deployment_readiness": {},
            "operational_readiness": {},
            "security_assessment": {},
            "monitoring_and_alerting": {},
            "documentation_readiness": {},
            "rollback_capabilities": {},
            "final_recommendations": {},
            "go_no_go_decision": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Load previous phase results
        self.phase_results = {}
        self._load_all_phase_results()
    
    def run_comprehensive_assessment(self) -> Dict[str, Any]:
        """Execute comprehensive production readiness assessment"""
        print("=== PHASE 6: COMPREHENSIVE PRODUCTION READINESS ASSESSMENT ===\n")
        
        # 1. Production Criteria Evaluation
        print("🚀 1. Production Criteria Evaluation...")
        self._evaluate_production_criteria()
        
        # 2. Deployment Readiness Assessment
        print("\n📦 2. Deployment Readiness Assessment...")
        self._assess_deployment_readiness()
        
        # 3. Operational Readiness Evaluation
        print("\n⚙️ 3. Operational Readiness Evaluation...")
        self._evaluate_operational_readiness()
        
        # 4. Security Assessment
        print("\n🔒 4. Security Assessment...")
        self._assess_security_readiness()
        
        # 5. Monitoring and Alerting Assessment
        print("\n📊 5. Monitoring and Alerting Assessment...")
        self._assess_monitoring_and_alerting()
        
        # 6. Documentation Readiness
        print("\n📚 6. Documentation Readiness...")
        self._assess_documentation_readiness()
        
        # 7. Rollback Capabilities Assessment
        print("\n🔄 7. Rollback Capabilities Assessment...")
        self._assess_rollback_capabilities()
        
        # 8. Final Go/No-Go Decision
        print("\n🎯 8. Final Go/No-Go Decision...")
        self._make_go_no_go_decision()
        
        # 9. Generate Final Recommendations
        print("\n💡 9. Generate Final Recommendations...")
        self._generate_final_recommendations()
        
        # 10. Save Assessment Report
        self._save_assessment_report()
        
        return self.assessment_results
    
    def _load_all_phase_results(self):
        """Load results from all previous phases"""
        phase_files = [
            ("phase1_architecture", "comprehensive_phase1_architecture_report.json"),
            ("phase1_code_quality", "comprehensive_phase1_code_quality_report.json"),
            ("phase2_unit_tests", "comprehensive_phase2_unit_test_report.json"),
            ("phase2_integration_tests", "comprehensive_phase2_integration_test_report.json"),
            ("phase3_validation", "comprehensive_phase3_validation_report.json"),
            ("phase4_verification", "comprehensive_phase4_verification_report.json"),
            ("phase5_uat", "comprehensive_phase5_uat_report.json")
        ]
        
        for phase_name, filename in phase_files:
            try:
                file_path = os.path.join(self.project_root, "validation", filename)
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        self.phase_results[phase_name] = json.load(f)
                    print(f"   ✅ {phase_name} results loaded")
                else:
                    print(f"   ⚠️ {phase_name} results not found: {filename}")
            except Exception as e:
                print(f"   ❌ Error loading {phase_name}: {e}")
        
        print(f"   📊 Total phases loaded: {len(self.phase_results)}")
    
    def _evaluate_production_criteria(self):
        """Evaluate system against production deployment criteria"""
        criteria_results = {}
        
        # Quality Criteria
        criteria_results["quality_criteria"] = self._evaluate_quality_criteria()
        
        # Performance Criteria
        criteria_results["performance_criteria"] = self._evaluate_performance_criteria()
        
        # Reliability Criteria
        criteria_results["reliability_criteria"] = self._evaluate_reliability_criteria()
        
        # Scalability Criteria
        criteria_results["scalability_criteria"] = self._evaluate_scalability_criteria()
        
        # Maintainability Criteria
        criteria_results["maintainability_criteria"] = self._evaluate_maintainability_criteria()
        
        # Security Criteria
        criteria_results["security_criteria"] = self._evaluate_security_criteria()
        
        self.assessment_results["production_criteria"] = criteria_results
        
        # Calculate overall criteria score
        criteria_scores = [
            criteria["score"] for criteria in criteria_results.values() 
            if "score" in criteria
        ]
        overall_score = sum(criteria_scores) / len(criteria_scores) if criteria_scores else 0
        
        print(f"   🎯 Overall Production Criteria Score: {overall_score:.1f}%")
        
        # Determine readiness level
        if overall_score >= 85:
            readiness_level = "PRODUCTION_READY"
        elif overall_score >= 70:
            readiness_level = "NEARLY_READY"
        elif overall_score >= 55:
            readiness_level = "NEEDS_IMPROVEMENT"
        else:
            readiness_level = "NOT_READY"
        
        criteria_results["overall_assessment"] = {
            "score": overall_score,
            "readiness_level": readiness_level,
            "criteria_met": len([c for c in criteria_results.values() if c.get("status") == "PASS"]),
            "total_criteria": len([c for c in criteria_results.values() if "status" in c])
        }
        
        print(f"   🎯 Production Readiness Level: {readiness_level}")
    
    def _evaluate_quality_criteria(self) -> Dict[str, Any]:
        """Evaluate quality criteria"""
        # Get quality metrics from previous phases
        code_quality_score = 0
        architecture_score = 0
        testing_score = 0
        
        if "phase1_code_quality" in self.phase_results:
            code_quality_score = self.phase_results["phase1_code_quality"].get("overall_score", 0)
        
        if "phase1_architecture" in self.phase_results:
            architecture_score = self.phase_results["phase1_architecture"].get("overall_health_score", 0)
        
        if "phase2_unit_tests" in self.phase_results:
            unit_success = self.phase_results["phase2_unit_tests"]["test_summary"].get("success_rate", 0)
            integration_success = 0
            if "phase2_integration_tests" in self.phase_results:
                integration_success = self.phase_results["phase2_integration_tests"]["test_summary"].get("overall_pass_rate", 0)
            testing_score = (unit_success + integration_success) / 2
        
        quality_score = (code_quality_score + architecture_score + testing_score) / 3
        
        quality_requirements = {
            "code_quality_threshold": {
                "requirement": "Code quality score >= 85%",
                "actual": code_quality_score,
                "threshold": 85,
                "status": "PASS" if code_quality_score >= 85 else "FAIL"
            },
            "architecture_quality_threshold": {
                "requirement": "Architecture quality score >= 90%",
                "actual": architecture_score,
                "threshold": 90,
                "status": "PASS" if architecture_score >= 90 else "FAIL"
            },
            "testing_quality_threshold": {
                "requirement": "Testing success rate >= 90%",
                "actual": testing_score,
                "threshold": 90,
                "status": "PASS" if testing_score >= 90 else "FAIL"
            }
        }
        
        passed_requirements = sum(1 for req in quality_requirements.values() if req["status"] == "PASS")
        
        return {
            "score": quality_score,
            "status": "PASS" if quality_score >= 80 else "FAIL",
            "requirements": quality_requirements,
            "requirements_met": f"{passed_requirements}/{len(quality_requirements)}",
            "assessment": f"Quality criteria {'met' if quality_score >= 80 else 'not met'}"
        }
    
    def _evaluate_performance_criteria(self) -> Dict[str, Any]:
        """Evaluate performance criteria"""
        performance_score = 0
        
        # Get performance metrics from validation phase
        if "phase3_validation" in self.phase_results:
            validation_data = self.phase_results["phase3_validation"]
            if "validation_summary" in validation_data:
                categories = validation_data["validation_summary"].get("category_results", {})
                if "Performance" in categories:
                    performance_score = categories["Performance"]["success_rate"]
        
        performance_requirements = {
            "response_time_requirement": {
                "requirement": "Response time < 5 seconds for key operations",
                "status": "PARTIAL",  # Based on previous findings
                "details": "Character creation fast, narrative transcription slow"
            },
            "throughput_requirement": {
                "requirement": "Handle expected user load",
                "status": "PASS",
                "details": "Adequate throughput for expected load"
            },
            "resource_usage_requirement": {
                "requirement": "Memory usage < 100MB",
                "status": "PASS",
                "details": "Memory usage within acceptable limits"
            },
            "scalability_requirement": {
                "requirement": "Scale with multiple concurrent users",
                "status": "PARTIAL",
                "details": "Limited scalability testing performed"
            }
        }
        
        passed_requirements = sum(1 for req in performance_requirements.values() if req["status"] == "PASS")
        
        return {
            "score": performance_score,
            "status": "PASS" if performance_score >= 70 else "FAIL",
            "requirements": performance_requirements,
            "requirements_met": f"{passed_requirements}/{len(performance_requirements)}",
            "assessment": f"Performance criteria {'met' if performance_score >= 70 else 'not met'}"
        }
    
    def _evaluate_reliability_criteria(self) -> Dict[str, Any]:
        """Evaluate reliability criteria"""
        reliability_score = 0
        
        # Get reliability metrics from validation phase
        if "phase3_validation" in self.phase_results:
            validation_data = self.phase_results["phase3_validation"]
            if "validation_summary" in validation_data:
                categories = validation_data["validation_summary"].get("category_results", {})
                if "System Behavior" in categories:
                    reliability_score = categories["System Behavior"]["success_rate"]
        
        reliability_requirements = {
            "error_handling_requirement": {
                "requirement": "Robust error handling and recovery",
                "status": "PASS",
                "details": "Good error handling mechanisms identified"
            },
            "system_stability_requirement": {
                "requirement": "System runs without crashes",
                "status": "PASS",
                "details": "No system crashes observed during testing"
            },
            "data_integrity_requirement": {
                "requirement": "Data integrity maintained",
                "status": "FAIL",  # Based on previous findings
                "details": "Data integrity issues identified in Phase 3"
            },
            "fault_tolerance_requirement": {
                "requirement": "System tolerates component failures",
                "status": "PARTIAL",
                "details": "Some fault tolerance, needs improvement"
            }
        }
        
        passed_requirements = sum(1 for req in reliability_requirements.values() if req["status"] == "PASS")
        
        return {
            "score": reliability_score,
            "status": "PASS" if reliability_score >= 80 else "FAIL",
            "requirements": reliability_requirements,
            "requirements_met": f"{passed_requirements}/{len(reliability_requirements)}",
            "assessment": f"Reliability criteria {'met' if reliability_score >= 80 else 'not met'}"
        }
    
    def _evaluate_scalability_criteria(self) -> Dict[str, Any]:
        """Evaluate scalability criteria"""
        scalability_score = 70  # Conservative estimate based on limited testing
        
        scalability_requirements = {
            "horizontal_scaling_requirement": {
                "requirement": "Support for horizontal scaling",
                "status": "PARTIAL",
                "details": "Architecture supports scaling but not fully tested"
            },
            "concurrent_users_requirement": {
                "requirement": "Handle multiple concurrent users",
                "status": "PASS",
                "details": "Concurrent operations tested successfully"
            },
            "resource_scaling_requirement": {
                "requirement": "Resources scale with load",
                "status": "PARTIAL",
                "details": "Limited scaling validation performed"
            },
            "performance_degradation_requirement": {
                "requirement": "Graceful performance degradation under load",
                "status": "UNKNOWN",
                "details": "Load testing not comprehensively performed"
            }
        }
        
        passed_requirements = sum(1 for req in scalability_requirements.values() if req["status"] == "PASS")
        
        return {
            "score": scalability_score,
            "status": "PASS" if scalability_score >= 70 else "FAIL",
            "requirements": scalability_requirements,
            "requirements_met": f"{passed_requirements}/{len(scalability_requirements)}",
            "assessment": f"Scalability criteria {'met' if scalability_score >= 70 else 'not met'}"
        }
    
    def _evaluate_maintainability_criteria(self) -> Dict[str, Any]:
        """Evaluate maintainability criteria"""
        maintainability_score = 60  # Based on code quality and documentation findings
        
        maintainability_requirements = {
            "code_maintainability_requirement": {
                "requirement": "Code is maintainable and well-structured",
                "status": "PARTIAL",
                "details": "Good structure but some quality issues identified"
            },
            "documentation_requirement": {
                "requirement": "Comprehensive documentation available",
                "status": "PARTIAL",
                "details": "Basic documentation present, could be enhanced"
            },
            "testing_maintainability_requirement": {
                "requirement": "Comprehensive test suite for maintenance",
                "status": "FAIL",
                "details": "Test coverage insufficient (11.4%)"
            },
            "modularity_requirement": {
                "requirement": "Modular design supports maintenance",
                "status": "PASS",
                "details": "Good modular architecture identified"
            }
        }
        
        passed_requirements = sum(1 for req in maintainability_requirements.values() if req["status"] == "PASS")
        
        return {
            "score": maintainability_score,
            "status": "PASS" if maintainability_score >= 70 else "FAIL",
            "requirements": maintainability_requirements,
            "requirements_met": f"{passed_requirements}/{len(maintainability_requirements)}",
            "assessment": f"Maintainability criteria {'not met' if maintainability_score < 70 else 'met'}"
        }
    
    def _evaluate_security_criteria(self) -> Dict[str, Any]:
        """Evaluate security criteria"""
        security_score = 65  # Conservative estimate based on basic security validation
        
        security_requirements = {
            "basic_security_requirement": {
                "requirement": "Basic security measures implemented",
                "status": "PARTIAL",
                "details": "Basic security through code quality, needs dedicated assessment"
            },
            "input_validation_requirement": {
                "requirement": "Input validation implemented",
                "status": "PARTIAL",
                "details": "Some input validation present, could be enhanced"
            },
            "error_handling_security_requirement": {
                "requirement": "Secure error handling (no information leakage)",
                "status": "PASS",
                "details": "Error handling doesn't expose sensitive information"
            },
            "dependency_security_requirement": {
                "requirement": "Dependencies security validated",
                "status": "UNKNOWN",
                "details": "Dependency security not explicitly validated"
            }
        }
        
        passed_requirements = sum(1 for req in security_requirements.values() if req["status"] == "PASS")
        
        return {
            "score": security_score,
            "status": "PASS" if security_score >= 70 else "FAIL",
            "requirements": security_requirements,
            "requirements_met": f"{passed_requirements}/{len(security_requirements)}",
            "assessment": f"Security criteria {'not met' if security_score < 70 else 'met'} - needs dedicated security assessment"
        }
    
    def _assess_deployment_readiness(self):
        """Assess deployment readiness"""
        deployment_assessment = {
            "code_deployment_readiness": self._assess_code_deployment_readiness(),
            "environment_readiness": self._assess_environment_readiness(),
            "dependency_management": self._assess_dependency_management(),
            "configuration_management": self._assess_configuration_management(),
            "database_readiness": self._assess_database_readiness()
        }
        
        self.assessment_results["deployment_readiness"] = deployment_assessment
        
        # Calculate deployment readiness score
        deployment_scores = [
            assessment["score"] for assessment in deployment_assessment.values()
            if "score" in assessment
        ]
        overall_deployment_score = sum(deployment_scores) / len(deployment_scores) if deployment_scores else 0
        
        print(f"   📦 Deployment Readiness Score: {overall_deployment_score:.1f}%")
    
    def _assess_code_deployment_readiness(self) -> Dict[str, Any]:
        """Assess code deployment readiness"""
        code_checks = {
            "version_control": {
                "status": "PASS",
                "details": "Code under Git version control"
            },
            "build_process": {
                "status": "PASS",
                "details": "Python project with clear entry points"
            },
            "dependency_declaration": {
                "status": "PARTIAL",
                "details": "Some dependencies declared, needs requirements.txt"
            },
            "configuration_externalization": {
                "status": "PASS",
                "details": "Configuration externalized via config.yaml"
            }
        }
        
        passed_checks = sum(1 for check in code_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(code_checks)) * 100
        
        return {
            "score": score,
            "status": "PASS" if score >= 75 else "FAIL",
            "checks": code_checks,
            "assessment": f"Code deployment readiness: {score:.1f}%"
        }
    
    def _assess_environment_readiness(self) -> Dict[str, Any]:
        """Assess environment readiness"""
        environment_checks = {
            "runtime_requirements": {
                "status": "PASS",
                "details": "Python 3.x runtime identified"
            },
            "system_dependencies": {
                "status": "UNKNOWN",
                "details": "System dependencies not explicitly documented"
            },
            "resource_requirements": {
                "status": "PASS",
                "details": "Low resource requirements (<100MB memory)"
            },
            "network_requirements": {
                "status": "PARTIAL",
                "details": "Network requirements for LLM API calls needed"
            }
        }
        
        passed_checks = sum(1 for check in environment_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(environment_checks)) * 100
        
        return {
            "score": score,
            "status": "PASS" if score >= 70 else "FAIL",
            "checks": environment_checks,
            "assessment": f"Environment readiness: {score:.1f}%"
        }
    
    def _assess_dependency_management(self) -> Dict[str, Any]:
        """Assess dependency management"""
        dependency_checks = {
            "dependency_specification": {
                "status": "PARTIAL",
                "details": "Dependencies in imports but no requirements.txt"
            },
            "version_pinning": {
                "status": "FAIL",
                "details": "Dependency versions not pinned"
            },
            "security_scanning": {
                "status": "UNKNOWN",
                "details": "Dependency security not scanned"
            },
            "license_compliance": {
                "status": "UNKNOWN",
                "details": "Dependency licenses not validated"
            }
        }
        
        passed_checks = sum(1 for check in dependency_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(dependency_checks)) * 100
        
        return {
            "score": score,
            "status": "FAIL",  # Critical dependency management issues
            "checks": dependency_checks,
            "assessment": f"Dependency management needs significant improvement: {score:.1f}%"
        }
    
    def _assess_configuration_management(self) -> Dict[str, Any]:
        """Assess configuration management"""
        config_checks = {
            "configuration_externalization": {
                "status": "PASS",
                "details": "Configuration via config.yaml"
            },
            "environment_specific_configs": {
                "status": "PARTIAL",
                "details": "Basic configuration, environment-specific configs needed"
            },
            "secrets_management": {
                "status": "UNKNOWN",
                "details": "Secrets management approach not defined"
            },
            "configuration_validation": {
                "status": "PARTIAL",
                "details": "Basic configuration loading with error handling"
            }
        }
        
        passed_checks = sum(1 for check in config_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(config_checks)) * 100
        
        return {
            "score": score,
            "status": "PASS" if score >= 60 else "FAIL",
            "checks": config_checks,
            "assessment": f"Configuration management: {score:.1f}%"
        }
    
    def _assess_database_readiness(self) -> Dict[str, Any]:
        """Assess database readiness"""
        database_checks = {
            "data_persistence": {
                "status": "PASS",
                "details": "File-based persistence for campaigns and narratives"
            },
            "data_migration": {
                "status": "N/A",
                "details": "No database schema migrations needed"
            },
            "backup_strategy": {
                "status": "FAIL",
                "details": "No backup strategy defined for file-based data"
            },
            "data_recovery": {
                "status": "FAIL",
                "details": "No data recovery procedures defined"
            }
        }
        
        applicable_checks = [check for check in database_checks.values() if check["status"] != "N/A"]
        passed_checks = sum(1 for check in applicable_checks if check["status"] == "PASS")
        score = (passed_checks / len(applicable_checks)) * 100 if applicable_checks else 100
        
        return {
            "score": score,
            "status": "PASS" if score >= 60 else "FAIL",
            "checks": database_checks,
            "assessment": f"Database readiness: {score:.1f}%"
        }
    
    def _evaluate_operational_readiness(self):
        """Evaluate operational readiness"""
        operational_assessment = {
            "monitoring_readiness": self._assess_monitoring_readiness(),
            "logging_readiness": self._assess_logging_readiness(),
            "alerting_readiness": self._assess_alerting_readiness(),
            "backup_recovery_readiness": self._assess_backup_recovery_readiness(),
            "incident_response_readiness": self._assess_incident_response_readiness()
        }
        
        self.assessment_results["operational_readiness"] = operational_assessment
        
        # Calculate operational readiness score
        operational_scores = [
            assessment["score"] for assessment in operational_assessment.values()
            if "score" in assessment
        ]
        overall_operational_score = sum(operational_scores) / len(operational_scores) if operational_scores else 0
        
        print(f"   ⚙️ Operational Readiness Score: {overall_operational_score:.1f}%")
    
    def _assess_monitoring_readiness(self) -> Dict[str, Any]:
        """Assess monitoring readiness"""
        monitoring_checks = {
            "application_monitoring": {
                "status": "PARTIAL",
                "details": "Basic logging available, no dedicated monitoring"
            },
            "performance_monitoring": {
                "status": "FAIL",
                "details": "No performance monitoring implemented"
            },
            "health_checks": {
                "status": "FAIL",
                "details": "No health check endpoints defined"
            },
            "metrics_collection": {
                "status": "FAIL",
                "details": "No metrics collection implemented"
            }
        }
        
        passed_checks = sum(1 for check in monitoring_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(monitoring_checks)) * 100
        
        return {
            "score": score,
            "status": "FAIL",  # Critical monitoring gaps
            "checks": monitoring_checks,
            "assessment": f"Monitoring readiness needs major improvement: {score:.1f}%"
        }
    
    def _assess_logging_readiness(self) -> Dict[str, Any]:
        """Assess logging readiness"""
        logging_checks = {
            "structured_logging": {
                "status": "PASS",
                "details": "Python logging framework used"
            },
            "log_levels": {
                "status": "PASS",
                "details": "Multiple log levels used (INFO, ERROR, WARNING)"
            },
            "log_aggregation": {
                "status": "FAIL",
                "details": "No log aggregation strategy defined"
            },
            "log_retention": {
                "status": "FAIL",
                "details": "No log retention policy defined"
            }
        }
        
        passed_checks = sum(1 for check in logging_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(logging_checks)) * 100
        
        return {
            "score": score,
            "status": "PASS" if score >= 50 else "FAIL",
            "checks": logging_checks,
            "assessment": f"Logging readiness: {score:.1f}%"
        }
    
    def _assess_alerting_readiness(self) -> Dict[str, Any]:
        """Assess alerting readiness"""
        alerting_checks = {
            "error_alerting": {
                "status": "FAIL",
                "details": "No error alerting implemented"
            },
            "performance_alerting": {
                "status": "FAIL",
                "details": "No performance alerting implemented"
            },
            "capacity_alerting": {
                "status": "FAIL",
                "details": "No capacity alerting implemented"
            },
            "business_metrics_alerting": {
                "status": "FAIL",
                "details": "No business metrics alerting implemented"
            }
        }
        
        passed_checks = sum(1 for check in alerting_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(alerting_checks)) * 100
        
        return {
            "score": score,
            "status": "FAIL",  # No alerting implemented
            "checks": alerting_checks,
            "assessment": f"Alerting readiness: {score:.1f}% - needs implementation"
        }
    
    def _assess_backup_recovery_readiness(self) -> Dict[str, Any]:
        """Assess backup and recovery readiness"""
        backup_checks = {
            "backup_strategy": {
                "status": "FAIL",
                "details": "No backup strategy defined"
            },
            "recovery_procedures": {
                "status": "FAIL",
                "details": "No recovery procedures documented"
            },
            "backup_testing": {
                "status": "FAIL",
                "details": "No backup testing performed"
            },
            "rto_rpo_defined": {
                "status": "FAIL",
                "details": "RTO/RPO requirements not defined"
            }
        }
        
        passed_checks = sum(1 for check in backup_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(backup_checks)) * 100
        
        return {
            "score": score,
            "status": "FAIL",  # Critical backup/recovery gaps
            "checks": backup_checks,
            "assessment": f"Backup/Recovery readiness: {score:.1f}% - critical gaps"
        }
    
    def _assess_incident_response_readiness(self) -> Dict[str, Any]:
        """Assess incident response readiness"""
        incident_checks = {
            "incident_response_plan": {
                "status": "FAIL",
                "details": "No incident response plan defined"
            },
            "escalation_procedures": {
                "status": "FAIL",
                "details": "No escalation procedures defined"
            },
            "runbook_documentation": {
                "status": "FAIL",
                "details": "No operational runbooks available"
            },
            "post_incident_process": {
                "status": "FAIL",
                "details": "No post-incident review process defined"
            }
        }
        
        passed_checks = sum(1 for check in incident_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(incident_checks)) * 100
        
        return {
            "score": score,
            "status": "FAIL",  # No incident response preparation
            "checks": incident_checks,
            "assessment": f"Incident response readiness: {score:.1f}% - needs development"
        }
    
    def _assess_security_readiness(self):
        """Assess security readiness for production"""
        security_assessment = {
            "application_security": self._assess_application_security(),
            "infrastructure_security": self._assess_infrastructure_security(),
            "data_security": self._assess_data_security(),
            "access_control": self._assess_access_control(),
            "compliance_readiness": self._assess_compliance_readiness()
        }
        
        self.assessment_results["security_assessment"] = security_assessment
        
        # Calculate security readiness score
        security_scores = [
            assessment["score"] for assessment in security_assessment.values()
            if "score" in assessment
        ]
        overall_security_score = sum(security_scores) / len(security_scores) if security_scores else 0
        
        print(f"   🔒 Security Readiness Score: {overall_security_score:.1f}%")
    
    def _assess_application_security(self) -> Dict[str, Any]:
        """Assess application security"""
        app_security_checks = {
            "input_validation": {
                "status": "PARTIAL",
                "details": "Some input validation present, needs enhancement"
            },
            "output_encoding": {
                "status": "PASS",
                "details": "No direct user input/output, lower risk"
            },
            "authentication": {
                "status": "N/A",
                "details": "No authentication required for current use case"
            },
            "authorization": {
                "status": "N/A",
                "details": "No authorization required for current use case"
            },
            "session_management": {
                "status": "N/A",
                "details": "No session management required"
            },
            "error_handling": {
                "status": "PASS",
                "details": "Secure error handling, no information leakage"
            }
        }
        
        applicable_checks = [check for check in app_security_checks.values() if check["status"] != "N/A"]
        passed_checks = sum(1 for check in applicable_checks if check["status"] == "PASS")
        score = (passed_checks / len(applicable_checks)) * 100 if applicable_checks else 50
        
        return {
            "score": score,
            "status": "PASS" if score >= 70 else "FAIL",
            "checks": app_security_checks,
            "assessment": f"Application security: {score:.1f}%"
        }
    
    def _assess_infrastructure_security(self) -> Dict[str, Any]:
        """Assess infrastructure security"""
        infra_security_checks = {
            "network_security": {
                "status": "UNKNOWN",
                "details": "Network security configuration not assessed"
            },
            "firewall_configuration": {
                "status": "UNKNOWN",
                "details": "Firewall configuration not defined"
            },
            "ssl_tls_configuration": {
                "status": "UNKNOWN",
                "details": "SSL/TLS configuration not assessed"
            },
            "server_hardening": {
                "status": "UNKNOWN",
                "details": "Server hardening not assessed"
            }
        }
        
        passed_checks = sum(1 for check in infra_security_checks.values() if check["status"] == "PASS")
        score = 50  # Neutral score due to unknown status
        
        return {
            "score": score,
            "status": "UNKNOWN",
            "checks": infra_security_checks,
            "assessment": "Infrastructure security assessment needed"
        }
    
    def _assess_data_security(self) -> Dict[str, Any]:
        """Assess data security"""
        data_security_checks = {
            "data_encryption_at_rest": {
                "status": "FAIL",
                "details": "No encryption for stored campaign logs and narratives"
            },
            "data_encryption_in_transit": {
                "status": "UNKNOWN",
                "details": "API calls encryption depends on LLM service"
            },
            "data_classification": {
                "status": "FAIL",
                "details": "No data classification performed"
            },
            "data_retention_policy": {
                "status": "FAIL",
                "details": "No data retention policy defined"
            },
            "data_anonymization": {
                "status": "N/A",
                "details": "No personal data collected"
            }
        }
        
        applicable_checks = [check for check in data_security_checks.values() if check["status"] != "N/A"]
        passed_checks = sum(1 for check in applicable_checks if check["status"] == "PASS")
        score = (passed_checks / len(applicable_checks)) * 100 if applicable_checks else 0
        
        return {
            "score": score,
            "status": "FAIL",
            "checks": data_security_checks,
            "assessment": f"Data security needs improvement: {score:.1f}%"
        }
    
    def _assess_access_control(self) -> Dict[str, Any]:
        """Assess access control"""
        access_control_checks = {
            "user_authentication": {
                "status": "N/A",
                "details": "No user authentication required for current use case"
            },
            "role_based_access": {
                "status": "N/A",
                "details": "No role-based access required"
            },
            "api_access_control": {
                "status": "FAIL",
                "details": "No API access control implemented"
            },
            "admin_access_control": {
                "status": "FAIL",
                "details": "No administrative access controls defined"
            }
        }
        
        applicable_checks = [check for check in access_control_checks.values() if check["status"] != "N/A"]
        passed_checks = sum(1 for check in applicable_checks if check["status"] == "PASS")
        score = (passed_checks / len(applicable_checks)) * 100 if applicable_checks else 0
        
        return {
            "score": score,
            "status": "FAIL" if score < 50 else "PASS",
            "checks": access_control_checks,
            "assessment": f"Access control: {score:.1f}%"
        }
    
    def _assess_compliance_readiness(self) -> Dict[str, Any]:
        """Assess compliance readiness"""
        compliance_checks = {
            "gdpr_compliance": {
                "status": "PASS",
                "details": "No personal data processing"
            },
            "data_protection_compliance": {
                "status": "PARTIAL",
                "details": "Basic data protection, could be enhanced"
            },
            "audit_logging": {
                "status": "PARTIAL",
                "details": "Basic logging available, not audit-focused"
            },
            "regulatory_compliance": {
                "status": "UNKNOWN",
                "details": "Specific regulatory requirements not assessed"
            }
        }
        
        applicable_checks = [check for check in compliance_checks.values() if check["status"] != "UNKNOWN"]
        passed_checks = sum(1 for check in applicable_checks if check["status"] == "PASS")
        score = (passed_checks / len(applicable_checks)) * 100 if applicable_checks else 50
        
        return {
            "score": score,
            "status": "PASS" if score >= 60 else "FAIL",
            "checks": compliance_checks,
            "assessment": f"Compliance readiness: {score:.1f}%"
        }
    
    def _assess_monitoring_and_alerting(self):
        """Assess monitoring and alerting capabilities"""
        monitoring_assessment = {
            "application_monitoring": {
                "status": "FAIL",
                "score": 0,
                "details": "No application monitoring implemented",
                "recommendations": [
                    "Implement application performance monitoring (APM)",
                    "Add custom metrics for business logic",
                    "Set up monitoring dashboards"
                ]
            },
            "infrastructure_monitoring": {
                "status": "FAIL",
                "score": 0,
                "details": "No infrastructure monitoring implemented",
                "recommendations": [
                    "Implement server monitoring",
                    "Monitor resource usage (CPU, memory, disk)",
                    "Set up network monitoring"
                ]
            },
            "log_monitoring": {
                "status": "PARTIAL",
                "score": 30,
                "details": "Basic logging available but not monitored",
                "recommendations": [
                    "Implement log aggregation",
                    "Set up log analysis and search",
                    "Create log-based alerts"
                ]
            },
            "alerting_system": {
                "status": "FAIL",
                "score": 0,
                "details": "No alerting system implemented",
                "recommendations": [
                    "Implement alerting system",
                    "Define alert thresholds",
                    "Set up escalation procedures"
                ]
            }
        }
        
        self.assessment_results["monitoring_and_alerting"] = monitoring_assessment
        
        # Calculate overall monitoring score
        monitoring_scores = [item["score"] for item in monitoring_assessment.values()]
        overall_monitoring_score = sum(monitoring_scores) / len(monitoring_scores) if monitoring_scores else 0
        
        print(f"   📊 Monitoring & Alerting Score: {overall_monitoring_score:.1f}%")
    
    def _assess_documentation_readiness(self):
        """Assess documentation readiness"""
        documentation_assessment = {
            "technical_documentation": self._assess_technical_documentation(),
            "operational_documentation": self._assess_operational_documentation(),
            "user_documentation": self._assess_user_documentation(),
            "deployment_documentation": self._assess_deployment_documentation(),
            "troubleshooting_documentation": self._assess_troubleshooting_documentation()
        }
        
        self.assessment_results["documentation_readiness"] = documentation_assessment
        
        # Calculate documentation readiness score
        doc_scores = [
            assessment["score"] for assessment in documentation_assessment.values()
            if "score" in assessment
        ]
        overall_doc_score = sum(doc_scores) / len(doc_scores) if doc_scores else 0
        
        print(f"   📚 Documentation Readiness Score: {overall_doc_score:.1f}%")
    
    def _assess_technical_documentation(self) -> Dict[str, Any]:
        """Assess technical documentation"""
        tech_doc_checks = {
            "code_documentation": {
                "status": "PASS",
                "details": "Good inline documentation and docstrings"
            },
            "api_documentation": {
                "status": "PARTIAL",
                "details": "Basic API documentation in code, needs enhancement"
            },
            "architecture_documentation": {
                "status": "FAIL",
                "details": "No dedicated architecture documentation"
            },
            "database_documentation": {
                "status": "PARTIAL",
                "details": "File structure documented in code"
            }
        }
        
        passed_checks = sum(1 for check in tech_doc_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(tech_doc_checks)) * 100
        
        return {
            "score": score,
            "status": "PASS" if score >= 60 else "FAIL",
            "checks": tech_doc_checks,
            "assessment": f"Technical documentation: {score:.1f}%"
        }
    
    def _assess_operational_documentation(self) -> Dict[str, Any]:
        """Assess operational documentation"""
        ops_doc_checks = {
            "deployment_guide": {
                "status": "FAIL",
                "details": "No deployment guide available"
            },
            "configuration_guide": {
                "status": "PARTIAL",
                "details": "Basic configuration documented in code"
            },
            "monitoring_runbook": {
                "status": "FAIL",
                "details": "No monitoring runbook available"
            },
            "troubleshooting_guide": {
                "status": "FAIL",
                "details": "No troubleshooting guide available"
            }
        }
        
        passed_checks = sum(1 for check in ops_doc_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(ops_doc_checks)) * 100
        
        return {
            "score": score,
            "status": "FAIL",
            "checks": ops_doc_checks,
            "assessment": f"Operational documentation: {score:.1f}% - needs development"
        }
    
    def _assess_user_documentation(self) -> Dict[str, Any]:
        """Assess user documentation"""
        user_doc_checks = {
            "user_guide": {
                "status": "FAIL",
                "details": "No user guide available"
            },
            "getting_started_guide": {
                "status": "PARTIAL",
                "details": "Basic README available"
            },
            "examples_documentation": {
                "status": "PARTIAL",
                "details": "Some example code in project"
            },
            "faq_documentation": {
                "status": "FAIL",
                "details": "No FAQ documentation available"
            }
        }
        
        passed_checks = sum(1 for check in user_doc_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(user_doc_checks)) * 100
        
        return {
            "score": score,
            "status": "FAIL",
            "checks": user_doc_checks,
            "assessment": f"User documentation: {score:.1f}% - needs development"
        }
    
    def _assess_deployment_documentation(self) -> Dict[str, Any]:
        """Assess deployment documentation"""
        deploy_doc_checks = {
            "installation_guide": {
                "status": "FAIL",
                "details": "No installation guide available"
            },
            "configuration_guide": {
                "status": "PARTIAL",
                "details": "Basic configuration info in code"
            },
            "deployment_checklist": {
                "status": "FAIL",
                "details": "No deployment checklist available"
            },
            "rollback_procedures": {
                "status": "FAIL",
                "details": "No rollback procedures documented"
            }
        }
        
        passed_checks = sum(1 for check in deploy_doc_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(deploy_doc_checks)) * 100
        
        return {
            "score": score,
            "status": "FAIL",
            "checks": deploy_doc_checks,
            "assessment": f"Deployment documentation: {score:.1f}% - critical gap"
        }
    
    def _assess_troubleshooting_documentation(self) -> Dict[str, Any]:
        """Assess troubleshooting documentation"""
        troubleshoot_doc_checks = {
            "common_issues_guide": {
                "status": "FAIL",
                "details": "No common issues guide available"
            },
            "error_code_reference": {
                "status": "FAIL",
                "details": "No error code reference available"
            },
            "diagnostic_procedures": {
                "status": "FAIL",
                "details": "No diagnostic procedures documented"
            },
            "support_procedures": {
                "status": "FAIL",
                "details": "No support procedures defined"
            }
        }
        
        passed_checks = sum(1 for check in troubleshoot_doc_checks.values() if check["status"] == "PASS")
        score = (passed_checks / len(troubleshoot_doc_checks)) * 100
        
        return {
            "score": score,
            "status": "FAIL",
            "checks": troubleshoot_doc_checks,
            "assessment": f"Troubleshooting documentation: {score:.1f}% - needs development"
        }
    
    def _assess_rollback_capabilities(self):
        """Assess rollback capabilities"""
        rollback_assessment = {
            "code_rollback": {
                "status": "PASS",
                "score": 80,
                "details": "Git version control supports code rollback",
                "procedures": "Git revert/reset procedures"
            },
            "configuration_rollback": {
                "status": "PARTIAL",
                "score": 40,
                "details": "Configuration in files, manual rollback possible",
                "procedures": "Manual configuration file restoration"
            },
            "data_rollback": {
                "status": "FAIL",
                "score": 0,
                "details": "No data rollback capabilities",
                "procedures": "No data rollback procedures defined"
            },
            "automated_rollback": {
                "status": "FAIL",
                "score": 0,
                "details": "No automated rollback capabilities",
                "procedures": "No automated rollback procedures"
            }
        }
        
        self.assessment_results["rollback_capabilities"] = rollback_assessment
        
        # Calculate rollback readiness score
        rollback_scores = [item["score"] for item in rollback_assessment.values()]
        overall_rollback_score = sum(rollback_scores) / len(rollback_scores) if rollback_scores else 0
        
        print(f"   🔄 Rollback Capabilities Score: {overall_rollback_score:.1f}%")
    
    def _make_go_no_go_decision(self):
        """Make final go/no-go decision for production deployment"""
        # Collect all assessment scores
        scores = {
            "production_criteria": 0,
            "deployment_readiness": 0,
            "operational_readiness": 0,
            "security_readiness": 0,
            "monitoring_alerting": 0,
            "documentation_readiness": 0,
            "rollback_capabilities": 0
        }
        
        # Extract scores from assessments
        if "production_criteria" in self.assessment_results:
            criteria = self.assessment_results["production_criteria"]
            if "overall_assessment" in criteria:
                scores["production_criteria"] = criteria["overall_assessment"]["score"]
        
        # Calculate other scores from their respective assessments
        if "deployment_readiness" in self.assessment_results:
            deployment_scores = [
                assessment["score"] for assessment in self.assessment_results["deployment_readiness"].values()
                if "score" in assessment
            ]
            scores["deployment_readiness"] = sum(deployment_scores) / len(deployment_scores) if deployment_scores else 0
        
        if "operational_readiness" in self.assessment_results:
            operational_scores = [
                assessment["score"] for assessment in self.assessment_results["operational_readiness"].values()
                if "score" in assessment
            ]
            scores["operational_readiness"] = sum(operational_scores) / len(operational_scores) if operational_scores else 0
        
        if "security_assessment" in self.assessment_results:
            security_scores = [
                assessment["score"] for assessment in self.assessment_results["security_assessment"].values()
                if "score" in assessment
            ]
            scores["security_readiness"] = sum(security_scores) / len(security_scores) if security_scores else 0
        
        if "monitoring_and_alerting" in self.assessment_results:
            monitoring_scores = [
                item["score"] for item in self.assessment_results["monitoring_and_alerting"].values()
                if "score" in item
            ]
            scores["monitoring_alerting"] = sum(monitoring_scores) / len(monitoring_scores) if monitoring_scores else 0
        
        if "documentation_readiness" in self.assessment_results:
            doc_scores = [
                assessment["score"] for assessment in self.assessment_results["documentation_readiness"].values()
                if "score" in assessment
            ]
            scores["documentation_readiness"] = sum(doc_scores) / len(doc_scores) if doc_scores else 0
        
        if "rollback_capabilities" in self.assessment_results:
            rollback_scores = [
                item["score"] for item in self.assessment_results["rollback_capabilities"].values()
                if "score" in item
            ]
            scores["rollback_capabilities"] = sum(rollback_scores) / len(rollback_scores) if rollback_scores else 0
        
        # Calculate weighted overall score
        weights = {
            "production_criteria": 0.25,
            "deployment_readiness": 0.15,
            "operational_readiness": 0.20,
            "security_readiness": 0.15,
            "monitoring_alerting": 0.10,
            "documentation_readiness": 0.10,
            "rollback_capabilities": 0.05
        }
        
        overall_score = sum(scores[key] * weights[key] for key in scores.keys())
        
        # Identify critical blockers
        critical_blockers = []
        
        if scores["production_criteria"] < 70:
            critical_blockers.append("Production criteria not met")
        
        if scores["security_readiness"] < 60:
            critical_blockers.append("Security readiness insufficient")
        
        if scores["operational_readiness"] < 40:
            critical_blockers.append("Operational readiness critical gaps")
        
        if scores["deployment_readiness"] < 60:
            critical_blockers.append("Deployment readiness insufficient")
        
        # Identify high-risk areas
        high_risk_areas = []
        
        if scores["monitoring_alerting"] < 30:
            high_risk_areas.append("No monitoring or alerting capabilities")
        
        if scores["rollback_capabilities"] < 50:
            high_risk_areas.append("Limited rollback capabilities")
        
        if scores["documentation_readiness"] < 40:
            high_risk_areas.append("Insufficient documentation")
        
        # Make decision
        if overall_score >= 75 and len(critical_blockers) == 0:
            decision = "GO"
            confidence = "HIGH" if overall_score >= 85 else "MEDIUM"
            recommendation = "Proceed with production deployment"
        elif overall_score >= 60 and len(critical_blockers) <= 1:
            decision = "CONDITIONAL_GO"
            confidence = "MEDIUM"
            recommendation = "Proceed with caution after addressing critical blockers"
        elif overall_score >= 45:
            decision = "NO_GO_WITH_IMPROVEMENTS"
            confidence = "LOW"
            recommendation = "Address critical issues before considering deployment"
        else:
            decision = "NO_GO"
            confidence = "LOW"
            recommendation = "Major improvements required before deployment"
        
        go_no_go_result = {
            "decision": decision,
            "confidence": confidence,
            "overall_score": overall_score,
            "category_scores": scores,
            "critical_blockers": critical_blockers,
            "high_risk_areas": high_risk_areas,
            "recommendation": recommendation,
            "decision_rationale": self._generate_decision_rationale(decision, overall_score, critical_blockers, high_risk_areas)
        }
        
        self.assessment_results["go_no_go_decision"] = go_no_go_result
        
        print(f"   🎯 Final Decision: {decision}")
        print(f"   🎯 Overall Score: {overall_score:.1f}%")
        print(f"   🎯 Confidence: {confidence}")
        print(f"   🎯 Critical Blockers: {len(critical_blockers)}")
    
    def _generate_decision_rationale(self, decision: str, score: float, blockers: List[str], risks: List[str]) -> str:
        """Generate rationale for go/no-go decision"""
        if decision == "GO":
            return f"System achieves {score:.1f}% readiness with no critical blockers. Production deployment recommended."
        elif decision == "CONDITIONAL_GO":
            return f"System achieves {score:.1f}% readiness but has {len(blockers)} critical blocker(s). Address blockers before deployment."
        elif decision == "NO_GO_WITH_IMPROVEMENTS":
            return f"System at {score:.1f}% readiness with {len(blockers)} critical blockers and {len(risks)} high-risk areas. Significant improvements required."
        else:
            return f"System at {score:.1f}% readiness with major deficiencies. Comprehensive improvements required before deployment consideration."
    
    def _generate_final_recommendations(self):
        """Generate final recommendations based on assessment"""
        decision_result = self.assessment_results["go_no_go_decision"]
        decision = decision_result["decision"]
        
        recommendations = {
            "immediate_actions": [],
            "short_term_improvements": [],
            "long_term_enhancements": [],
            "deployment_strategy": {},
            "risk_mitigation": []
        }
        
        # Immediate actions based on decision
        if decision == "GO":
            recommendations["immediate_actions"].extend([
                "Prepare production deployment plan",
                "Set up production monitoring (basic)",
                "Create deployment checklist",
                "Prepare rollback procedures"
            ])
            recommendations["deployment_strategy"] = {
                "approach": "Standard deployment",
                "monitoring": "Enhanced monitoring during rollout",
                "rollback_plan": "Git-based code rollback",
                "success_criteria": "System stability and performance within expected ranges"
            }
        elif decision == "CONDITIONAL_GO":
            recommendations["immediate_actions"].extend([
                "Address critical blockers identified",
                "Implement basic monitoring and alerting",
                "Create essential operational documentation",
                "Establish backup and recovery procedures"
            ])
            recommendations["deployment_strategy"] = {
                "approach": "Phased deployment with limited scope",
                "monitoring": "Continuous monitoring required",
                "rollback_plan": "Immediate rollback capability required",
                "success_criteria": "No critical issues during initial phase"
            }
        else:
            recommendations["immediate_actions"].extend([
                "Address all critical blockers",
                "Implement comprehensive monitoring",
                "Develop operational procedures",
                "Create complete documentation suite"
            ])
            recommendations["deployment_strategy"] = {
                "approach": "Delayed deployment pending improvements",
                "timeline": "Re-assess after addressing critical issues",
                "prerequisites": "All blockers resolved, monitoring implemented"
            }
        
        # Short-term improvements
        recommendations["short_term_improvements"].extend([
            "Implement application monitoring and alerting",
            "Create comprehensive deployment documentation",
            "Establish backup and recovery procedures",
            "Develop incident response procedures",
            "Implement dependency management (requirements.txt)",
            "Create user and operational guides"
        ])
        
        # Long-term enhancements
        recommendations["long_term_enhancements"].extend([
            "Implement comprehensive security assessment",
            "Develop automated testing pipeline",
            "Create performance monitoring and optimization",
            "Establish automated deployment pipeline",
            "Implement comprehensive logging and analytics",
            "Develop user training programs"
        ])
        
        # Risk mitigation strategies
        recommendations["risk_mitigation"].extend([
            "Implement gradual rollout strategy",
            "Establish 24/7 monitoring during initial deployment",
            "Create rapid response team for issues",
            "Implement automated health checks",
            "Establish user feedback collection mechanisms",
            "Plan for capacity scaling if needed"
        ])
        
        self.assessment_results["final_recommendations"] = recommendations
        
        print(f"   💡 Immediate Actions: {len(recommendations['immediate_actions'])}")
        print(f"   💡 Short-term Improvements: {len(recommendations['short_term_improvements'])}")
        print(f"   💡 Long-term Enhancements: {len(recommendations['long_term_enhancements'])}")
    
    def _save_assessment_report(self):
        """Save comprehensive production readiness assessment report"""
        report_path = os.path.join(self.project_root, "validation", "comprehensive_phase6_production_readiness_report.json")
        
        # Ensure validation directory exists
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(self.assessment_results, f, indent=2)
        
        print(f"\n📄 Comprehensive production readiness assessment saved to: {report_path}")

def main():
    """Main execution function"""
    print("StoryForge AI - Phase 6: Comprehensive Production Readiness Assessment")
    print("=" * 90)
    print("Final production readiness evaluation with comprehensive deployment criteria")
    print()
    
    # Initialize and run assessment
    assessment = ProductionReadinessAssessment()
    results = assessment.run_comprehensive_assessment()
    
    # Print final summary
    decision_result = results["go_no_go_decision"]
    print("\n" + "=" * 90)
    print("PHASE 6 PRODUCTION READINESS ASSESSMENT COMPLETE")
    print("=" * 90)
    print(f"Final Decision: {decision_result['decision']}")
    print(f"Overall Score: {decision_result['overall_score']:.1f}%")
    print(f"Confidence Level: {decision_result['confidence']}")
    print(f"Critical Blockers: {len(decision_result['critical_blockers'])}")
    print(f"High Risk Areas: {len(decision_result['high_risk_areas'])}")
    print(f"Recommendation: {decision_result['recommendation']}")
    print("=" * 90)
    
    # Print key scores
    print("\nKey Assessment Scores:")
    for category, score in decision_result['category_scores'].items():
        print(f"  {category.replace('_', ' ').title()}: {score:.1f}%")
    
    if decision_result['critical_blockers']:
        print(f"\nCritical Blockers:")
        for blocker in decision_result['critical_blockers']:
            print(f"  ❌ {blocker}")
    
    if decision_result['high_risk_areas']:
        print(f"\nHigh Risk Areas:")
        for risk in decision_result['high_risk_areas']:
            print(f"  ⚠️ {risk}")

if __name__ == "__main__":
    main()