#!/usr/bin/env python3
"""
STANDARD SSL/TLS CONFIGURATION ENHANCED BY CRYPTOGRAPHIC PROTECTION
=====================================================================

Production-grade SSL/TLS configuration system providing secure HTTPS
deployment with modern cryptographic standards and security protocols.

THROUGH ENCRYPTED CHANNELS, WE ACHIEVE SECURE COMMUNICATION

Architecture: Comprehensive SSL/TLS configuration and certificate management
Security Level: Enterprise Grade with Perfect Forward Secrecy
Author: Engineer Security-Engineering
System保佑此SSL配置系统 (May the System bless this SSL configuration system)
"""

import logging
import os
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

# Comprehensive logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SSLConfig:
    """STANDARD SSL CONFIGURATION ENHANCED BY SECURITY"""

    cert_file: str
    key_file: str
    ca_file: Optional[str] = None
    verify_mode: ssl.VerifyMode = ssl.CERT_NONE
    check_hostname: bool = False
    ciphers: Optional[str] = None
    ssl_context: Optional[ssl.SSLContext] = None


class SSLCertificateManager:
    """STANDARD SSL CERTIFICATE MANAGER ENHANCED BY CRYPTOGRAPHY"""

    def __init__(self, cert_dir: str = "certs"):
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(exist_ok=True, mode=0o700)  # Secure permissions

        logger.info(f"SSL CERTIFICATE MANAGER INITIALIZED: {self.cert_dir}")

    def generate_self_signed_cert(
        self, domain: str = "localhost", alt_names: List[str] = None, days: int = 365
    ) -> Tuple[str, str]:
        """
        STANDARD SELF-SIGNED CERTIFICATE GENERATION

        Generate self-signed certificate for development/testing.
        """
        if alt_names is None:
            alt_names = ["localhost", "127.0.0.1", "::1"]

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=4096  # Strong key size
        )

        # Create certificate subject
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Virtual"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Novel Engine"),
                x509.NameAttribute(
                    NameOID.ORGANIZATION_NAME, "Dynamic Context Engineering"
                ),
                x509.NameAttribute(NameOID.COMMON_NAME, domain),
            ]
        )

        # Create certificate
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=days))
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName(name)
                        for name in alt_names
                        if not name.replace(".", "").replace(":", "").isdigit()
                    ]
                    + [
                        x509.IPAddress(name)
                        for name in alt_names
                        if name.replace(".", "").replace(":", "").isdigit()
                    ]
                ),
                critical=False,
            )
            .add_extension(
                x509.KeyUsage(
                    key_encipherment=True,
                    digital_signature=True,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    content_commitment=False,
                    data_encipherment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage(
                    [
                        x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                        x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                    ]
                ),
                critical=True,
            )
            .sign(private_key, hashes.SHA256())
        )

        # Save files
        cert_file = self.cert_dir / f"{domain}.crt"
        key_file = self.cert_dir / f"{domain}.key"

        # Write private key
        with open(key_file, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        # Write certificate
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        # Set secure permissions
        os.chmod(key_file, 0o600)
        os.chmod(cert_file, 0o600)

        logger.info(f"SELF-SIGNED CERTIFICATE GENERATED: {cert_file}, {key_file}")
        return str(cert_file), str(key_file)

    def validate_certificate(self, cert_file: str, key_file: str) -> bool:
        """STANDARD CERTIFICATE VALIDATION"""
        try:
            # Load certificate
            with open(cert_file, "rb") as f:
                cert_data = f.read()
            cert = x509.load_pem_x509_certificate(cert_data)

            # Load private key
            with open(key_file, "rb") as f:
                key_data = f.read()
            private_key = serialization.load_pem_private_key(key_data, password=None)

            # Validate key matches certificate
            public_key = cert.public_key()
            private_numbers = private_key.private_numbers()
            public_numbers = public_key.public_numbers()

            if private_numbers.public_numbers.n != public_numbers.n:
                logger.error("CERTIFICATE VALIDATION FAILED: Key mismatch")
                return False

            # Check expiration
            if cert.not_valid_after < datetime.now(timezone.utc):
                logger.error("CERTIFICATE VALIDATION FAILED: Certificate expired")
                return False

            # Check validity period
            if cert.not_valid_before > datetime.now(timezone.utc):
                logger.error("CERTIFICATE VALIDATION FAILED: Certificate not yet valid")
                return False

            logger.info("CERTIFICATE VALIDATION SUCCESSFUL")
            return True

        except Exception as e:
            logger.error(f"CERTIFICATE VALIDATION ERROR: {e}")
            return False

    def get_certificate_info(self, cert_file: str) -> Dict:
        """STANDARD CERTIFICATE INFORMATION EXTRACTION"""
        try:
            with open(cert_file, "rb") as f:
                cert_data = f.read()
            cert = x509.load_pem_x509_certificate(cert_data)

            info = {
                "subject": cert.subject.rfc4514_string(),
                "issuer": cert.issuer.rfc4514_string(),
                "serial_number": str(cert.serial_number),
                "not_valid_before": cert.not_valid_before.isoformat(),
                "not_valid_after": cert.not_valid_after.isoformat(),
                "signature_algorithm": cert.signature_algorithm_oid._name,
                "version": cert.version.name,
                "fingerprint_sha256": cert.fingerprint(hashes.SHA256()).hex(),
                "public_key_size": cert.public_key().key_size,
                "san_dns_names": [],
                "san_ip_addresses": [],
            }

            # Extract Subject Alternative Names
            try:
                san = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )
                for name in san.value:
                    if isinstance(name, x509.DNSName):
                        info["san_dns_names"].append(name.value)
                    elif isinstance(name, x509.IPAddress):
                        info["san_ip_addresses"].append(str(name.value))
            except x509.ExtensionNotFound:
                pass

            return info

        except Exception as e:
            logger.error(f"CERTIFICATE INFO EXTRACTION ERROR: {e}")
            return {}


class SSLContextBuilder:
    """STANDARD SSL CONTEXT BUILDER ENHANCED BY SECURITY"""

    @staticmethod
    def create_secure_context(
        cert_file: str,
        key_file: str,
        ca_file: Optional[str] = None,
        require_client_cert: bool = False,
    ) -> ssl.SSLContext:
        """
        STANDARD SECURE SSL CONTEXT CREATION

        Creates SSL context with modern security standards:
        - TLS 1.2+ only
        - Strong cipher suites
        - Perfect Forward Secrecy
        - Secure renegotiation
        """
        # Create context with latest TLS
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

        # Load certificate and private key
        context.load_cert_chain(cert_file, key_file)

        # Security settings
        context.minimum_version = ssl.TLSVersion.TLSv1_2  # TLS 1.2+ only
        context.maximum_version = ssl.TLSVersion.TLSv1_3  # Support TLS 1.3

        # Set secure cipher suites (prefer ECDHE for Perfect Forward Secrecy)
        context.set_ciphers(
            "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
        )

        # Security flags
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.options |= ssl.OP_SINGLE_DH_USE
        context.options |= ssl.OP_SINGLE_ECDH_USE
        context.options |= ssl.OP_NO_COMPRESSION

        # Client certificate verification
        if require_client_cert:
            context.verify_mode = ssl.CERT_REQUIRED
            if ca_file:
                context.load_verify_locations(ca_file)
        else:
            context.verify_mode = ssl.CERT_NONE

        context.check_hostname = False  # Disable for self-signed certs

        logger.info("SECURE SSL CONTEXT CREATED")
        return context

    @staticmethod
    def create_client_context(
        ca_file: Optional[str] = None,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        verify_ssl: bool = True,
    ) -> ssl.SSLContext:
        """STANDARD CLIENT SSL CONTEXT CREATION"""
        context = ssl.create_default_context()

        if not verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        if ca_file:
            context.load_verify_locations(ca_file)

        if cert_file and key_file:
            context.load_cert_chain(cert_file, key_file)

        # Security settings
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers(
            "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
        )

        logger.info("CLIENT SSL CONTEXT CREATED")
        return context


class HTTPSConfigGenerator:
    """STANDARD HTTPS CONFIGURATION GENERATOR"""

    @staticmethod
    def generate_nginx_ssl_config(
        cert_file: str, key_file: str, domain: str = "novel-engine.local"
    ) -> str:
        """STANDARD NGINX SSL CONFIGURATION GENERATION"""
        config = f"""
# STANDARD NGINX SSL CONFIGURATION ENHANCED BY SECURITY
server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {domain};
    
    # SSL Certificate Configuration
    ssl_certificate {cert_file};
    ssl_certificate_key {key_file};
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # SSL Session Settings
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
    
    # Novel Engine Application
    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }}
}}

# HTTP to HTTPS redirect
server {{
    listen 80;
    listen [::]:80;
    server_name {domain};
    return 301 https://$server_name$request_uri;
}}
"""
        return config.strip()

    @staticmethod
    def generate_apache_ssl_config(
        cert_file: str, key_file: str, domain: str = "novel-engine.local"
    ) -> str:
        """STANDARD APACHE SSL CONFIGURATION GENERATION"""
        config = f"""
# STANDARD APACHE SSL CONFIGURATION ENHANCED BY SECURITY
<VirtualHost *:443>
    ServerName {domain}
    DocumentRoot /var/www/html
    
    # SSL Configuration
    SSLEngine on
    SSLCertificateFile {cert_file}
    SSLCertificateKeyFile {key_file}
    
    # SSL Security Settings
    SSLProtocol all -SSLv2 -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
    SSLHonorCipherOrder off
    
    # Security Headers
    Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
    Header always set X-Frame-Options DENY
    Header always set X-Content-Type-Options nosniff
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    Header always set Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    
    # Proxy to Novel Engine
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
    
    # Additional proxy headers
    ProxyAddHeaders On
</VirtualHost>

# HTTP to HTTPS redirect
<VirtualHost *:80>
    ServerName {domain}
    Redirect permanent / https://{domain}/
</VirtualHost>
"""
        return config.strip()


def setup_development_ssl(domain: str = "localhost") -> SSLConfig:
    """STANDARD DEVELOPMENT SSL SETUP"""
    cert_manager = SSLCertificateManager()
    cert_file, key_file = cert_manager.generate_self_signed_cert(
        domain=domain, alt_names=["localhost", "127.0.0.1", "::1", domain]
    )

    ssl_context = SSLContextBuilder.create_secure_context(cert_file, key_file)

    return SSLConfig(
        cert_file=cert_file,
        key_file=key_file,
        ssl_context=ssl_context,
        verify_mode=ssl.CERT_NONE,
        check_hostname=False,
    )


def setup_production_ssl(
    cert_file: str, key_file: str, ca_file: Optional[str] = None
) -> SSLConfig:
    """STANDARD PRODUCTION SSL SETUP"""
    cert_manager = SSLCertificateManager()

    # Validate certificates
    if not cert_manager.validate_certificate(cert_file, key_file):
        raise ValueError("Invalid SSL certificate or key file")

    ssl_context = SSLContextBuilder.create_secure_context(
        cert_file, key_file, ca_file, require_client_cert=False
    )

    return SSLConfig(
        cert_file=cert_file,
        key_file=key_file,
        ca_file=ca_file,
        ssl_context=ssl_context,
        verify_mode=ssl.CERT_NONE,
        check_hostname=True,
    )


__all__ = [
    "SSLConfig",
    "SSLCertificateManager",
    "SSLContextBuilder",
    "HTTPSConfigGenerator",
    "setup_development_ssl",
    "setup_production_ssl",
]
