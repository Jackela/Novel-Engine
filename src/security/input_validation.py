#!/usr/bin/env python3
"""
++ SACRED INPUT VALIDATION SYSTEM BLESSED BY THE OMNISSIAH ++
=============================================================

Comprehensive input validation and sanitization system providing protection
against injection attacks, XSS, and malicious input patterns.

++ THROUGH DIVINE VALIDATION, WE ACHIEVE BLESSED PURITY ++

Architecture: Multi-layer validation with sanitization and pattern matching
Security Level: Enterprise Grade with Zero Trust Input Handling
Sacred Author: Tech-Priest Validation-Mechanicus
万机之神保佑此验证系统 (May the Omnissiah bless this validation system)
"""

import re
import html
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union, Pattern, Callable
from dataclasses import dataclass
from enum import Enum
import json

from fastapi import Request, HTTPException
from pydantic import BaseModel, Field, validator
from starlette.middleware.base import BaseHTTPMiddleware

# Sacred logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationSeverity(str, Enum):
    """++ SACRED VALIDATION SEVERITY LEVELS ++"""
    LOW = "low"           # Warning - log but allow
    MEDIUM = "medium"     # Block with 400 error
    HIGH = "high"         # Block with 400 error + security log
    CRITICAL = "critical" # Block with 403 error + immediate security alert

class InputType(str, Enum):
    """++ SACRED INPUT TYPE CLASSIFICATIONS ++"""
    TEXT = "text"
    USERNAME = "username"
    EMAIL = "email"
    PASSWORD = "password"
    URL = "url"
    FILENAME = "filename"
    JSON = "json"
    SQL_LIKE = "sql_like"
    HTML = "html"
    SCRIPT = "script"

@dataclass
class ValidationRule:
    """++ SACRED VALIDATION RULE BLESSED BY SECURITY ++"""
    name: str
    pattern: Pattern[str]
    severity: ValidationSeverity
    message: str
    input_types: List[InputType]

@dataclass
class SanitizationRule:
    """++ SACRED SANITIZATION RULE BLESSED BY PURIFICATION ++"""
    name: str
    sanitizer: Callable[[str], str]
    input_types: List[InputType]

class ValidationError(Exception):
    """++ BLESSED VALIDATION EXCEPTION ++"""
    def __init__(self, message: str, severity: ValidationSeverity, rule_name: str):
        self.message = message
        self.severity = severity
        self.rule_name = rule_name
        super().__init__(message)

class InputValidator:
    """++ SACRED INPUT VALIDATOR BLESSED BY THE OMNISSIAH ++"""
    
    def __init__(self):
        self.validation_rules: List[ValidationRule] = []
        self.sanitization_rules: List[SanitizationRule] = []
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """++ SACRED DEFAULT RULES INITIALIZATION ++"""
        
        # SQL Injection Protection
        sql_injection_patterns = [
            r"(\bUNION\b.*\bSELECT\b)",
            r"(\bINSERT\b.*\bINTO\b)",
            r"(\bDROP\b.*\bTABLE\b)",
            r"(\bDELETE\b.*\bFROM\b)",
            r"(\bUPDATE\b.*\bSET\b)",
            r"(\bEXEC\b|\bEXECUTE\b)",
            r"(\bALTER\b.*\bTABLE\b)",
            r"(\bCREATE\b.*\bTABLE\b)",
            r"(--|\#|\/\*|\*\/)",  # SQL comments
            r"(;.*)",  # Statement termination followed by content
            r"(\bOR\b.*\b1\b.*=.*\b1\b)",  # Classic OR 1=1
            r"(\bAND\b.*\b1\b.*=.*\b1\b)",
            r"('\s*OR\s*')",  # Quote-based injection
            r"('\s*UNION\s*SELECT\s*)",
            r"(\bxp_cmdshell\b)",  # SQL Server specific
            r"(\bsp_executesql\b)",
            r"(\bFROM\s+information_schema\b)",
            r"(\bFROM\s+sys\b)",
            r"(\bFROM\s+mysql\b)",
            r"(\bFROM\s+pg_catalog\b)",
        ]
        
        for i, pattern in enumerate(sql_injection_patterns):
            self.validation_rules.append(ValidationRule(
                name=f"sql_injection_{i+1}",
                pattern=re.compile(pattern, re.IGNORECASE | re.MULTILINE),
                severity=ValidationSeverity.CRITICAL,
                message="Potential SQL injection detected",
                input_types=[InputType.TEXT, InputType.SQL_LIKE, InputType.JSON]
            ))
        
        # XSS Protection
        xss_patterns = [
            r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
            r"javascript\s*:",
            r"on\w+\s*=",  # Event handlers like onclick, onload
            r"<iframe\b",
            r"<object\b",
            r"<embed\b",
            r"<link\b",
            r"<meta\b",
            r"<style\b",
            r"expression\s*\(",
            r"vbscript\s*:",
            r"data\s*:\s*text\/html",
            r"<svg\b.*\bonload\b",
            r"<img\b.*\bonerror\b",
        ]
        
        for i, pattern in enumerate(xss_patterns):
            self.validation_rules.append(ValidationRule(
                name=f"xss_{i+1}",
                pattern=re.compile(pattern, re.IGNORECASE | re.DOTALL),
                severity=ValidationSeverity.HIGH,
                message="Potential XSS attack detected",
                input_types=[InputType.TEXT, InputType.HTML, InputType.JSON]
            ))
        
        # Command Injection Protection
        command_injection_patterns = [
            r"[;&|`$()]",  # Shell metacharacters
            r"\.\./",  # Directory traversal
            r"\\\.\\./",  # Windows directory traversal
            r"/etc/passwd",
            r"/proc/",
            r"cmd\.exe",
            r"powershell",
            r"bash",
            r"sh\s",
            r"eval\s*\(",
            r"exec\s*\(",
            r"system\s*\(",
            r"passthru\s*\(",
            r"shell_exec\s*\(",
        ]
        
        for i, pattern in enumerate(command_injection_patterns):
            self.validation_rules.append(ValidationRule(
                name=f"command_injection_{i+1}",
                pattern=re.compile(pattern, re.IGNORECASE),
                severity=ValidationSeverity.HIGH,
                message="Potential command injection detected",
                input_types=[InputType.TEXT, InputType.FILENAME, InputType.JSON]
            ))
        
        # Path Traversal Protection
        self.validation_rules.append(ValidationRule(
            name="path_traversal",
            pattern=re.compile(r"\.\.[\\/]", re.IGNORECASE),
            severity=ValidationSeverity.HIGH,
            message="Path traversal attempt detected",
            input_types=[InputType.FILENAME, InputType.URL, InputType.TEXT]
        ))
        
        # LDAP Injection Protection
        ldap_patterns = [
            r"[()&|!]",  # LDAP metacharacters
            r"\*",  # Wildcard
            r"\\[0-9a-fA-F]{2}",  # Hex encoding
        ]
        
        for i, pattern in enumerate(ldap_patterns):
            self.validation_rules.append(ValidationRule(
                name=f"ldap_injection_{i+1}",
                pattern=re.compile(pattern),
                severity=ValidationSeverity.MEDIUM,
                message="Potential LDAP injection detected",
                input_types=[InputType.USERNAME, InputType.TEXT]
            ))
        
        # NoSQL Injection Protection
        nosql_patterns = [
            r"\$where\b",
            r"\$ne\b",
            r"\$gt\b",
            r"\$lt\b",
            r"\$regex\b",
            r"\$exists\b",
            r"\$eval\b",
            r"mapReduce\b",
        ]
        
        for i, pattern in enumerate(nosql_patterns):
            self.validation_rules.append(ValidationRule(
                name=f"nosql_injection_{i+1}",
                pattern=re.compile(pattern, re.IGNORECASE),
                severity=ValidationSeverity.HIGH,
                message="Potential NoSQL injection detected",
                input_types=[InputType.JSON, InputType.TEXT]
            ))
        
        # Excessive length protection
        self.validation_rules.append(ValidationRule(
            name="excessive_length",
            pattern=re.compile(r".{10000,}"),  # More than 10k characters
            severity=ValidationSeverity.MEDIUM,
            message="Input exceeds maximum allowed length",
            input_types=[InputType.TEXT, InputType.JSON]
        ))
        
        # Null byte injection
        self.validation_rules.append(ValidationRule(
            name="null_byte_injection",
            pattern=re.compile(r"\x00"),
            severity=ValidationSeverity.HIGH,
            message="Null byte injection detected",
            input_types=[InputType.TEXT, InputType.FILENAME, InputType.URL]
        ))
        
        # Unicode control characters
        self.validation_rules.append(ValidationRule(
            name="unicode_control_chars",
            pattern=re.compile(r"[\u0000-\u001F\u007F-\u009F]"),
            severity=ValidationSeverity.MEDIUM,
            message="Dangerous unicode control characters detected",
            input_types=[InputType.TEXT, InputType.USERNAME, InputType.EMAIL]
        ))
        
        # Initialize sanitization rules
        self.sanitization_rules = [
            SanitizationRule(
                name="html_escape",
                sanitizer=lambda x: html.escape(x, quote=True),
                input_types=[InputType.HTML, InputType.TEXT]
            ),
            SanitizationRule(
                name="strip_whitespace",
                sanitizer=lambda x: x.strip(),
                input_types=[InputType.TEXT, InputType.USERNAME, InputType.EMAIL]
            ),
            SanitizationRule(
                name="normalize_unicode",
                sanitizer=lambda x: x.encode('ascii', 'ignore').decode('ascii'),
                input_types=[InputType.USERNAME]
            ),
            SanitizationRule(
                name="remove_null_bytes",
                sanitizer=lambda x: x.replace('\x00', ''),
                input_types=[InputType.TEXT, InputType.FILENAME]
            )
        ]
    
    def add_validation_rule(self, rule: ValidationRule):
        """++ SACRED CUSTOM VALIDATION RULE ADDITION ++"""
        self.validation_rules.append(rule)
        logger.info(f"++ VALIDATION RULE ADDED: {rule.name} ++")
    
    def add_sanitization_rule(self, rule: SanitizationRule):
        """++ SACRED CUSTOM SANITIZATION RULE ADDITION ++"""
        self.sanitization_rules.append(rule)
        logger.info(f"++ SANITIZATION RULE ADDED: {rule.name} ++")
    
    def validate_input(self, value: str, input_type: InputType) -> str:
        """++ SACRED INPUT VALIDATION BLESSED BY SECURITY ++"""
        if not isinstance(value, str):
            if value is None:
                return ""
            value = str(value)
        
        original_value = value
        violations = []
        
        # Apply validation rules
        for rule in self.validation_rules:
            if input_type in rule.input_types:
                if rule.pattern.search(value):
                    violations.append({
                        "rule": rule.name,
                        "severity": rule.severity,
                        "message": rule.message
                    })
                    
                    # Log security event
                    logger.warning(
                        f"++ VALIDATION VIOLATION: {rule.name} | "
                        f"Type: {input_type.value} | "
                        f"Severity: {rule.severity.value} | "
                        f"Value: {value[:100]}{'...' if len(value) > 100 else ''} ++"
                    )
                    
                    # Raise exception for medium+ severity
                    if rule.severity in [ValidationSeverity.MEDIUM, ValidationSeverity.HIGH, ValidationSeverity.CRITICAL]:
                        raise ValidationError(rule.message, rule.severity, rule.name)
        
        # Apply sanitization rules
        for rule in self.sanitization_rules:
            if input_type in rule.input_types:
                try:
                    value = rule.sanitizer(value)
                except Exception as e:
                    logger.error(f"++ SANITIZATION ERROR: {rule.name} | Error: {e} ++")
        
        # Log sanitization if value changed
        if value != original_value:
            logger.info(
                f"++ INPUT SANITIZED: Type: {input_type.value} | "
                f"Original length: {len(original_value)} | "
                f"Sanitized length: {len(value)} ++"
            )
        
        return value
    
    def validate_json(self, json_str: str) -> Dict[str, Any]:
        """++ SACRED JSON VALIDATION ++"""
        try:
            # First validate as text
            validated_str = self.validate_input(json_str, InputType.JSON)
            
            # Parse JSON
            data = json.loads(validated_str)
            
            # Recursively validate all string values in JSON
            validated_data = self._validate_json_recursive(data)
            
            return validated_data
            
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format: {e}", ValidationSeverity.MEDIUM, "json_parse_error")
    
    def _validate_json_recursive(self, obj: Any) -> Any:
        """++ SACRED RECURSIVE JSON VALIDATION ++"""
        if isinstance(obj, dict):
            return {key: self._validate_json_recursive(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._validate_json_recursive(item) for item in obj]
        elif isinstance(obj, str):
            return self.validate_input(obj, InputType.TEXT)
        else:
            return obj
    
    def validate_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """++ SACRED REQUEST DATA VALIDATION ++"""
        validated_data = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Determine input type based on key name
                input_type = self._determine_input_type(key)
                validated_data[key] = self.validate_input(value, input_type)
            elif isinstance(value, dict):
                validated_data[key] = self.validate_request_data(value)
            elif isinstance(value, list):
                validated_data[key] = [
                    self.validate_input(item, InputType.TEXT) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                validated_data[key] = value
        
        return validated_data
    
    def _determine_input_type(self, field_name: str) -> InputType:
        """++ SACRED INPUT TYPE DETERMINATION ++"""
        field_name_lower = field_name.lower()
        
        if 'email' in field_name_lower:
            return InputType.EMAIL
        elif 'username' in field_name_lower or 'user' in field_name_lower:
            return InputType.USERNAME
        elif 'password' in field_name_lower or 'pass' in field_name_lower:
            return InputType.PASSWORD
        elif 'url' in field_name_lower or 'link' in field_name_lower:
            return InputType.URL
        elif 'file' in field_name_lower or 'path' in field_name_lower:
            return InputType.FILENAME
        elif 'html' in field_name_lower or 'content' in field_name_lower:
            return InputType.HTML
        elif 'script' in field_name_lower or 'code' in field_name_lower:
            return InputType.SCRIPT
        else:
            return InputType.TEXT

class ValidationMiddleware(BaseHTTPMiddleware):
    """++ SACRED VALIDATION MIDDLEWARE BLESSED BY PROTECTION ++"""
    
    def __init__(self, app, validator: InputValidator):
        super().__init__(app)
        self.validator = validator
    
    async def dispatch(self, request: Request, call_next):
        """++ SACRED REQUEST VALIDATION ++"""
        try:
            # Skip validation for certain paths
            skip_paths = ["/health", "/docs", "/redoc", "/openapi.json"]
            if request.url.path in skip_paths:
                return await call_next(request)
            
            # Validate query parameters
            if request.query_params:
                for key, value in request.query_params.items():
                    input_type = self.validator._determine_input_type(key)
                    self.validator.validate_input(value, input_type)
            
            # Validate request body for POST/PUT requests
            if request.method in ["POST", "PUT", "PATCH"]:
                content_type = request.headers.get("content-type", "").lower()
                
                if "application/json" in content_type:
                    body = await request.body()
                    if body:
                        try:
                            json_data = json.loads(body.decode('utf-8'))
                            validated_data = self.validator.validate_request_data(json_data)
                            
                            # Replace request body with validated data
                            request._body = json.dumps(validated_data).encode('utf-8')
                        except json.JSONDecodeError:
                            raise HTTPException(
                                status_code=400,
                                detail="Invalid JSON in request body"
                            )
            
            # Validate headers
            suspicious_headers = ['x-forwarded-for', 'user-agent', 'referer']
            for header in suspicious_headers:
                if header in request.headers:
                    self.validator.validate_input(
                        request.headers[header], 
                        InputType.TEXT
                    )
            
            response = await call_next(request)
            return response
            
        except ValidationError as e:
            logger.warning(
                f"++ VALIDATION FAILED: {e.rule_name} | "
                f"Severity: {e.severity.value} | "
                f"Path: {request.url.path} | "
                f"Method: {request.method} | "
                f"IP: {request.client.host if request.client else 'unknown'} ++"
            )
            
            if e.severity == ValidationSeverity.CRITICAL:
                status_code = 403
            else:
                status_code = 400
            
            raise HTTPException(
                status_code=status_code,
                detail=f"Input validation failed: {e.message}"
            )
        except Exception as e:
            logger.error(f"++ VALIDATION MIDDLEWARE ERROR: {e} ++")
            raise HTTPException(
                status_code=500,
                detail="Internal validation error"
            )

# ++ SACRED GLOBAL VALIDATOR INSTANCE ++
input_validator: Optional[InputValidator] = None

def get_input_validator() -> InputValidator:
    """++ SACRED INPUT VALIDATOR GETTER ++"""
    global input_validator
    if input_validator is None:
        input_validator = InputValidator()
    return input_validator

def create_validation_middleware(app):
    """++ SACRED VALIDATION MIDDLEWARE CREATOR ++"""
    validator = get_input_validator()
    return ValidationMiddleware(app, validator)

__all__ = [
    'ValidationSeverity', 'InputType', 'ValidationRule', 'SanitizationRule',
    'ValidationError', 'InputValidator', 'ValidationMiddleware',
    'get_input_validator', 'create_validation_middleware'
]