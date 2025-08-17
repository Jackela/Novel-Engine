#!/usr/bin/env python3
"""
Advanced Export and Integration Engine
======================================

Comprehensive export and integration system for Novel Engine that provides
multi-format story export, sharing capabilities, API integrations, and
version control for stories.

Features:
- Multi-format export (PDF, EPUB, JSON, Markdown, HTML, DOCX)
- Story sharing and collaboration features
- API integration capabilities for external tools
- Batch story generation and management
- Version control and story iteration tracking
- Integration with publishing platforms
- Custom template support
- Metadata preservation and enhancement
"""

import json
import logging
import asyncio
import zipfile
import tempfile
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, IO
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import xml.etree.ElementTree as ET
from io import BytesIO, StringIO
import hashlib
import uuid

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Supported export formats."""
    PDF = "pdf"
    EPUB = "epub"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
    TXT = "txt"
    XML = "xml"
    RTF = "rtf"
    LATEX = "latex"


class ShareMode(Enum):
    """Story sharing modes."""
    PRIVATE = "private"             # Private, no sharing
    LINK_ONLY = "link_only"         # Share via link only
    PUBLIC = "public"               # Publicly discoverable
    COLLABORATIVE = "collaborative" # Allow collaborative editing
    READ_ONLY = "read_only"         # Read-only sharing
    COMMUNITY = "community"         # Community sharing


class IntegrationType(Enum):
    """Types of external integrations."""
    PUBLISHING_PLATFORM = "publishing_platform"
    WRITING_TOOL = "writing_tool"
    SOCIAL_MEDIA = "social_media"
    CLOUD_STORAGE = "cloud_storage"
    VERSION_CONTROL = "version_control"
    ANALYTICS = "analytics"
    FEEDBACK = "feedback"
    COLLABORATION = "collaboration"


class VersionAction(Enum):
    """Version control actions."""
    CREATE = "create"
    EDIT = "edit"
    MERGE = "merge"
    BRANCH = "branch"
    TAG = "tag"
    RESTORE = "restore"
    ARCHIVE = "archive"


@dataclass
class ExportRequest:
    """Export request configuration."""
    export_id: str
    story_id: str
    user_id: str
    format: ExportFormat
    options: Dict[str, Any] = field(default_factory=dict)
    template: Optional[str] = None
    metadata_options: Dict[str, Any] = field(default_factory=dict)
    custom_styles: Optional[Dict[str, Any]] = None
    include_analytics: bool = False
    watermark: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    priority: str = "normal"  # low, normal, high, urgent


@dataclass
class ExportResult:
    """Export operation result."""
    export_id: str
    success: bool
    format: ExportFormat
    file_path: Optional[str] = None
    file_data: Optional[bytes] = None
    file_size: int = 0
    export_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    download_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


@dataclass
class ShareConfiguration:
    """Story sharing configuration."""
    share_id: str
    story_id: str
    user_id: str
    share_mode: ShareMode
    permissions: Dict[str, bool] = field(default_factory=dict)
    expiry_date: Optional[datetime] = None
    access_token: Optional[str] = None
    password_protected: bool = False
    password_hash: Optional[str] = None
    allowed_users: List[str] = field(default_factory=list)
    share_url: Optional[str] = None
    analytics_enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: Optional[datetime] = None


@dataclass
class StoryVersion:
    """Story version for version control."""
    version_id: str
    story_id: str
    user_id: str
    version_number: str
    action: VersionAction
    content_hash: str
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_version: Optional[str] = None
    branch_name: str = "main"
    commit_message: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    file_size: int = 0
    changes_summary: Optional[Dict[str, Any]] = None


@dataclass
class IntegrationConnection:
    """External integration connection."""
    connection_id: str
    user_id: str
    integration_type: IntegrationType
    platform_name: str
    credentials: Dict[str, Any] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"  # active, inactive, error, expired
    last_sync: Optional[datetime] = None
    sync_frequency: Optional[str] = None  # manual, daily, weekly
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExportIntegrationEngine:
    """
    Advanced export and integration engine that handles multi-format exports,
    story sharing, external integrations, and version control.
    """
    
    def __init__(self, storage_path: str = "exports", max_file_size: int = 100 * 1024 * 1024):
        """
        Initialize the Export Integration Engine.
        
        Args:
            storage_path: Path for storing exported files
            max_file_size: Maximum file size for exports (in bytes)
        """
        self.storage_path = Path(storage_path)
        self.max_file_size = max_file_size
        
        # Create storage directory
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Data stores
        self.export_requests: Dict[str, ExportRequest] = {}
        self.export_results: Dict[str, ExportResult] = {}
        self.share_configurations: Dict[str, ShareConfiguration] = {}
        self.story_versions: Dict[str, List[StoryVersion]] = {}
        self.integration_connections: Dict[str, IntegrationConnection] = {}
        
        # Export templates and formatters
        self.export_templates: Dict[str, Dict[str, Any]] = {}
        self.format_handlers: Dict[ExportFormat, callable] = {}
        
        # Sharing and collaboration
        self.active_shares: Dict[str, ShareConfiguration] = {}
        self.collaboration_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Integration handlers
        self.integration_handlers: Dict[IntegrationType, callable] = {}
        self.sync_queue: asyncio.Queue = asyncio.Queue()
        
        # Performance and caching
        self.export_cache: Dict[str, ExportResult] = {}
        self.version_cache: Dict[str, StoryVersion] = {}
        
        # Initialize subsystems
        self._initialize_format_handlers()
        self._initialize_export_templates()
        self._initialize_integration_handlers()
        
        logger.info(f"ExportIntegrationEngine initialized with storage at {self.storage_path}")
    
    def _initialize_format_handlers(self):
        """Initialize format-specific export handlers."""
        self.format_handlers = {
            ExportFormat.JSON: self._export_json,
            ExportFormat.MARKDOWN: self._export_markdown,
            ExportFormat.HTML: self._export_html,
            ExportFormat.TXT: self._export_txt,
            ExportFormat.XML: self._export_xml,
            ExportFormat.PDF: self._export_pdf,
            ExportFormat.EPUB: self._export_epub,
            ExportFormat.DOCX: self._export_docx,
            ExportFormat.RTF: self._export_rtf,
            ExportFormat.LATEX: self._export_latex
        }
    
    def _initialize_export_templates(self):
        """Initialize export templates for different formats."""
        self.export_templates = {
            "html_standard": {
                "format": ExportFormat.HTML,
                "template": """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>{title}</title>
                    <meta charset="UTF-8">
                    <style>{styles}</style>
                </head>
                <body>
                    <header>
                        <h1>{title}</h1>
                        <div class="metadata">{metadata}</div>
                    </header>
                    <main>
                        {content}
                    </main>
                    <footer>
                        <div class="generated">Generated by Novel Engine on {date}</div>
                    </footer>
                </body>
                </html>
                """,
                "styles": """
                body { font-family: 'Times New Roman', serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; border-bottom: 2px solid #333; }
                .metadata { color: #666; font-style: italic; margin: 10px 0; }
                .generated { text-align: center; color: #999; font-size: 0.8em; margin-top: 40px; }
                p { line-height: 1.6; margin: 1em 0; }
                """
            },
            "markdown_github": {
                "format": ExportFormat.MARKDOWN,
                "template": """# {title}

{metadata}

---

{content}

---

*Generated by Novel Engine on {date}*
"""
            },
            "epub_standard": {
                "format": ExportFormat.EPUB,
                "metadata": {
                    "creator": "Novel Engine",
                    "language": "en",
                    "rights": "Copyright holder retains rights"
                }
            }
        }
    
    def _initialize_integration_handlers(self):
        """Initialize integration handlers for external platforms."""
        self.integration_handlers = {
            IntegrationType.PUBLISHING_PLATFORM: self._handle_publishing_integration,
            IntegrationType.CLOUD_STORAGE: self._handle_cloud_storage_integration,
            IntegrationType.SOCIAL_MEDIA: self._handle_social_media_integration,
            IntegrationType.VERSION_CONTROL: self._handle_version_control_integration,
            IntegrationType.COLLABORATION: self._handle_collaboration_integration
        }
    
    async def export_story(self, request: ExportRequest) -> ExportResult:
        """
        Export a story in the specified format.
        
        Args:
            request: Export request configuration
            
        Returns:
            Export result with file data or error information
        """
        try:
            start_time = datetime.now()
            
            # Validate request
            validation_result = await self._validate_export_request(request)
            if not validation_result["valid"]:
                return ExportResult(
                    export_id=request.export_id,
                    success=False,
                    format=request.format,
                    error_message=validation_result["error"]
                )
            
            # Store request
            self.export_requests[request.export_id] = request
            
            # Get story data
            story_data = await self._get_story_data(request.story_id)
            if not story_data:
                return ExportResult(
                    export_id=request.export_id,
                    success=False,
                    format=request.format,
                    error_message="Story not found"
                )
            
            # Check cache
            cache_key = self._generate_export_cache_key(request, story_data)
            if cache_key in self.export_cache:
                cached_result = self.export_cache[cache_key]
                if self._is_cache_valid(cached_result):
                    logger.info(f"Returning cached export for {request.export_id}")
                    return cached_result
            
            # Apply template if specified
            if request.template:
                story_data = await self._apply_export_template(story_data, request.template, request.options)
            
            # Get format handler
            handler = self.format_handlers.get(request.format)
            if not handler:
                return ExportResult(
                    export_id=request.export_id,
                    success=False,
                    format=request.format,
                    error_message=f"Unsupported format: {request.format.value}"
                )
            
            # Perform export
            export_data = await handler(story_data, request.options)
            
            # Apply watermark if specified
            if request.watermark:
                export_data = await self._apply_watermark(export_data, request.watermark, request.format)
            
            # Save file if needed
            file_path = None
            if request.options.get("save_file", True):
                file_path = await self._save_export_file(
                    export_data, request.export_id, request.format
                )
            
            # Calculate metrics
            export_time = (datetime.now() - start_time).total_seconds()
            file_size = len(export_data) if isinstance(export_data, (bytes, str)) else 0
            
            # Create result
            result = ExportResult(
                export_id=request.export_id,
                success=True,
                format=request.format,
                file_path=str(file_path) if file_path else None,
                file_data=export_data if not file_path else None,
                file_size=file_size,
                export_time=export_time,
                metadata=await self._generate_export_metadata(story_data, request),
                expires_at=datetime.now() + timedelta(days=7)  # Default 7-day expiry
            )
            
            # Store result and cache
            self.export_results[request.export_id] = result
            self.export_cache[cache_key] = result
            
            logger.info(f"Successfully exported story {request.story_id} to {request.format.value}")
            return result
            
        except Exception as e:
            logger.error(f"Export failed for {request.export_id}: {e}")
            return ExportResult(
                export_id=request.export_id,
                success=False,
                format=request.format,
                error_message=str(e)
            )
    
    async def create_story_share(self, share_config: ShareConfiguration) -> Dict[str, Any]:
        """
        Create a shareable link for a story.
        
        Args:
            share_config: Sharing configuration
            
        Returns:
            Share result with URL and access information
        """
        try:
            # Generate secure access token
            if not share_config.access_token:
                share_config.access_token = self._generate_access_token()
            
            # Generate share URL
            share_config.share_url = self._generate_share_url(share_config)
            
            # Store configuration
            self.share_configurations[share_config.share_id] = share_config
            self.active_shares[share_config.share_id] = share_config
            
            # Set up analytics if enabled
            if share_config.analytics_enabled:
                await self._setup_share_analytics(share_config)
            
            result = {
                "success": True,
                "share_id": share_config.share_id,
                "share_url": share_config.share_url,
                "access_token": share_config.access_token,
                "expires_at": share_config.expiry_date,
                "permissions": share_config.permissions,
                "analytics_enabled": share_config.analytics_enabled
            }
            
            logger.info(f"Created share for story {share_config.story_id}: {share_config.share_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create story share: {e}")
            return {"success": False, "error": str(e)}
    
    async def access_shared_story(self, share_id: str, access_token: Optional[str] = None,
                                password: Optional[str] = None) -> Dict[str, Any]:
        """
        Access a shared story.
        
        Args:
            share_id: Share identifier
            access_token: Access token for authentication
            password: Password if password-protected
            
        Returns:
            Story data and access information
        """
        try:
            if share_id not in self.active_shares:
                return {"success": False, "error": "Share not found or expired"}
            
            share_config = self.active_shares[share_id]
            
            # Check expiry
            if share_config.expiry_date and datetime.now() > share_config.expiry_date:
                return {"success": False, "error": "Share has expired"}
            
            # Validate access token
            if share_config.access_token and access_token != share_config.access_token:
                return {"success": False, "error": "Invalid access token"}
            
            # Check password
            if share_config.password_protected:
                if not password or not self._verify_password(password, share_config.password_hash):
                    return {"success": False, "error": "Invalid password"}
            
            # Get story data
            story_data = await self._get_story_data(share_config.story_id)
            if not story_data:
                return {"success": False, "error": "Story not found"}
            
            # Update access metrics
            share_config.access_count += 1
            share_config.last_accessed = datetime.now()
            
            # Track analytics
            if share_config.analytics_enabled:
                await self._track_share_access(share_config, access_token)
            
            result = {
                "success": True,
                "story_data": story_data,
                "share_info": {
                    "share_mode": share_config.share_mode.value,
                    "permissions": share_config.permissions,
                    "access_count": share_config.access_count
                }
            }
            
            logger.info(f"Story accessed via share {share_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to access shared story: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_story_version(self, story_id: str, user_id: str, action: VersionAction,
                                 content: Dict[str, Any], commit_message: Optional[str] = None,
                                 branch_name: str = "main") -> StoryVersion:
        """
        Create a new version of a story for version control.
        
        Args:
            story_id: Story identifier
            user_id: User creating the version
            action: Version action type
            content: Story content
            commit_message: Optional commit message
            branch_name: Branch name
            
        Returns:
            Created story version
        """
        try:
            # Generate version ID and number
            version_id = f"{story_id}_v_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Get existing versions for this story
            existing_versions = self.story_versions.get(story_id, [])
            
            # Calculate version number
            if action == VersionAction.CREATE:
                version_number = "1.0.0"
                parent_version = None
            else:
                # Find latest version in branch
                branch_versions = [v for v in existing_versions if v.branch_name == branch_name]
                if branch_versions:
                    latest_version = max(branch_versions, key=lambda x: x.created_at)
                    parent_version = latest_version.version_id
                    version_number = self._increment_version_number(latest_version.version_number, action)
                else:
                    version_number = "1.0.0"
                    parent_version = None
            
            # Calculate content hash
            content_hash = self._calculate_content_hash(content)
            
            # Calculate changes if parent exists
            changes_summary = None
            if parent_version:
                parent_content = next((v.content for v in existing_versions if v.version_id == parent_version), None)
                if parent_content:
                    changes_summary = await self._calculate_content_changes(parent_content, content)
            
            # Create version
            version = StoryVersion(
                version_id=version_id,
                story_id=story_id,
                user_id=user_id,
                version_number=version_number,
                action=action,
                content_hash=content_hash,
                content=content,
                parent_version=parent_version,
                branch_name=branch_name,
                commit_message=commit_message,
                file_size=len(json.dumps(content).encode('utf-8')),
                changes_summary=changes_summary,
                metadata={
                    "created_by": user_id,
                    "action_type": action.value,
                    "branch": branch_name,
                    "content_type": "story_data"
                }
            )
            
            # Store version
            if story_id not in self.story_versions:
                self.story_versions[story_id] = []
            self.story_versions[story_id].append(version)
            
            # Cache latest version
            self.version_cache[f"{story_id}:{branch_name}:latest"] = version
            
            logger.info(f"Created version {version_number} for story {story_id}")
            return version
            
        except Exception as e:
            logger.error(f"Failed to create story version: {e}")
            raise
    
    async def get_story_versions(self, story_id: str, branch_name: Optional[str] = None,
                               limit: int = 50) -> List[StoryVersion]:
        """
        Get version history for a story.
        
        Args:
            story_id: Story identifier
            branch_name: Optional branch filter
            limit: Maximum number of versions to return
            
        Returns:
            List of story versions
        """
        try:
            if story_id not in self.story_versions:
                return []
            
            versions = self.story_versions[story_id]
            
            # Filter by branch if specified
            if branch_name:
                versions = [v for v in versions if v.branch_name == branch_name]
            
            # Sort by creation time (newest first) and limit
            versions.sort(key=lambda x: x.created_at, reverse=True)
            return versions[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get story versions: {e}")
            return []
    
    async def restore_story_version(self, story_id: str, version_id: str, user_id: str) -> Dict[str, Any]:
        """
        Restore a story to a specific version.
        
        Args:
            story_id: Story identifier
            version_id: Version to restore
            user_id: User performing the restore
            
        Returns:
            Restore result
        """
        try:
            # Find the version to restore
            versions = self.story_versions.get(story_id, [])
            target_version = next((v for v in versions if v.version_id == version_id), None)
            
            if not target_version:
                return {"success": False, "error": "Version not found"}
            
            # Create restore version
            restore_version = await self.create_story_version(
                story_id=story_id,
                user_id=user_id,
                action=VersionAction.RESTORE,
                content=target_version.content,
                commit_message=f"Restored to version {target_version.version_number}",
                branch_name=target_version.branch_name
            )
            
            result = {
                "success": True,
                "restored_version": version_id,
                "new_version": restore_version.version_id,
                "content": target_version.content
            }
            
            logger.info(f"Restored story {story_id} to version {target_version.version_number}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to restore story version: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_integration(self, connection: IntegrationConnection) -> Dict[str, Any]:
        """
        Create an external integration connection.
        
        Args:
            connection: Integration connection configuration
            
        Returns:
            Integration creation result
        """
        try:
            # Validate integration
            validation_result = await self._validate_integration(connection)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}
            
            # Test connection
            test_result = await self._test_integration_connection(connection)
            if not test_result["success"]:
                return {"success": False, "error": f"Connection test failed: {test_result['error']}"}
            
            # Store connection
            self.integration_connections[connection.connection_id] = connection
            
            # Set up sync if configured
            if connection.sync_frequency and connection.sync_frequency != "manual":
                await self._schedule_integration_sync(connection)
            
            result = {
                "success": True,
                "connection_id": connection.connection_id,
                "status": connection.status,
                "platform": connection.platform_name,
                "sync_frequency": connection.sync_frequency
            }
            
            logger.info(f"Created integration {connection.connection_id} for {connection.platform_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create integration: {e}")
            return {"success": False, "error": str(e)}
    
    async def sync_integration(self, connection_id: str, operation: str = "export") -> Dict[str, Any]:
        """
        Sync data with an external integration.
        
        Args:
            connection_id: Integration connection ID
            operation: Sync operation (export, import, sync)
            
        Returns:
            Sync result
        """
        try:
            if connection_id not in self.integration_connections:
                return {"success": False, "error": "Integration connection not found"}
            
            connection = self.integration_connections[connection_id]
            
            # Get integration handler
            handler = self.integration_handlers.get(connection.integration_type)
            if not handler:
                return {"success": False, "error": f"No handler for integration type {connection.integration_type.value}"}
            
            # Perform sync
            sync_result = await handler(connection, operation)
            
            # Update last sync time
            connection.last_sync = datetime.now()
            
            logger.info(f"Synced integration {connection_id} with operation {operation}")
            return sync_result
            
        except Exception as e:
            logger.error(f"Failed to sync integration: {e}")
            return {"success": False, "error": str(e)}
    
    async def batch_export_stories(self, story_ids: List[str], export_format: ExportFormat,
                                 user_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Export multiple stories in batch.
        
        Args:
            story_ids: List of story IDs to export
            export_format: Export format
            user_id: User requesting the export
            options: Export options
            
        Returns:
            Batch export result
        """
        try:
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            export_results = []
            
            for story_id in story_ids:
                request = ExportRequest(
                    export_id=f"{batch_id}_{story_id}",
                    story_id=story_id,
                    user_id=user_id,
                    format=export_format,
                    options=options or {}
                )
                
                result = await self.export_story(request)
                export_results.append({
                    "story_id": story_id,
                    "export_id": result.export_id,
                    "success": result.success,
                    "file_path": result.file_path,
                    "error": result.error_message
                })
            
            # Create batch archive if requested
            archive_path = None
            if options and options.get("create_archive", False):
                archive_path = await self._create_batch_archive(batch_id, export_results, export_format)
            
            result = {
                "success": True,
                "batch_id": batch_id,
                "total_stories": len(story_ids),
                "successful_exports": len([r for r in export_results if r["success"]]),
                "failed_exports": len([r for r in export_results if not r["success"]]),
                "export_results": export_results,
                "archive_path": archive_path
            }
            
            logger.info(f"Completed batch export {batch_id} for {len(story_ids)} stories")
            return result
            
        except Exception as e:
            logger.error(f"Failed to batch export stories: {e}")
            return {"success": False, "error": str(e)}
    
    # Format-specific export handlers
    
    async def _export_json(self, story_data: Dict[str, Any], options: Dict[str, Any]) -> bytes:
        """Export story as JSON."""
        try:
            indent = options.get("indent", 2)
            include_metadata = options.get("include_metadata", True)
            
            export_data = {
                "story": story_data,
                "export_metadata": {
                    "format": "json",
                    "exported_at": datetime.now().isoformat(),
                    "version": "1.0"
                } if include_metadata else None
            }
            
            if not include_metadata:
                export_data = story_data
            
            json_str = json.dumps(export_data, indent=indent, ensure_ascii=False)
            return json_str.encode('utf-8')
            
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            raise
    
    async def _export_markdown(self, story_data: Dict[str, Any], options: Dict[str, Any]) -> bytes:
        """Export story as Markdown."""
        try:
            include_metadata = options.get("include_metadata", True)
            style = options.get("style", "standard")
            
            markdown_content = []
            
            # Title
            if "title" in story_data:
                markdown_content.append(f"# {story_data['title']}\n")
            
            # Metadata
            if include_metadata and "metadata" in story_data:
                markdown_content.append("## Story Information\n")
                for key, value in story_data["metadata"].items():
                    markdown_content.append(f"**{key.title()}:** {value}  ")
                markdown_content.append("\n---\n")
            
            # Content
            if "content" in story_data:
                if isinstance(story_data["content"], str):
                    markdown_content.append(story_data["content"])
                elif isinstance(story_data["content"], list):
                    for paragraph in story_data["content"]:
                        markdown_content.append(f"{paragraph}\n")
            
            # Footer
            markdown_content.append(f"\n---\n*Generated by Novel Engine on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
            
            return "\n".join(markdown_content).encode('utf-8')
            
        except Exception as e:
            logger.error(f"Markdown export failed: {e}")
            raise
    
    async def _export_html(self, story_data: Dict[str, Any], options: Dict[str, Any]) -> bytes:
        """Export story as HTML."""
        try:
            template_name = options.get("template", "html_standard")
            include_styles = options.get("include_styles", True)
            
            # Get template
            template_config = self.export_templates.get(template_name, self.export_templates["html_standard"])
            template = template_config["template"]
            styles = template_config["styles"] if include_styles else ""
            
            # Prepare content
            content = story_data.get("content", "")
            if isinstance(content, list):
                content = "\n".join(f"<p>{paragraph}</p>" for paragraph in content)
            elif isinstance(content, str):
                # Convert line breaks to paragraphs
                paragraphs = content.split('\n\n')
                content = "\n".join(f"<p>{paragraph.replace(chr(10), ' ')}</p>" for paragraph in paragraphs if paragraph.strip())
            
            # Prepare metadata
            metadata_html = ""
            if "metadata" in story_data:
                metadata_items = []
                for key, value in story_data["metadata"].items():
                    metadata_items.append(f"<span class='meta-item'><strong>{key.title()}:</strong> {value}</span>")
                metadata_html = " | ".join(metadata_items)
            
            # Fill template
            html_content = template.format(
                title=story_data.get("title", "Untitled Story"),
                content=content,
                metadata=metadata_html,
                styles=styles,
                date=datetime.now().strftime('%Y-%m-%d %H:%M')
            )
            
            return html_content.encode('utf-8')
            
        except Exception as e:
            logger.error(f"HTML export failed: {e}")
            raise
    
    async def _export_txt(self, story_data: Dict[str, Any], options: Dict[str, Any]) -> bytes:
        """Export story as plain text."""
        try:
            include_metadata = options.get("include_metadata", True)
            line_ending = options.get("line_ending", "\n")
            
            text_content = []
            
            # Title
            if "title" in story_data:
                text_content.append(story_data["title"])
                text_content.append("=" * len(story_data["title"]))
                text_content.append("")
            
            # Metadata
            if include_metadata and "metadata" in story_data:
                for key, value in story_data["metadata"].items():
                    text_content.append(f"{key.title()}: {value}")
                text_content.append("")
                text_content.append("-" * 50)
                text_content.append("")
            
            # Content
            if "content" in story_data:
                if isinstance(story_data["content"], str):
                    text_content.append(story_data["content"])
                elif isinstance(story_data["content"], list):
                    text_content.extend(story_data["content"])
            
            # Footer
            text_content.append("")
            text_content.append("-" * 50)
            text_content.append(f"Generated by Novel Engine on {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            return line_ending.join(text_content).encode('utf-8')
            
        except Exception as e:
            logger.error(f"TXT export failed: {e}")
            raise
    
    async def _export_xml(self, story_data: Dict[str, Any], options: Dict[str, Any]) -> bytes:
        """Export story as XML."""
        try:
            root = ET.Element("story")
            
            # Title
            if "title" in story_data:
                title_elem = ET.SubElement(root, "title")
                title_elem.text = story_data["title"]
            
            # Metadata
            if "metadata" in story_data:
                metadata_elem = ET.SubElement(root, "metadata")
                for key, value in story_data["metadata"].items():
                    meta_elem = ET.SubElement(metadata_elem, key)
                    meta_elem.text = str(value)
            
            # Content
            if "content" in story_data:
                content_elem = ET.SubElement(root, "content")
                if isinstance(story_data["content"], str):
                    content_elem.text = story_data["content"]
                elif isinstance(story_data["content"], list):
                    for i, paragraph in enumerate(story_data["content"]):
                        para_elem = ET.SubElement(content_elem, "paragraph", {"index": str(i)})
                        para_elem.text = paragraph
            
            # Export metadata
            export_elem = ET.SubElement(root, "export_info")
            ET.SubElement(export_elem, "exported_at").text = datetime.now().isoformat()
            ET.SubElement(export_elem, "format").text = "xml"
            ET.SubElement(export_elem, "generator").text = "Novel Engine"
            
            # Convert to string
            xml_str = ET.tostring(root, encoding='unicode', method='xml')
            return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'.encode('utf-8')
            
        except Exception as e:
            logger.error(f"XML export failed: {e}")
            raise
    
    # Placeholder implementations for advanced formats
    
    async def _export_pdf(self, story_data: Dict[str, Any], options: Dict[str, Any]) -> bytes:
        """Export story as PDF."""
        # This would require a PDF library like reportlab
        logger.warning("PDF export not fully implemented")
        return b"PDF export placeholder"
    
    async def _export_epub(self, story_data: Dict[str, Any], options: Dict[str, Any]) -> bytes:
        """Export story as EPUB."""
        # This would require an EPUB library
        logger.warning("EPUB export not fully implemented")
        return b"EPUB export placeholder"
    
    async def _export_docx(self, story_data: Dict[str, Any], options: Dict[str, Any]) -> bytes:
        """Export story as DOCX."""
        # This would require python-docx library
        logger.warning("DOCX export not fully implemented")
        return b"DOCX export placeholder"
    
    async def _export_rtf(self, story_data: Dict[str, Any], options: Dict[str, Any]) -> bytes:
        """Export story as RTF."""
        logger.warning("RTF export not fully implemented")
        return b"RTF export placeholder"
    
    async def _export_latex(self, story_data: Dict[str, Any], options: Dict[str, Any]) -> bytes:
        """Export story as LaTeX."""
        logger.warning("LaTeX export not fully implemented")
        return b"LaTeX export placeholder"
    
    # Helper methods
    
    async def _validate_export_request(self, request: ExportRequest) -> Dict[str, Any]:
        """Validate export request."""
        if not request.story_id:
            return {"valid": False, "error": "Story ID is required"}
        
        if not request.user_id:
            return {"valid": False, "error": "User ID is required"}
        
        if request.format not in self.format_handlers:
            return {"valid": False, "error": f"Unsupported format: {request.format.value}"}
        
        return {"valid": True}
    
    async def _get_story_data(self, story_id: str) -> Optional[Dict[str, Any]]:
        """Get story data from storage."""
        # This would integrate with the story storage system
        # For now, return a placeholder
        return {
            "title": f"Story {story_id}",
            "content": "This is a placeholder story content.",
            "metadata": {
                "author": "Novel Engine User",
                "created_at": datetime.now().isoformat(),
                "genre": "fiction",
                "word_count": 100
            }
        }
    
    def _generate_export_cache_key(self, request: ExportRequest, story_data: Dict[str, Any]) -> str:
        """Generate cache key for export."""
        story_hash = hashlib.md5(json.dumps(story_data, sort_keys=True).encode()).hexdigest()
        options_hash = hashlib.md5(json.dumps(request.options, sort_keys=True).encode()).hexdigest()
        return f"{request.format.value}_{story_hash}_{options_hash}"
    
    def _is_cache_valid(self, cached_result: ExportResult) -> bool:
        """Check if cached export result is still valid."""
        if cached_result.expires_at and datetime.now() > cached_result.expires_at:
            return False
        return True
    
    async def _apply_export_template(self, story_data: Dict[str, Any], template_name: str,
                                   options: Dict[str, Any]) -> Dict[str, Any]:
        """Apply export template to story data."""
        # This would apply template transformations
        return story_data
    
    async def _apply_watermark(self, export_data: bytes, watermark: str, format: ExportFormat) -> bytes:
        """Apply watermark to exported data."""
        # This would apply format-specific watermarking
        return export_data
    
    async def _save_export_file(self, export_data: bytes, export_id: str, format: ExportFormat) -> Path:
        """Save export data to file."""
        filename = f"{export_id}.{format.value}"
        file_path = self.storage_path / filename
        
        with open(file_path, 'wb') as f:
            f.write(export_data)
        
        return file_path
    
    async def _generate_export_metadata(self, story_data: Dict[str, Any], request: ExportRequest) -> Dict[str, Any]:
        """Generate export metadata."""
        return {
            "original_story": request.story_id,
            "export_format": request.format.value,
            "exported_by": request.user_id,
            "export_timestamp": datetime.now().isoformat(),
            "story_metadata": story_data.get("metadata", {}),
            "export_options": request.options
        }
    
    def _generate_access_token(self) -> str:
        """Generate secure access token."""
        return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip('=')
    
    def _generate_share_url(self, share_config: ShareConfiguration) -> str:
        """Generate share URL."""
        base_url = "https://novelengine.com/share"  # This would be configurable
        return f"{base_url}/{share_config.share_id}?token={share_config.access_token}"
    
    async def _setup_share_analytics(self, share_config: ShareConfiguration):
        """Set up analytics for a shared story."""
        # This would integrate with the analytics platform
        pass
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        # This would use proper password hashing
        return hashlib.sha256(password.encode()).hexdigest() == password_hash
    
    async def _track_share_access(self, share_config: ShareConfiguration, access_token: Optional[str]):
        """Track access to shared story."""
        # This would integrate with analytics tracking
        pass
    
    def _calculate_content_hash(self, content: Dict[str, Any]) -> str:
        """Calculate hash of story content."""
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def _increment_version_number(self, current_version: str, action: VersionAction) -> str:
        """Increment version number based on action."""
        parts = current_version.split('.')
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        
        if action == VersionAction.EDIT:
            patch += 1
        elif action == VersionAction.MERGE:
            minor += 1
            patch = 0
        elif action == VersionAction.BRANCH:
            minor += 1
            patch = 0
        
        return f"{major}.{minor}.{patch}"
    
    async def _calculate_content_changes(self, old_content: Dict[str, Any], new_content: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate changes between content versions."""
        # This would implement diff calculation
        return {
            "changed_fields": [],
            "additions": 0,
            "deletions": 0,
            "modifications": 0
        }
    
    async def _create_batch_archive(self, batch_id: str, export_results: List[Dict[str, Any]],
                                  format: ExportFormat) -> str:
        """Create archive of batch exported files."""
        archive_path = self.storage_path / f"{batch_id}_archive.zip"
        
        with zipfile.ZipFile(archive_path, 'w') as archive:
            for result in export_results:
                if result["success"] and result["file_path"]:
                    file_path = Path(result["file_path"])
                    if file_path.exists():
                        archive.write(file_path, file_path.name)
        
        return str(archive_path)
    
    # Integration handlers
    
    async def _validate_integration(self, connection: IntegrationConnection) -> Dict[str, Any]:
        """Validate integration connection."""
        if not connection.platform_name:
            return {"valid": False, "error": "Platform name is required"}
        
        if not connection.credentials:
            return {"valid": False, "error": "Credentials are required"}
        
        return {"valid": True}
    
    async def _test_integration_connection(self, connection: IntegrationConnection) -> Dict[str, Any]:
        """Test integration connection."""
        # This would test the actual connection
        return {"success": True}
    
    async def _schedule_integration_sync(self, connection: IntegrationConnection):
        """Schedule automatic sync for integration."""
        # This would set up scheduled sync
        pass
    
    async def _handle_publishing_integration(self, connection: IntegrationConnection, operation: str) -> Dict[str, Any]:
        """Handle publishing platform integration."""
        return {"success": True, "message": "Publishing integration placeholder"}
    
    async def _handle_cloud_storage_integration(self, connection: IntegrationConnection, operation: str) -> Dict[str, Any]:
        """Handle cloud storage integration."""
        return {"success": True, "message": "Cloud storage integration placeholder"}
    
    async def _handle_social_media_integration(self, connection: IntegrationConnection, operation: str) -> Dict[str, Any]:
        """Handle social media integration."""
        return {"success": True, "message": "Social media integration placeholder"}
    
    async def _handle_version_control_integration(self, connection: IntegrationConnection, operation: str) -> Dict[str, Any]:
        """Handle version control integration."""
        return {"success": True, "message": "Version control integration placeholder"}
    
    async def _handle_collaboration_integration(self, connection: IntegrationConnection, operation: str) -> Dict[str, Any]:
        """Handle collaboration platform integration."""
        return {"success": True, "message": "Collaboration integration placeholder"}


def create_export_integration_engine(storage_path: str = "exports", max_file_size: int = 100 * 1024 * 1024) -> ExportIntegrationEngine:
    """
    Factory function to create and configure an Export Integration Engine.
    
    Args:
        storage_path: Path for storing exported files
        max_file_size: Maximum file size for exports
        
    Returns:
        Configured ExportIntegrationEngine instance
    """
    engine = ExportIntegrationEngine(storage_path, max_file_size)
    logger.info("Export Integration Engine created and configured")
    return engine