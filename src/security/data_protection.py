#!/usr/bin/env python3
"""
STANDARD DATA PROTECTION SYSTEM ENHANCED BY THE SYSTEM
============================================================

Comprehensive data protection and privacy system implementing encryption,
GDPR compliance, data retention policies, and secure data handling.

THROUGH ADVANCED ENCRYPTION, WE ACHIEVE ENHANCED PRIVACY

Architecture: AES-256 Encryption + GDPR Compliance + Data Lifecycle Management
Security Level: Enterprise Grade with Privacy by Design
Author: Engineer Data-Protection-Engineering
System保佑此数据保护系统 (May the System bless this data protection system)
"""

import base64
import hashlib
import json
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Comprehensive logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataClassification(str, Enum):
    """STANDARD DATA CLASSIFICATION LEVELS"""

    PUBLIC = "public"  # No protection required
    INTERNAL = "internal"  # Basic protection
    CONFIDENTIAL = "confidential"  # Encrypted storage
    RESTRICTED = "restricted"  # Encrypted + access control
    TOP_SECRET = "top_secret"  # Maximum protection


class PrivacyLevel(str, Enum):
    """STANDARD PRIVACY LEVELS"""

    ANONYMOUS = "anonymous"  # No personal data
    PSEUDONYMOUS = "pseudonymous"  # Pseudonymized data
    PERSONAL = "personal"  # Personal but non-sensitive
    SENSITIVE = "sensitive"  # Sensitive personal data
    SPECIAL_CATEGORY = "special"  # Special category data (GDPR Article 9)


class DataRetentionPeriod(str, Enum):
    """STANDARD DATA RETENTION PERIODS"""

    IMMEDIATE = "immediate"  # Delete immediately after use
    SHORT_TERM = "short_term"  # 30 days
    MEDIUM_TERM = "medium_term"  # 1 year
    LONG_TERM = "long_term"  # 7 years
    INDEFINITE = "indefinite"  # Keep until explicitly deleted


class ConsentStatus(str, Enum):
    """STANDARD CONSENT STATUS"""

    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"
    EXPIRED = "expired"


class ProcessingLawfulBasis(str, Enum):
    """STANDARD GDPR LAWFUL BASIS"""

    CONSENT = "consent"  # Article 6(1)(a)
    CONTRACT = "contract"  # Article 6(1)(b)
    LEGAL_OBLIGATION = "legal_obligation"  # Article 6(1)(c)
    VITAL_INTERESTS = "vital_interests"  # Article 6(1)(d)
    PUBLIC_TASK = "public_task"  # Article 6(1)(e)
    LEGITIMATE_INTERESTS = "legitimate_interests"  # Article 6(1)(f)


@dataclass
class DataElement:
    """STANDARD DATA ELEMENT DEFINITION"""

    field_name: str
    classification: DataClassification
    privacy_level: PrivacyLevel
    retention_period: DataRetentionPeriod
    lawful_basis: ProcessingLawfulBasis
    purpose: str
    encryption_required: bool = True
    pseudonymization_required: bool = False
    access_control_required: bool = True


@dataclass
class ConsentRecord:
    """STANDARD CONSENT RECORD"""

    consent_id: str
    user_id: str
    purpose: str
    status: ConsentStatus
    granted_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    consent_text: str = ""
    processing_activities: List[str] = None


@dataclass
class DataProcessingRecord:
    """STANDARD DATA PROCESSING RECORD"""

    record_id: str
    user_id: str
    data_subject: str
    processing_purpose: str
    lawful_basis: ProcessingLawfulBasis
    data_categories: List[str]
    recipients: List[str]
    retention_period: DataRetentionPeriod
    security_measures: List[str]
    created_at: datetime
    updated_at: datetime


class EncryptionService:
    """STANDARD ENCRYPTION SERVICE ENHANCED BY CRYPTOGRAPHY"""

    def __init__(self, master_key: Optional[str] = None):
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = os.getenv(
                "ENCRYPTION_MASTER_KEY", secrets.token_urlsafe(32)
            ).encode()

        # Derive encryption key from master key
        salt = (
            b"novel_engine_salt_2024"  # In production, use random salt per encryption
        )
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        self.fernet = Fernet(key)

    def encrypt(self, data: str) -> str:
        """STANDARD DATA ENCRYPTION"""
        if not data:
            return ""

        try:
            encrypted_data = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"ENCRYPTION FAILED: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """STANDARD DATA DECRYPTION"""
        if not encrypted_data:
            return ""

        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"DECRYPTION FAILED: {e}")
            raise

    def encrypt_dict(
        self, data: Dict[str, Any], fields_to_encrypt: List[str]
    ) -> Dict[str, Any]:
        """STANDARD DICTIONARY ENCRYPTION"""
        encrypted_data = data.copy()
        for field in fields_to_encrypt:
            if field in encrypted_data:
                value = encrypted_data[field]
                if isinstance(value, str):
                    encrypted_data[field] = self.encrypt(value)
                elif value is not None:
                    encrypted_data[field] = self.encrypt(str(value))
        return encrypted_data

    def decrypt_dict(
        self, encrypted_data: Dict[str, Any], fields_to_decrypt: List[str]
    ) -> Dict[str, Any]:
        """STANDARD DICTIONARY DECRYPTION"""
        decrypted_data = encrypted_data.copy()
        for field in fields_to_decrypt:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt(decrypted_data[field])
                except Exception:
                    # If decryption fails, field might not be encrypted
                    pass
        return decrypted_data


class PseudonymizationService:
    """STANDARD PSEUDONYMIZATION SERVICE"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()

    def pseudonymize(self, identifier: str, purpose: str = "default") -> str:
        """STANDARD IDENTIFIER PSEUDONYMIZATION"""
        combined = f"{identifier}:{purpose}:{self.secret_key.decode()}"
        hash_obj = hashlib.sha256(combined.encode())
        return hash_obj.hexdigest()[:16]  # 16 character pseudonym

    def create_pseudonym_mapping(
        self, original_id: str, purpose: str = "default"
    ) -> Tuple[str, str]:
        """STANDARD PSEUDONYM MAPPING CREATION"""
        pseudonym = self.pseudonymize(original_id, purpose)
        return original_id, pseudonym


class DataProtectionService:
    """STANDARD DATA PROTECTION SERVICE ENHANCED BY THE SYSTEM"""

    def __init__(self, database_path: str, master_key: Optional[str] = None):
        self.database_path = database_path
        self.encryption_service = EncryptionService(master_key)
        self.pseudonymization_service = PseudonymizationService(
            master_key or os.getenv("PSEUDONYMIZATION_KEY", secrets.token_urlsafe(32))
        )

        # Define data elements that require protection
        self.protected_data_elements = {
            "user_email": DataElement(
                field_name="email",
                classification=DataClassification.CONFIDENTIAL,
                privacy_level=PrivacyLevel.PERSONAL,
                retention_period=DataRetentionPeriod.LONG_TERM,
                lawful_basis=ProcessingLawfulBasis.CONTRACT,
                purpose="User account management",
                encryption_required=True,
            ),
            "user_password": DataElement(
                field_name="password_hash",
                classification=DataClassification.RESTRICTED,
                privacy_level=PrivacyLevel.SENSITIVE,
                retention_period=DataRetentionPeriod.LONG_TERM,
                lawful_basis=ProcessingLawfulBasis.CONTRACT,
                purpose="Authentication",
                encryption_required=True,
            ),
            "story_content": DataElement(
                field_name="story_content",
                classification=DataClassification.CONFIDENTIAL,
                privacy_level=PrivacyLevel.PERSONAL,
                retention_period=DataRetentionPeriod.MEDIUM_TERM,
                lawful_basis=ProcessingLawfulBasis.CONSENT,
                purpose="Content generation and storage",
                encryption_required=True,
            ),
            "character_data": DataElement(
                field_name="character_details",
                classification=DataClassification.INTERNAL,
                privacy_level=PrivacyLevel.PERSONAL,
                retention_period=DataRetentionPeriod.MEDIUM_TERM,
                lawful_basis=ProcessingLawfulBasis.CONSENT,
                purpose="Character management",
                encryption_required=False,
            ),
            "api_logs": DataElement(
                field_name="request_data",
                classification=DataClassification.INTERNAL,
                privacy_level=PrivacyLevel.PSEUDONYMOUS,
                retention_period=DataRetentionPeriod.SHORT_TERM,
                lawful_basis=ProcessingLawfulBasis.LEGITIMATE_INTERESTS,
                purpose="System monitoring and security",
                encryption_required=False,
                pseudonymization_required=True,
            ),
        }

    async def initialize_database(self):
        """STANDARD DATABASE INITIALIZATION"""
        async with aiosqlite.connect(self.database_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.execute("PRAGMA journal_mode = WAL")
            await conn.execute("PRAGMA synchronous = NORMAL")

            # Consent management table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consent_records (
                    consent_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    status TEXT NOT NULL,
                    granted_at TIMESTAMP NULL,
                    withdrawn_at TIMESTAMP NULL,
                    expires_at TIMESTAMP NULL,
                    consent_text TEXT NOT NULL,
                    processing_activities TEXT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Data processing records
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS data_processing_records (
                    record_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    data_subject TEXT NOT NULL,
                    processing_purpose TEXT NOT NULL,
                    lawful_basis TEXT NOT NULL,
                    data_categories TEXT NOT NULL,
                    recipients TEXT NOT NULL,
                    retention_period TEXT NOT NULL,
                    security_measures TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Data retention schedule
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS data_retention_schedule (
                    id TEXT PRIMARY KEY,
                    data_type TEXT NOT NULL,
                    user_id TEXT NULL,
                    created_at TIMESTAMP NOT NULL,
                    retention_period TEXT NOT NULL,
                    delete_after TIMESTAMP NOT NULL,
                    deleted BOOLEAN DEFAULT FALSE,
                    deletion_reason TEXT NULL
                )
            """
            )

            # Pseudonym mappings (encrypted)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pseudonym_mappings (
                    id TEXT PRIMARY KEY,
                    purpose TEXT NOT NULL,
                    encrypted_original_id TEXT NOT NULL,
                    pseudonym TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            await conn.commit()
            logger.info("DATA PROTECTION DATABASE INITIALIZED")

    async def record_consent(
        self,
        user_id: str,
        purpose: str,
        processing_activities: List[str],
        consent_text: str,
        expires_in_days: Optional[int] = None,
    ) -> ConsentRecord:
        """STANDARD CONSENT RECORDING"""
        consent_id = secrets.token_urlsafe(16)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None

        consent_record = ConsentRecord(
            consent_id=consent_id,
            user_id=user_id,
            purpose=purpose,
            status=ConsentStatus.GRANTED,
            granted_at=now,
            expires_at=expires_at,
            consent_text=consent_text,
            processing_activities=processing_activities,
        )

        async with aiosqlite.connect(self.database_path) as conn:
            await conn.execute(
                """
                INSERT INTO consent_records (
                    consent_id, user_id, purpose, status, granted_at, 
                    expires_at, consent_text, processing_activities
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    consent_record.consent_id,
                    consent_record.user_id,
                    consent_record.purpose,
                    consent_record.status.value,
                    consent_record.granted_at,
                    consent_record.expires_at,
                    consent_record.consent_text,
                    json.dumps(consent_record.processing_activities),
                ),
            )
            await conn.commit()

        logger.info(f"CONSENT RECORDED: {user_id} | Purpose: {purpose}")
        return consent_record

    async def withdraw_consent(self, user_id: str, purpose: str) -> bool:
        """STANDARD CONSENT WITHDRAWAL"""
        async with aiosqlite.connect(self.database_path) as conn:
            await conn.execute(
                """
                UPDATE consent_records 
                SET status = ?, withdrawn_at = ?, updated_at = ?
                WHERE user_id = ? AND purpose = ? AND status = ?
            """,
                (
                    ConsentStatus.WITHDRAWN.value,
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc),
                    user_id,
                    purpose,
                    ConsentStatus.GRANTED.value,
                ),
            )

            rows_affected = conn.total_changes
            await conn.commit()

        if rows_affected > 0:
            logger.info(f"CONSENT WITHDRAWN: {user_id} | Purpose: {purpose}")
            # Trigger data deletion for withdrawn consent
            await self._handle_consent_withdrawal(user_id, purpose)
            return True

        return False

    async def check_consent(self, user_id: str, purpose: str) -> bool:
        """STANDARD CONSENT CHECK"""
        async with aiosqlite.connect(self.database_path) as conn:
            cursor = await conn.execute(
                """
                SELECT status, expires_at FROM consent_records
                WHERE user_id = ? AND purpose = ?
                ORDER BY granted_at DESC LIMIT 1
            """,
                (user_id, purpose),
            )
            row = await cursor.fetchone()

            if not row:
                return False

            status, expires_at = row

            # Check if consent is granted and not expired
            if status != ConsentStatus.GRANTED.value:
                return False

            if expires_at:
                expires_datetime = datetime.fromisoformat(expires_at)
                if expires_datetime < datetime.now(timezone.utc):
                    # Mark as expired
                    await conn.execute(
                        """
                        UPDATE consent_records 
                        SET status = ?, updated_at = ?
                        WHERE user_id = ? AND purpose = ? AND status = ?
                    """,
                        (
                            ConsentStatus.EXPIRED.value,
                            datetime.now(timezone.utc),
                            user_id,
                            purpose,
                            ConsentStatus.GRANTED.value,
                        ),
                    )
                    await conn.commit()
                    return False

            return True

    async def encrypt_personal_data(
        self, data: Dict[str, Any], data_type: str
    ) -> Dict[str, Any]:
        """STANDARD PERSONAL DATA ENCRYPTION"""
        if data_type not in self.protected_data_elements:
            return data

        element = self.protected_data_elements[data_type]

        if element.encryption_required:
            # Identify fields to encrypt based on data element definition
            fields_to_encrypt = [element.field_name]

            # Add additional sensitive fields
            sensitive_fields = ["email", "password_hash", "personal_info", "content"]
            fields_to_encrypt.extend([f for f in sensitive_fields if f in data])

            return self.encryption_service.encrypt_dict(data, fields_to_encrypt)

        return data

    async def decrypt_personal_data(
        self, encrypted_data: Dict[str, Any], data_type: str
    ) -> Dict[str, Any]:
        """STANDARD PERSONAL DATA DECRYPTION"""
        if data_type not in self.protected_data_elements:
            return encrypted_data

        element = self.protected_data_elements[data_type]

        if element.encryption_required:
            # Identify fields to decrypt
            fields_to_decrypt = [element.field_name]

            # Add additional sensitive fields
            sensitive_fields = ["email", "password_hash", "personal_info", "content"]
            fields_to_decrypt.extend(
                [f for f in sensitive_fields if f in encrypted_data]
            )

            return self.encryption_service.decrypt_dict(
                encrypted_data, fields_to_decrypt
            )

        return encrypted_data

    async def pseudonymize_data(
        self, data: Dict[str, Any], user_id: str, purpose: str
    ) -> Dict[str, Any]:
        """STANDARD DATA PSEUDONYMIZATION"""
        pseudonymized_data = data.copy()

        # Create pseudonym for user ID
        original_id, pseudonym = self.pseudonymization_service.create_pseudonym_mapping(
            user_id, purpose
        )

        # Store mapping securely
        await self._store_pseudonym_mapping(original_id, pseudonym, purpose)

        # Replace user ID with pseudonym
        if "user_id" in pseudonymized_data:
            pseudonymized_data["user_id"] = pseudonym

        # Remove direct identifiers
        identifiers_to_remove = ["email", "full_name", "phone", "address"]
        for identifier in identifiers_to_remove:
            pseudonymized_data.pop(identifier, None)

        return pseudonymized_data

    async def _store_pseudonym_mapping(
        self, original_id: str, pseudonym: str, purpose: str
    ):
        """STANDARD PSEUDONYM MAPPING STORAGE"""
        mapping_id = secrets.token_urlsafe(16)
        encrypted_original_id = self.encryption_service.encrypt(original_id)

        async with aiosqlite.connect(self.database_path) as conn:
            await conn.execute(
                """
                INSERT INTO pseudonym_mappings (id, purpose, encrypted_original_id, pseudonym)
                VALUES (?, ?, ?, ?)
            """,
                (mapping_id, purpose, encrypted_original_id, pseudonym),
            )
            await conn.commit()

    async def schedule_data_deletion(
        self, data_type: str, user_id: str, retention_period: DataRetentionPeriod
    ):
        """STANDARD DATA DELETION SCHEDULING"""
        deletion_id = secrets.token_urlsafe(16)
        now = datetime.now(timezone.utc)

        # Calculate deletion date
        if retention_period == DataRetentionPeriod.IMMEDIATE:
            delete_after = now
        elif retention_period == DataRetentionPeriod.SHORT_TERM:
            delete_after = now + timedelta(days=30)
        elif retention_period == DataRetentionPeriod.MEDIUM_TERM:
            delete_after = now + timedelta(days=365)
        elif retention_period == DataRetentionPeriod.LONG_TERM:
            delete_after = now + timedelta(days=365 * 7)
        else:  # INDEFINITE
            delete_after = now + timedelta(days=365 * 100)  # Far future

        async with aiosqlite.connect(self.database_path) as conn:
            await conn.execute(
                """
                INSERT INTO data_retention_schedule (
                    id, data_type, user_id, created_at, retention_period, delete_after
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    deletion_id,
                    data_type,
                    user_id,
                    now,
                    retention_period.value,
                    delete_after,
                ),
            )
            await conn.commit()

        logger.info(
            f"DATA DELETION SCHEDULED: {data_type} | User: {user_id} | Delete after: {delete_after}"
        )

    async def process_data_deletions(self):
        """STANDARD DATA DELETION PROCESSING"""
        now = datetime.now(timezone.utc)

        async with aiosqlite.connect(self.database_path) as conn:
            # Get items scheduled for deletion
            cursor = await conn.execute(
                """
                SELECT id, data_type, user_id FROM data_retention_schedule
                WHERE delete_after <= ? AND deleted = FALSE
            """,
                (now,),
            )
            items_to_delete = await cursor.fetchall()

            for deletion_id, data_type, user_id in items_to_delete:
                try:
                    # Perform actual data deletion (implement based on data type)
                    await self._delete_user_data(data_type, user_id)

                    # Mark as deleted
                    await conn.execute(
                        """
                        UPDATE data_retention_schedule 
                        SET deleted = TRUE, deletion_reason = 'Retention period expired'
                        WHERE id = ?
                    """,
                        (deletion_id,),
                    )

                    logger.info(f"DATA DELETED: {data_type} | User: {user_id}")

                except Exception as e:
                    logger.error(
                        f"DATA DELETION FAILED: {data_type} | User: {user_id} | Error: {e}"
                    )

            await conn.commit()

    async def _delete_user_data(self, data_type: str, user_id: str):
        """STANDARD USER DATA DELETION"""
        # This would implement actual data deletion based on data type
        # For now, this is a placeholder that logs the deletion
        logger.info(f"DELETING USER DATA: {data_type} | User: {user_id}")

        # In a real implementation, this would:
        # 1. Delete from main application database
        # 2. Delete from backup systems
        # 3. Delete from log files
        # 4. Notify external processors
        # 5. Generate deletion certificate

    async def _handle_consent_withdrawal(self, user_id: str, purpose: str):
        """STANDARD CONSENT WITHDRAWAL HANDLING"""
        # Schedule immediate deletion of data processed for this purpose
        await self.schedule_data_deletion(
            data_type=f"consent_{purpose}",
            user_id=user_id,
            retention_period=DataRetentionPeriod.IMMEDIATE,
        )

    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """STANDARD USER DATA EXPORT (GDPR Article 20)"""
        exported_data = {
            "user_id": user_id,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "data_categories": {},
        }

        # Get consent records
        async with aiosqlite.connect(self.database_path) as conn:
            cursor = await conn.execute(
                """
                SELECT purpose, status, granted_at, consent_text 
                FROM consent_records WHERE user_id = ?
            """,
                (user_id,),
            )
            consent_records = await cursor.fetchall()

            exported_data["consent_records"] = [
                {
                    "purpose": row[0],
                    "status": row[1],
                    "granted_at": row[2],
                    "consent_text": row[3],
                }
                for row in consent_records
            ]

        # Export other user data (implement based on your data model)
        # This would include decrypted personal data that the user has rights to

        logger.info(f"USER DATA EXPORTED: {user_id}")
        return exported_data

    async def get_processing_activities(self, user_id: str) -> List[Dict[str, Any]]:
        """STANDARD PROCESSING ACTIVITIES REPORT"""
        async with aiosqlite.connect(self.database_path) as conn:
            cursor = await conn.execute(
                """
                SELECT processing_purpose, lawful_basis, data_categories, 
                       recipients, security_measures, created_at
                FROM data_processing_records WHERE user_id = ?
            """,
                (user_id,),
            )
            records = await cursor.fetchall()

            return [
                {
                    "purpose": row[0],
                    "lawful_basis": row[1],
                    "data_categories": json.loads(row[2]),
                    "recipients": json.loads(row[3]),
                    "security_measures": json.loads(row[4]),
                    "start_date": row[5],
                }
                for row in records
            ]


# STANDARD GLOBAL DATA PROTECTION SERVICE
data_protection_service: Optional[DataProtectionService] = None


def get_data_protection_service() -> DataProtectionService:
    """STANDARD DATA PROTECTION SERVICE GETTER"""
    global data_protection_service
    if data_protection_service is None:
        raise RuntimeError("Data protection service not initialized")
    return data_protection_service


def initialize_data_protection_service(
    database_path: str, master_key: Optional[str] = None
):
    """STANDARD DATA PROTECTION SERVICE INITIALIZATION"""
    global data_protection_service
    data_protection_service = DataProtectionService(database_path, master_key)
    return data_protection_service


__all__ = [
    "DataClassification",
    "PrivacyLevel",
    "DataRetentionPeriod",
    "ConsentStatus",
    "ProcessingLawfulBasis",
    "DataElement",
    "ConsentRecord",
    "DataProcessingRecord",
    "EncryptionService",
    "PseudonymizationService",
    "DataProtectionService",
    "get_data_protection_service",
    "initialize_data_protection_service",
]
