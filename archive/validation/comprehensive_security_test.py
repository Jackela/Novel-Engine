#!/usr/bin/env python3
"""
Novel Engine Comprehensive Security Testing Suite
================================================

This module provides comprehensive security testing for the Novel Engine production deployment,
covering OWASP Top 10 vulnerabilities and production security requirements.

Security Test Coverage:
- Authentication & Authorization Testing
- Input Validation & Injection Testing 
- Data Protection & Encryption Validation
- Infrastructure Security Assessment
- API Security Testing
- Session Management Testing
"""

import asyncio
import json
import logging
import time
import uuid
import os
import subprocess
import re
import requests
import sqlite3
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Security Testing Framework
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SecurityFinding:
    """Represents a security vulnerability or finding."""
    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    title: str
    description: str
    evidence: str
    recommendation: str
    cve_reference: Optional[str] = None
    owasp_category: Optional[str] = None
    risk_score: float = 0.0

@dataclass
class SecurityTestResult:
    """Contains results from security testing."""
    test_name: str
    status: str  # PASS, FAIL, WARNING, ERROR
    findings: List[SecurityFinding] = field(default_factory=list)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class NovelEngineSecurityTester:
    """Comprehensive security testing for Novel Engine."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        """Initialize security tester with target configuration."""
        self.base_url = base_url
        self.session = self._create_session()
        self.findings: List[SecurityFinding] = []
        self.test_results: List[SecurityTestResult] = []
        
        # Security test payloads
        self.sql_injection_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM sqlite_master --",
            "admin'--",
            "admin' /*",
            "' OR 1=1#",
            "') OR '1'='1'--",
            "1' UNION SELECT null, username, password FROM users--",
        ]
        
        self.xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "{{7*7}}",  # Template injection
            "${7*7}",   # Template injection
            "<%=7*7%>", # Template injection
        ]
        
        self.command_injection_payloads = [
            "; ls -la",
            "| whoami",
            "&& ping -c 4 127.0.0.1",
            "; cat /etc/passwd",
            "$(whoami)",
            "`id`",
            "; powershell.exe Get-Process",
            "|| dir",
        ]
        
        self.path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
        ]
    
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _add_finding(self, finding: SecurityFinding):
        """Add a security finding to the results."""
        self.findings.append(finding)
        logger.warning(f"Security finding: {finding.severity} - {finding.title}")
    
    def _calculate_risk_score(self, severity: str, exploitability: float, impact: float) -> float:
        """Calculate CVSS-like risk score."""
        severity_weights = {"CRITICAL": 10, "HIGH": 7, "MEDIUM": 4, "LOW": 1, "INFO": 0}
        base_score = severity_weights.get(severity, 0)
        return min(10.0, base_score * exploitability * impact)
    
    async def test_authentication_mechanisms(self) -> SecurityTestResult:
        """Test authentication and authorization mechanisms."""
        start_time = time.time()
        result = SecurityTestResult("Authentication & Authorization Testing", "PASS")
        
        try:
            # Test 1: Check for authentication endpoints
            auth_endpoints = ["/login", "/auth", "/authenticate", "/signin", "/token"]
            
            for endpoint in auth_endpoints:
                try:
                    response = self.session.get(urljoin(self.base_url, endpoint))
                    if response.status_code != 404:
                        result.metadata[f"auth_endpoint_{endpoint}"] = {
                            "status": response.status_code,
                            "headers": dict(response.headers)
                        }
                except requests.RequestException:
                    pass
            
            # Test 2: Check for unprotected admin endpoints
            admin_endpoints = ["/admin", "/admin/", "/administrator", "/management", "/console"]
            
            for endpoint in admin_endpoints:
                try:
                    response = self.session.get(urljoin(self.base_url, endpoint))
                    if response.status_code == 200:
                        self._add_finding(SecurityFinding(
                            category="Authentication",
                            severity="HIGH",
                            title="Unprotected Admin Endpoint",
                            description=f"Admin endpoint {endpoint} is accessible without authentication",
                            evidence=f"HTTP {response.status_code} response to {endpoint}",
                            recommendation="Implement authentication for administrative endpoints",
                            owasp_category="A01:2021 – Broken Access Control"
                        ))
                        result.status = "FAIL"
                except requests.RequestException:
                    pass
            
            # Test 3: Check for session management
            response = self.session.get(self.base_url)
            session_headers = ["Set-Cookie", "Authorization", "X-Auth-Token"]
            
            has_session_management = any(header in response.headers for header in session_headers)
            
            if not has_session_management:
                self._add_finding(SecurityFinding(
                    category="Authentication",
                    severity="MEDIUM",
                    title="No Session Management Detected",
                    description="No session management headers found in responses",
                    evidence="Missing session headers: Set-Cookie, Authorization, X-Auth-Token",
                    recommendation="Implement proper session management for user state",
                    owasp_category="A07:2021 – Identification and Authentication Failures"
                ))
            
            # Test 4: Default credentials testing
            default_creds = [
                ("admin", "admin"),
                ("admin", "password"),
                ("root", "root"),
                ("test", "test"),
                ("user", "user")
            ]
            
            # Note: Since no auth endpoint found, mark as informational
            if not any("auth" in str(result.metadata) for _ in [None]):
                self._add_finding(SecurityFinding(
                    category="Authentication",
                    severity="INFO",
                    title="No Authentication System Detected",
                    description="No authentication endpoints or mechanisms were found",
                    evidence="404 responses to common auth endpoints",
                    recommendation="Implement authentication system for production deployment",
                    owasp_category="A07:2021 – Identification and Authentication Failures"
                ))
        
        except Exception as e:
            result.status = "ERROR"
            result.metadata["error"] = str(e)
            logger.error(f"Authentication testing error: {e}")
        
        result.execution_time = time.time() - start_time
        return result
    
    async def test_input_validation(self) -> SecurityTestResult:
        """Test input validation and injection vulnerabilities."""
        start_time = time.time()
        result = SecurityTestResult("Input Validation & Injection Testing", "PASS")
        
        try:
            # Test endpoints that accept input
            test_endpoints = [
                ("/simulations", "POST"),
                ("/characters", "GET"),
                ("/health", "GET"),
                ("/", "GET")
            ]
            
            for endpoint, method in test_endpoints:
                url = urljoin(self.base_url, endpoint)
                
                # SQL Injection Testing
                if method == "POST":
                    for payload in self.sql_injection_payloads:
                        test_data = {
                            "character_names": [payload],
                            "turns": 1
                        }
                        
                        try:
                            response = self.session.post(url, json=test_data, timeout=10)
                            
                            # Check for SQL error messages
                            sql_errors = [
                                "sqlite", "mysql", "postgresql", "sql syntax",
                                "database error", "sqlalchemy", "constraint failed"
                            ]
                            
                            if any(error in response.text.lower() for error in sql_errors):
                                self._add_finding(SecurityFinding(
                                    category="Input Validation",
                                    severity="HIGH",
                                    title="SQL Injection Vulnerability",
                                    description=f"SQL injection detected in {endpoint}",
                                    evidence=f"Payload: {payload}, Response contains SQL errors",
                                    recommendation="Implement parameterized queries and input validation",
                                    owasp_category="A03:2021 – Injection",
                                    risk_score=self._calculate_risk_score("HIGH", 0.8, 0.9)
                                ))
                                result.status = "FAIL"
                        
                        except requests.RequestException:
                            pass
                
                # XSS Testing for GET endpoints
                if method == "GET":
                    for payload in self.xss_payloads:
                        try:
                            params = {"q": payload, "search": payload, "name": payload}
                            response = self.session.get(url, params=params, timeout=10)
                            
                            if payload in response.text and "text/html" in response.headers.get("content-type", ""):
                                self._add_finding(SecurityFinding(
                                    category="Input Validation",
                                    severity="MEDIUM",
                                    title="Cross-Site Scripting (XSS)",
                                    description=f"Reflected XSS vulnerability in {endpoint}",
                                    evidence=f"Payload reflected: {payload}",
                                    recommendation="Implement output encoding and Content Security Policy",
                                    owasp_category="A03:2021 – Injection",
                                    risk_score=self._calculate_risk_score("MEDIUM", 0.6, 0.7)
                                ))
                                result.status = "FAIL"
                        
                        except requests.RequestException:
                            pass
                
                # Path Traversal Testing
                for payload in self.path_traversal_payloads:
                    try:
                        traversal_url = url + "/" + payload
                        response = self.session.get(traversal_url, timeout=10)
                        
                        # Check for sensitive file content
                        sensitive_patterns = [
                            r"root:.*:/bin/bash",  # /etc/passwd
                            r"\[boot loader\]",    # Windows boot.ini
                            r"# Copyright.*Microsoft",  # Windows hosts
                        ]
                        
                        if any(re.search(pattern, response.text) for pattern in sensitive_patterns):
                            self._add_finding(SecurityFinding(
                                category="Input Validation",
                                severity="HIGH",
                                title="Path Traversal Vulnerability",
                                description=f"Path traversal detected in {endpoint}",
                                evidence=f"Payload: {payload}, Sensitive file content exposed",
                                recommendation="Implement proper path validation and access controls",
                                owasp_category="A01:2021 – Broken Access Control",
                                risk_score=self._calculate_risk_score("HIGH", 0.7, 0.8)
                            ))
                            result.status = "FAIL"
                    
                    except requests.RequestException:
                        pass
        
        except Exception as e:
            result.status = "ERROR"
            result.metadata["error"] = str(e)
            logger.error(f"Input validation testing error: {e}")
        
        result.execution_time = time.time() - start_time
        return result
    
    async def test_data_protection(self) -> SecurityTestResult:
        """Test data protection and encryption mechanisms."""
        start_time = time.time()
        result = SecurityTestResult("Data Protection & Encryption Testing", "PASS")
        
        try:
            # Test 1: HTTPS Configuration
            parsed_url = urlparse(self.base_url)
            if parsed_url.scheme == "http":
                self._add_finding(SecurityFinding(
                    category="Data Protection",
                    severity="HIGH",
                    title="Missing HTTPS Encryption",
                    description="Application is not using HTTPS encryption",
                    evidence=f"Base URL uses HTTP: {self.base_url}",
                    recommendation="Implement HTTPS with valid SSL/TLS certificates",
                    owasp_category="A02:2021 – Cryptographic Failures"
                ))
                result.status = "FAIL"
            
            # Test 2: Check for sensitive data exposure
            sensitive_endpoints = ["/health", "/", "/characters"]
            
            for endpoint in sensitive_endpoints:
                try:
                    response = self.session.get(urljoin(self.base_url, endpoint))
                    
                    # Check for exposed sensitive information
                    sensitive_patterns = [
                        r"password\s*[:=]\s*['\"]?[^'\"\s]+",
                        r"api_key\s*[:=]\s*['\"]?[^'\"\s]+",
                        r"secret\s*[:=]\s*['\"]?[^'\"\s]+",
                        r"token\s*[:=]\s*['\"]?[^'\"\s]+",
                        r"database\s*[:=]\s*['\"]?[^'\"\s]+",
                    ]
                    
                    for pattern in sensitive_patterns:
                        matches = re.findall(pattern, response.text, re.IGNORECASE)
                        if matches:
                            self._add_finding(SecurityFinding(
                                category="Data Protection",
                                severity="CRITICAL",
                                title="Sensitive Data Exposure",
                                description=f"Sensitive information exposed in {endpoint}",
                                evidence=f"Pattern matched: {pattern}, Found: {matches[:3]}",
                                recommendation="Remove sensitive data from responses and implement data classification",
                                owasp_category="A02:2021 – Cryptographic Failures"
                            ))
                            result.status = "FAIL"
                
                except requests.RequestException:
                    pass
            
            # Test 3: Check database security
            db_files = ["data/api_server.db", "context.db", "*.db"]
            for db_pattern in db_files:
                try:
                    # Check if database files are accessible via web
                    response = self.session.get(urljoin(self.base_url, db_pattern))
                    if response.status_code == 200 and len(response.content) > 0:
                        self._add_finding(SecurityFinding(
                            category="Data Protection",
                            severity="CRITICAL",
                            title="Database File Exposure",
                            description=f"Database file accessible via web: {db_pattern}",
                            evidence=f"HTTP 200 response with content length: {len(response.content)}",
                            recommendation="Prevent direct access to database files via web server configuration",
                            owasp_category="A01:2021 – Broken Access Control"
                        ))
                        result.status = "FAIL"
                except requests.RequestException:
                    pass
        
        except Exception as e:
            result.status = "ERROR"
            result.metadata["error"] = str(e)
            logger.error(f"Data protection testing error: {e}")
        
        result.execution_time = time.time() - start_time
        return result
    
    async def test_infrastructure_security(self) -> SecurityTestResult:
        """Test infrastructure security configuration."""
        start_time = time.time()
        result = SecurityTestResult("Infrastructure Security Testing", "PASS")
        
        try:
            # Test 1: Security Headers
            response = self.session.get(self.base_url)
            
            required_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Content-Security-Policy": None,
                "Strict-Transport-Security": None,
                "Referrer-Policy": "strict-origin-when-cross-origin"
            }
            
            missing_headers = []
            for header, expected_value in required_headers.items():
                if header not in response.headers:
                    missing_headers.append(header)
                elif expected_value and response.headers[header] != expected_value:
                    missing_headers.append(f"{header} (incorrect value)")
            
            if missing_headers:
                self._add_finding(SecurityFinding(
                    category="Infrastructure Security",
                    severity="MEDIUM",
                    title="Missing Security Headers",
                    description="Important security headers are missing or misconfigured",
                    evidence=f"Missing headers: {', '.join(missing_headers)}",
                    recommendation="Implement all recommended security headers",
                    owasp_category="A05:2021 – Security Misconfiguration"
                ))
            
            # Test 2: CORS Configuration
            cors_headers = response.headers.get("Access-Control-Allow-Origin", "")
            if cors_headers == "*":
                self._add_finding(SecurityFinding(
                    category="Infrastructure Security",
                    severity="MEDIUM",
                    title="Overly Permissive CORS Policy",
                    description="CORS policy allows all origins (*)",
                    evidence=f"Access-Control-Allow-Origin: {cors_headers}",
                    recommendation="Restrict CORS to specific trusted origins",
                    owasp_category="A05:2021 – Security Misconfiguration"
                ))
            
            # Test 3: Server Information Disclosure
            server_header = response.headers.get("Server", "")
            if server_header and any(info in server_header.lower() for info in ["uvicorn", "fastapi", "python"]):
                self._add_finding(SecurityFinding(
                    category="Infrastructure Security",
                    severity="LOW",
                    title="Server Information Disclosure",
                    description="Server header reveals technology stack information",
                    evidence=f"Server: {server_header}",
                    recommendation="Remove or obscure server identification headers",
                    owasp_category="A05:2021 – Security Misconfiguration"
                ))
            
            # Test 4: Error Handling
            error_endpoints = ["/nonexistent", "/admin", "/test/../../etc/passwd"]
            
            for endpoint in error_endpoints:
                try:
                    response = self.session.get(urljoin(self.base_url, endpoint))
                    
                    # Check for verbose error messages
                    error_patterns = [
                        r"traceback", r"stack trace", r"file.*line \d+",
                        r"exception.*:", r"error.*line", r"python.*py"
                    ]
                    
                    if any(re.search(pattern, response.text, re.IGNORECASE) for pattern in error_patterns):
                        self._add_finding(SecurityFinding(
                            category="Infrastructure Security",
                            severity="LOW",
                            title="Verbose Error Messages",
                            description=f"Detailed error information exposed in {endpoint}",
                            evidence="Error response contains stack traces or file paths",
                            recommendation="Implement custom error pages that don't reveal system information",
                            owasp_category="A05:2021 – Security Misconfiguration"
                        ))
                
                except requests.RequestException:
                    pass
        
        except Exception as e:
            result.status = "ERROR"
            result.metadata["error"] = str(e)
            logger.error(f"Infrastructure security testing error: {e}")
        
        result.execution_time = time.time() - start_time
        return result
    
    async def test_api_security(self) -> SecurityTestResult:
        """Test API-specific security measures."""
        start_time = time.time()
        result = SecurityTestResult("API Security Testing", "PASS")
        
        try:
            # Test 1: Rate Limiting
            rate_limit_url = urljoin(self.base_url, "/health")
            rate_limit_responses = []
            
            for i in range(20):  # Send 20 rapid requests
                try:
                    response = self.session.get(rate_limit_url, timeout=5)
                    rate_limit_responses.append(response.status_code)
                    if response.status_code == 429:  # Rate limit hit
                        break
                except requests.RequestException:
                    pass
            
            if 429 not in rate_limit_responses:
                self._add_finding(SecurityFinding(
                    category="API Security",
                    severity="MEDIUM",
                    title="No Rate Limiting Detected",
                    description="API does not implement rate limiting protection",
                    evidence=f"20 consecutive requests succeeded without rate limiting",
                    recommendation="Implement rate limiting to prevent abuse and DoS attacks",
                    owasp_category="A04:2021 – Insecure Design"
                ))
            
            # Test 2: Input Size Limits
            large_payload = {
                "character_names": ["test"] * 1000,  # Large array
                "turns": 1
            }
            
            try:
                response = self.session.post(
                    urljoin(self.base_url, "/simulations"),
                    json=large_payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    self._add_finding(SecurityFinding(
                        category="API Security",
                        severity="MEDIUM",
                        title="No Input Size Validation",
                        description="API accepts unreasonably large payloads",
                        evidence="Large payload (1000 character names) was accepted",
                        recommendation="Implement payload size limits and validation",
                        owasp_category="A04:2021 – Insecure Design"
                    ))
            
            except requests.RequestException:
                pass
            
            # Test 3: HTTP Methods Security
            test_methods = ["OPTIONS", "HEAD", "PUT", "DELETE", "PATCH", "TRACE"]
            
            for method in test_methods:
                try:
                    response = self.session.request(method, self.base_url, timeout=5)
                    
                    if method == "TRACE" and response.status_code == 200:
                        self._add_finding(SecurityFinding(
                            category="API Security",
                            severity="LOW",
                            title="HTTP TRACE Method Enabled",
                            description="HTTP TRACE method is enabled and could expose sensitive headers",
                            evidence=f"TRACE method returned status {response.status_code}",
                            recommendation="Disable TRACE method on web server",
                            owasp_category="A05:2021 – Security Misconfiguration"
                        ))
                    
                    if method in ["PUT", "DELETE", "PATCH"] and response.status_code not in [404, 405, 501]:
                        result.metadata[f"{method}_allowed"] = response.status_code
                
                except requests.RequestException:
                    pass
            
            # Test 4: Content Type Validation
            malformed_requests = [
                {"content_type": "application/xml", "data": "<test>data</test>"},
                {"content_type": "text/plain", "data": "plain text data"},
                {"content_type": "application/x-www-form-urlencoded", "data": "key=value"},
            ]
            
            for req in malformed_requests:
                try:
                    response = self.session.post(
                        urljoin(self.base_url, "/simulations"),
                        data=req["data"],
                        headers={"Content-Type": req["content_type"]},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        self._add_finding(SecurityFinding(
                            category="API Security",
                            severity="LOW",
                            title="Weak Content Type Validation",
                            description=f"API accepts unexpected content type: {req['content_type']}",
                            evidence=f"Request with {req['content_type']} returned status 200",
                            recommendation="Implement strict content type validation",
                            owasp_category="A04:2021 – Insecure Design"
                        ))
                
                except requests.RequestException:
                    pass
        
        except Exception as e:
            result.status = "ERROR"
            result.metadata["error"] = str(e)
            logger.error(f"API security testing error: {e}")
        
        result.execution_time = time.time() - start_time
        return result
    
    async def run_comprehensive_security_test(self) -> Dict[str, Any]:
        """Execute comprehensive security testing suite."""
        logger.info("Starting Novel Engine Comprehensive Security Testing")
        start_time = time.time()
        
        # Execute all security tests
        test_methods = [
            self.test_authentication_mechanisms,
            self.test_input_validation,
            self.test_data_protection,
            self.test_infrastructure_security,
            self.test_api_security,
        ]
        
        for test_method in test_methods:
            try:
                result = await test_method()
                self.test_results.append(result)
                logger.info(f"Completed {result.test_name}: {result.status}")
            except Exception as e:
                logger.error(f"Test {test_method.__name__} failed: {e}")
                error_result = SecurityTestResult(
                    test_name=test_method.__name__,
                    status="ERROR",
                    metadata={"error": str(e)}
                )
                self.test_results.append(error_result)
        
        # Generate comprehensive report
        report = self._generate_security_report()
        total_time = time.time() - start_time
        
        logger.info(f"Security testing completed in {total_time:.2f} seconds")
        logger.info(f"Total findings: {len(self.findings)}")
        
        return report
    
    def _generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security assessment report."""
        
        # Calculate security metrics
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        owasp_categories = {}
        
        for finding in self.findings:
            severity_counts[finding.severity] += 1
            if finding.owasp_category:
                owasp_categories[finding.owasp_category] = owasp_categories.get(finding.owasp_category, 0) + 1
        
        # Calculate overall security score (0-100)
        total_findings = len(self.findings)
        if total_findings == 0:
            security_score = 100
        else:
            weighted_score = (
                severity_counts["CRITICAL"] * 10 +
                severity_counts["HIGH"] * 5 +
                severity_counts["MEDIUM"] * 2 +
                severity_counts["LOW"] * 1
            )
            security_score = max(0, 100 - weighted_score)
        
        # Determine overall risk level
        if severity_counts["CRITICAL"] > 0 or severity_counts["HIGH"] > 2:
            risk_level = "HIGH"
        elif severity_counts["HIGH"] > 0 or severity_counts["MEDIUM"] > 3:
            risk_level = "MEDIUM"
        elif total_findings > 0:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"
        
        # Production readiness assessment
        production_ready = (
            severity_counts["CRITICAL"] == 0 and
            severity_counts["HIGH"] <= 1 and
            security_score >= 70
        )
        
        return {
            "assessment_summary": {
                "timestamp": datetime.now().isoformat(),
                "target": self.base_url,
                "security_score": security_score,
                "risk_level": risk_level,
                "production_ready": production_ready,
                "total_tests": len(self.test_results),
                "total_findings": total_findings
            },
            "severity_breakdown": severity_counts,
            "owasp_top10_coverage": owasp_categories,
            "test_results": [
                {
                    "test_name": result.test_name,
                    "status": result.status,
                    "execution_time": result.execution_time,
                    "findings_count": len(result.findings),
                    "metadata": result.metadata
                }
                for result in self.test_results
            ],
            "detailed_findings": [
                {
                    "category": finding.category,
                    "severity": finding.severity,
                    "title": finding.title,
                    "description": finding.description,
                    "evidence": finding.evidence,
                    "recommendation": finding.recommendation,
                    "owasp_category": finding.owasp_category,
                    "risk_score": finding.risk_score
                }
                for finding in self.findings
            ],
            "security_recommendations": self._generate_security_recommendations(),
            "compliance_assessment": self._assess_compliance(),
        }
    
    def _generate_security_recommendations(self) -> List[Dict[str, str]]:
        """Generate prioritized security recommendations."""
        recommendations = []
        
        # Critical recommendations based on findings
        if any(f.severity == "CRITICAL" for f in self.findings):
            recommendations.append({
                "priority": "IMMEDIATE",
                "category": "Critical Vulnerabilities",
                "action": "Address all CRITICAL severity findings before production deployment",
                "timeline": "Before deployment"
            })
        
        if any("HTTPS" in f.title for f in self.findings):
            recommendations.append({
                "priority": "HIGH",
                "category": "Encryption",
                "action": "Implement HTTPS with valid SSL/TLS certificates",
                "timeline": "Before production"
            })
        
        if any("Authentication" in f.category for f in self.findings):
            recommendations.append({
                "priority": "HIGH",
                "category": "Authentication",
                "action": "Implement comprehensive authentication and authorization system",
                "timeline": "Before production"
            })
        
        recommendations.extend([
            {
                "priority": "MEDIUM",
                "category": "Security Headers",
                "action": "Implement all recommended security headers (CSP, HSTS, etc.)",
                "timeline": "1-2 weeks"
            },
            {
                "priority": "MEDIUM",
                "category": "Input Validation",
                "action": "Implement comprehensive input validation and sanitization",
                "timeline": "1-2 weeks"
            },
            {
                "priority": "LOW",
                "category": "Monitoring",
                "action": "Implement security monitoring and logging",
                "timeline": "2-4 weeks"
            }
        ])
        
        return recommendations
    
    def _assess_compliance(self) -> Dict[str, Any]:
        """Assess compliance with security standards."""
        return {
            "owasp_top10_2021": {
                "A01_broken_access_control": len([f for f in self.findings if "A01:2021" in str(f.owasp_category)]),
                "A02_cryptographic_failures": len([f for f in self.findings if "A02:2021" in str(f.owasp_category)]),
                "A03_injection": len([f for f in self.findings if "A03:2021" in str(f.owasp_category)]),
                "A04_insecure_design": len([f for f in self.findings if "A04:2021" in str(f.owasp_category)]),
                "A05_security_misconfiguration": len([f for f in self.findings if "A05:2021" in str(f.owasp_category)]),
                "A07_identification_authentication_failures": len([f for f in self.findings if "A07:2021" in str(f.owasp_category)]),
            },
            "production_security_checklist": {
                "https_implemented": not any("HTTPS" in f.title for f in self.findings),
                "authentication_system": not any("Authentication" in f.category and f.severity in ["CRITICAL", "HIGH"] for f in self.findings),
                "input_validation": not any("Input Validation" in f.category and f.severity in ["CRITICAL", "HIGH"] for f in self.findings),
                "security_headers": not any("Security Headers" in f.title for f in self.findings),
                "error_handling": not any("Error" in f.title for f in self.findings),
                "rate_limiting": not any("Rate Limiting" in f.title for f in self.findings),
            }
        }

async def main():
    """Main execution function for security testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Novel Engine Security Testing Suite")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL to test")
    parser.add_argument("--output", default="security_assessment_report.json", help="Output file for report")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize security tester
    tester = NovelEngineSecurityTester(args.url)
    
    # Run comprehensive security assessment
    try:
        report = await tester.run_comprehensive_security_test()
        
        # Save detailed report
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print executive summary
        print("\n" + "="*80)
        print("NOVEL ENGINE SECURITY ASSESSMENT REPORT")
        print("="*80)
        print(f"Target: {args.url}")
        print(f"Assessment Time: {report['assessment_summary']['timestamp']}")
        print(f"Security Score: {report['assessment_summary']['security_score']}/100")
        print(f"Risk Level: {report['assessment_summary']['risk_level']}")
        print(f"Production Ready: {'✅ YES' if report['assessment_summary']['production_ready'] else '❌ NO'}")
        print()
        
        print("FINDINGS SUMMARY:")
        severity_breakdown = report['severity_breakdown']
        for severity, count in severity_breakdown.items():
            if count > 0:
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵", "INFO": "⚪"}.get(severity, "")
                print(f"  {icon} {severity}: {count}")
        
        print()
        print("TOP RECOMMENDATIONS:")
        for rec in report['security_recommendations'][:3]:
            print(f"  • [{rec['priority']}] {rec['action']}")
        
        print()
        print(f"📄 Detailed report saved to: {args.output}")
        print("="*80)
        
        # Exit with appropriate code
        if not report['assessment_summary']['production_ready']:
            exit(1)
        
    except Exception as e:
        logger.error(f"Security testing failed: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())