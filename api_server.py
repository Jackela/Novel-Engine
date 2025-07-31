#!/usr/bin/env python3
"""
FastAPI Web Server for Warhammer 40k Multi-Agent Simulator
===========================================================

This module implements a FastAPI web server that provides RESTful API endpoints
for the Warhammer 40k Multi-Agent Simulator. The server enables web-based access
to the simulation system, allowing external applications and clients to interact
with the simulator through HTTP requests.

The FastAPI server provides:
1. Basic API endpoint with health check functionality
2. JSON response format for API communication
3. Error handling and logging capabilities
4. Extensible structure for future endpoint additions
5. Integration preparation for existing simulator components

This implementation serves as the foundation for web API capabilities that will
later be extended with additional endpoints for simulation control, agent
management, and real-time updates.

Architecture Reference: Architecture_Blueprint.md - API Integration Layer
Development Phase: FastAPI Integration - Web Server Foundation
"""

import logging
import uvicorn
import os
import shutil
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, field_validator, Field
from typing import List as TypingList

# 召唤配置系统的神圣知识，为未来的机械融合做准备...
from config_loader import get_config

# 引入模拟引擎的神圣组件，准备唤醒沉睡的机器灵魂...
from character_factory import CharacterFactory
from director_agent import DirectorAgent
from chronicler_agent import ChroniclerAgent
# 引入Gemini API神圣接口，召唤AI Scribe的机械智慧...
from persona_agent import _validate_gemini_api_key, _make_gemini_api_request

# 引入神圣约束系统 - Sacred Constraints System blessed by the Omnissiah
from src.constraints_loader import (
    get_character_name_constraints,
    get_character_description_constraints,
    get_file_upload_constraints,
    get_simulation_constraints,
    validate_character_name,
    validate_character_description,
    validate_file_upload
)
import time
import uuid
import json
import re

# 启动神圣的信息记录仪式，追踪API神殿中一切圣行与异端活动...
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _find_project_root(start_path: str) -> str:
    """
    Find the project root directory by looking for marker files.
    
    Uses the same logic as CharacterFactory for consistency.
    
    Args:
        start_path: Directory to start searching from
        
    Returns:
        str: Path to the project root directory
    """
    # 寻觅项目圣域的标记符文，定位神圣机械殿堂的中心...
    markers = ['persona_agent.py', 'director_agent.py', 'config.yaml', '.git']
    
    current_path = os.path.abspath(start_path)
    while current_path != os.path.dirname(current_path):  # Not at filesystem root
        for marker in markers:
            if os.path.exists(os.path.join(current_path, marker)):
                logger.debug(f"Found project root at {current_path} (marker: {marker})")
                return current_path
        current_path = os.path.dirname(current_path)
    
    # 执行后备仪式：将当前工作目录奉为项目根目录圣域...
    fallback_root = os.path.abspath(os.getcwd())
    logger.warning(f"Could not determine project root, using fallback: {fallback_root}")
    return fallback_root


def _get_characters_directory_path() -> str:
    """
    Get the absolute path to the characters directory.
    
    Uses the same path resolution logic as CharacterFactory for consistency.
    
    Returns:
        str: Absolute path to the characters directory
    """
    base_character_path = "characters"
    
    # 执行路径圣化仪式，将相对路径转换为绝对圣域坐标，以应对工作目录的变迁...
    if not os.path.isabs(base_character_path):
        # 通过寻觅标记符文定位项目根目录圣域...
        current_dir = os.path.abspath(os.getcwd())
        project_root = _find_project_root(current_dir)
        characters_path = os.path.join(project_root, base_character_path)
    else:
        characters_path = base_character_path
    
    logger.debug(f"Characters directory path resolved to: {characters_path}")
    return characters_path


def _get_campaigns_directory_path() -> str:
    """
    Get the absolute path to the campaigns directory.
    
    Sacred path resolution for campaign codex storage, following the blessed
    architectural patterns of the Omnissiah.
    
    Returns:
        str: Absolute path to the codex/campaigns directory
    """
    base_campaigns_path = os.path.join("codex", "campaigns")
    
    # 执行战役圣域路径仪式，定位战役典籍的神圣存储殿堂...
    if not os.path.isabs(base_campaigns_path):
        # 通过寻觅标记符文定位项目根目录圣域...
        current_dir = os.path.abspath(os.getcwd())
        project_root = _find_project_root(current_dir)
        campaigns_path = os.path.join(project_root, base_campaigns_path)
    else:
        campaigns_path = base_campaigns_path
    
    logger.debug(f"Campaigns directory path resolved to: {campaigns_path}")
    return campaigns_path


# Response models for API documentation
class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    message: str


class ErrorResponse(BaseModel):
    """Response model for error responses."""
    error: str
    detail: str


class CharactersListResponse(BaseModel):
    """Response model for characters list endpoint."""
    characters: List[str]


class CampaignsListResponse(BaseModel):
    """Response model for campaigns list endpoint."""
    campaigns: List[str]


class CampaignCreationRequest(BaseModel):
    """Request model for campaign creation endpoint."""
    campaign_name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Sacred campaign designation (3-50 characters, alphanumeric and underscores only)"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional campaign description for AI-powered brief generation (max 500 characters)"
    )
    
    @field_validator('campaign_name')
    @classmethod
    def validate_campaign_name(cls, v):
        """Validate campaign name format using sacred naming conventions."""
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Campaign name must contain only alphanumeric characters and underscores')
        
        # Convert to lowercase for consistency
        return v.strip().lower()


class CampaignCreationResponse(BaseModel):
    """Response model for campaign creation endpoint."""
    campaign_name: str = Field(
        ...,
        description="Confirmed campaign designation"
    )
    status: str = Field(
        ...,
        description="Campaign creation status"
    )
    directory_path: str = Field(
        ...,
        description="Full path to the created campaign directory"
    )
    brief_generated: bool = Field(
        ...,
        description="Indicates whether AI-powered campaign brief was successfully generated"
    )


class FileCount(BaseModel):
    """Model for file count statistics."""
    md: int
    yaml: int


class CharacterDetailResponse(BaseModel):
    """Response model for character detail endpoint."""
    narrative_context: str
    structured_data: Dict[str, Any]
    character_name: str
    file_count: FileCount


class SimulationRequest(BaseModel):
    """Request model for simulation endpoint."""
    character_names: List[str] = Field(
        ...,
        min_length=get_simulation_constraints()['minSelection'],
        max_length=get_simulation_constraints()['maxSelection'],
        description=f"List of character names to participate in the simulation ({get_simulation_constraints()['minSelection']}-{get_simulation_constraints()['maxSelection']} characters)"
    )
    turns: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Number of turns to execute (default from config, range 1-10)"
    )
    narrative_style: Optional[str] = Field(
        default="epic",
        description="Style of narrative generation"
    )
    
    @field_validator('character_names')
    @classmethod
    def validate_character_names(cls, v):
        """Validate character names are non-empty strings."""
        if not v:
            raise ValueError('At least 2 character names are required')
        
        for name in v:
            if not isinstance(name, str) or not name.strip():
                raise ValueError('Character names must be non-empty strings')
        
        return [name.strip() for name in v]
    
    @field_validator('narrative_style')
    @classmethod
    def validate_narrative_style(cls, v):
        """Validate narrative style is one of the allowed values."""
        allowed_styles = ["epic", "detailed", "concise"]
        if v and v not in allowed_styles:
            raise ValueError(f'Narrative style must be one of: {", ".join(allowed_styles)}')
        return v


class SimulationResponse(BaseModel):
    """Response model for simulation endpoint."""
    story: str = Field(
        ...,
        description="The final narrative story generated by the ChroniclerAgent"
    )
    participants: List[str] = Field(
        ...,
        description="Character names that participated in the simulation"
    )
    turns_executed: int = Field(
        ...,
        ge=0,
        description="Actual number of turns executed during the simulation"
    )
    duration_seconds: float = Field(
        ...,
        ge=0.0,
        description="Total execution time of the simulation in seconds"
    )


class CharacterCreationRequest(BaseModel):
    """Request model for character creation endpoint."""
    name: str = Field(
        ...,
        min_length=get_character_name_constraints()['minLength'],
        max_length=get_character_name_constraints()['maxLength'],
        description=f"Character's sacred designation ({get_character_name_constraints()['minLength']}-{get_character_name_constraints()['maxLength']} characters)"
    )
    description: str = Field(
        ...,
        min_length=get_character_description_constraints()['minLength'],
        max_length=get_character_description_constraints()['maxLength'],
        description=f"Character's holy narrative description ({get_character_description_constraints()['minLength']}-{get_character_description_constraints()['maxLength']} characters, minimum {get_character_description_constraints()['minWords']} words)"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate character name format using centralized constraints."""
        is_valid, error_message = validate_character_name(v)
        if not is_valid:
            raise ValueError(error_message)
        
        # 统一为小写形式，遵循角色目录命名惯例...
        return v.strip().lower()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """Validate character description content using centralized constraints."""
        is_valid, error_message = validate_character_description(v)
        if not is_valid:
            raise ValueError(error_message)
        
        return v.strip()


class CharacterCreationResponse(BaseModel):
    """Response model for character creation endpoint."""
    name: str = Field(
        ...,
        description="Confirmed character designation"
    )
    status: str = Field(
        ...,
        description="Creation process status"
    )
    ai_scribe_enhanced: bool = Field(
        default=False,
        description="Whether the character was enhanced by AI Scribe"
    )
    files_processed: int = Field(
        default=0,
        description="Number of uploaded files processed"
    )


# AI Scribe Sacred Functions - Invoke the machine spirits of textual generation
async def _process_uploaded_files(files: TypingList[UploadFile]) -> str:
    """
    Process uploaded files and extract their text content.
    
    Sacred ritual to extract the textual essence from uploaded documents,
    preparing them for fusion with the character's base description.
    
    Args:
        files: List of uploaded files from the API request
        
    Returns:
        str: Concatenated text content from all files
        
    Raises:
        HTTPException: If file processing fails
    """
    all_text_content = []
    
    for file in files:
        try:
            # Read file content - sacred data extraction protocol
            content = await file.read()
            
            # Decode based on file type - interpret the machine runes
            try:
                if file.filename and file.filename.lower().endswith(('.txt', '.md', '.yaml', '.yml', '.json')):
                    text_content = content.decode('utf-8')
                else:
                    # Attempt UTF-8 decoding for other file types
                    text_content = content.decode('utf-8')
                
                # Add file header for context
                file_header = f"\n\n=== Content from file: {file.filename} ===\n"
                all_text_content.append(file_header + text_content)
                
                logger.info(f"Successfully processed file: {file.filename} ({len(text_content)} characters)")
                
            except UnicodeDecodeError:
                logger.warning(f"Could not decode file as UTF-8: {file.filename}")
                # Skip non-text files but log the attempt
                continue
                
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process uploaded file: {file.filename}"
            )
    
    return "\n".join(all_text_content)


def _create_master_context_engineer_prompt(name: str, description: str, file_content: str) -> str:
    """
    Create a detailed prompt for the Gemini API Master Context Engineer.
    
    Sacred incantation to invoke the AI Scribe's contextual generation powers,
    instructing it to act as a Master Context Engineer and generate structured
    character content following the V2 codex architecture.
    
    Args:
        name: Character's sacred designation
        description: User-provided character description
        file_content: Concatenated content from uploaded files
        
    Returns:
        str: Detailed prompt for Gemini API
    """
    prompt = f"""You are a Master Context Engineer specializing in Warhammer 40,000 universe character creation. Your sacred duty is to generate comprehensive character files based on the provided information.

CHARACTER DESIGNATION: {name}

USER DESCRIPTION:
{description}

ADDITIONAL CONTEXT FROM UPLOADED FILES:
{file_content}

YOUR MISSION:
Generate structured character content following the V2 Codex Architecture. Create exactly 4 files with the following specifications:

=== FILE: 1_core.md ===
# Character Core: {name.title()}

## Identity Matrix
- **Name**: [Full character name]
- **Title/Rank**: [Official designation]
- **Origin World**: [Homeworld/Origin]
- **Faction**: [Primary allegiance]
- **Role**: [Primary function/specialization]

## Physical Description
[Detailed physical appearance including distinctive features, scars, augmentations, height, build, eye color, etc.]

## Core Personality
[Primary personality traits, motivations, fears, loyalties, and behavioral patterns]

## Background Summary
[Concise overview of character's history and how they came to their current position]

=== FILE: 2_history.md ===
# Character History: {name.title()}

## Early Life
[Childhood, upbringing, formative experiences]

## Military/Professional Career
[Training, service record, notable campaigns or assignments]

## Key Events
[3-5 major events that shaped the character]

## Current Status
[Present circumstances and ongoing objectives]

## Notable Achievements
[Major accomplishments and recognitions]

## Scars and Losses
[Traumatic events, losses, and how they affected the character]

=== FILE: 3_profile.yaml ===
character:
  name: "[Character full name]"
  age: [Age in years]
  origin: "[Homeworld/Origin]"
  faction: "[Primary faction]"
  rank: "[Military/organizational rank]"
  specialization: "[Primary role/specialization]"

combat_stats:
  marksmanship: [1-10]
  melee: [1-10]
  tactics: [1-10]
  leadership: [1-10]
  endurance: [1-10]
  pilot: [1-10]

equipment:
  primary_weapon: "[Main weapon]"
  secondary_weapon: "[Backup weapon]"
  armor: "[Armor type]"
  special_gear:
    - "[Special equipment 1]"
    - "[Special equipment 2]"
    - "[Special equipment 3]"

psychological_profile:
  loyalty: [1-10]
  aggression: [1-10]
  caution: [1-10]
  morale: [1-10]
  corruption_resistance: [1-10]

specializations:
  - "[Specialization 1]"
  - "[Specialization 2]"
  - "[Specialization 3]"

relationships:
  allies:
    - "[Allied character/organization]"
  enemies:
    - "[Enemy character/organization]"
  mentor: "[Mentor figure if applicable]"

=== FILE: 4_lore.md ===
# Character Lore: {name.title()}

## Regiment/Organization Details
[Detailed information about their military unit or organization]

## Homeworld/Culture
[In-depth exploration of their cultural background and homeworld]

## Notable Quotes
> "[Memorable quote 1]"
> "[Memorable quote 2]"
> "[Memorable quote 3]"

## Combat Doctrine
[Preferred fighting style and tactical approaches]

## Beliefs and Philosophy
[Religious beliefs, personal philosophy, worldview]

## Secrets and Hidden Knowledge
[Things few others know about this character]

## Future Aspirations
[Goals, dreams, or destinies they pursue]

CRITICAL INSTRUCTIONS:
1. Base all content on the provided description and uploaded file context
2. Ensure all content is appropriate for the Warhammer 40,000 universe
3. Make stats realistic and balanced (avoid all 10s)
4. Include specific 40k lore elements and terminology
5. Maintain internal consistency across all files
6. Output EXACTLY the 4 files with the delimiters shown above
7. Use the exact file naming convention specified

Begin generation now. The Emperor protects."""

    return prompt


def _parse_generated_content(generated_text: str) -> Dict[str, str]:
    """
    Parse the AI-generated content into individual files.
    
    Sacred text parsing ritual to separate the generated content into
    the four required files of the V2 codex architecture.
    
    Args:
        generated_text: Complete response from Gemini API
        
    Returns:
        Dict[str, str]: Dictionary mapping filename to content
        
    Raises:
        ValueError: If content cannot be properly parsed
    """
    files = {}
    
    # Define file patterns - sacred parsing incantations
    file_patterns = {
        '1_core.md': r'=== FILE: 1_core\.md ===(.*?)(?==== FILE:|\Z)',
        '2_history.md': r'=== FILE: 2_history\.md ===(.*?)(?==== FILE:|\Z)',
        '3_profile.yaml': r'=== FILE: 3_profile\.yaml ===(.*?)(?==== FILE:|\Z)',
        '4_lore.md': r'=== FILE: 4_lore\.md ===(.*?)(?==== FILE:|\Z)'
    }
    
    for filename, pattern in file_patterns.items():
        match = re.search(pattern, generated_text, re.MULTILINE | re.DOTALL)
        if match:
            content = match.group(1).strip()
            files[filename] = content
            logger.debug(f"Successfully parsed content for {filename}: {len(content)} characters")
        else:
            logger.warning(f"Could not find content for {filename} in generated text")
            # Create minimal fallback content
            if filename.endswith('.yaml'):
                files[filename] = f"character:\n  name: \"Generated Character\"\n  status: \"AI_Generated_Placeholder\""
            else:
                files[filename] = f"# {filename}\n\nAI-generated content parsing failed. Please review and edit manually."
    
    return files


async def _write_v2_character_files(character_dir: str, files_content: Dict[str, str]) -> None:
    """
    Write the parsed content to V2 character files.
    
    Sacred file writing ritual to manifest the AI-generated character
    data into physical storage following V2 codex structure.
    
    Args:
        character_dir: Path to character directory
        files_content: Dictionary mapping filename to content
        
    Raises:
        IOError: If file writing fails
    """
    for filename, content in files_content.items():
        file_path = os.path.join(character_dir, filename)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Successfully wrote V2 character file: {file_path}")
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {str(e)}")
            raise IOError(f"Failed to write character file: {filename}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan event handler.
    
    Performs initialization and cleanup tasks:
    - Startup: Logs server startup, validates configuration
    - Shutdown: Logs server shutdown, cleanup resources
    """
    # 神圣启动仪式 - 唤醒API服务器的机器灵魂...
    logger.info("Starting Warhammer 40k Simulator API server...")
    
    try:
        # 验证配置系统是否可达，确保机械知识的传输通道畅通...
        config = get_config()
        logger.info("Configuration loaded successfully")
        
        # 记录服务器启动仪式的完成，机器之神见证此刻...
        logger.info("Warhammer 40k Simulator API server started successfully")
        
    except Exception as e:
        logger.error(f"Error during server startup: {str(e)}")
        raise
    
    yield
    
    # 神圣关闭仪式 - 安抚API服务器的机器灵魂进入沉睡...
    logger.info("Shutting down Warhammer 40k Simulator API server...")


# 初始化FastAPI神圣应用，建立API信息接口神殿...
app = FastAPI(
    title="Warhammer 40k Simulator API",
    description="RESTful API for the Warhammer 40k Multi-Agent Simulator",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加压缩神圣屏障，减少数据流传输负担，保持机械灵魂高效运转...
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 添加CORS神圣屏障，允许网络客户端穿越数据流边界...
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse, responses={
    200: {"description": "API is running successfully"},
    500: {"description": "Internal server error", "model": ErrorResponse}
})
async def root() -> Dict[str, str]:
    """
    Root endpoint that provides API health check.
    
    Returns a JSON response indicating that the Warhammer 40k Simulator API
    is running and accessible. This endpoint serves as both a health check
    and a basic connectivity test for clients.
    
    Returns:
        Dict[str, str]: JSON response with success message
        
    Raises:
        HTTPException: 500 error if server is experiencing issues
    """
    try:
        logger.info("Root endpoint accessed - API health check")
        
        response_data = {
            "message": "Warhammer 40k Simulator API is running!"
        }
        
        logger.debug(f"Returning response: {response_data}")
        return response_data
        
    except Exception as e:
        logger.error(f"Error in root endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error occurred"
        )


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Detailed health check endpoint.
    
    Provides more comprehensive health information including:
    - API status
    - Configuration validation
    - System readiness
    
    Returns:
        Dict[str, Any]: Detailed health status information
    """
    try:
        logger.info("Health check endpoint accessed")
        
        # 构建基础健康状态圣物，展示机器灵魂的活力...
        health_status = {
            "status": "healthy",
            "api": "running",
            "timestamp": str(logging.Formatter().formatTime(logging.LogRecord(
                name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
            ))),
            "version": "1.0.0"
        }
        
        # 验证配置系统的可达性，确认机械知识传输管道的完整...
        try:
            config = get_config()
            health_status["config"] = "loaded"
        except Exception as config_error:
            logger.warning(f"Configuration check failed: {str(config_error)}")
            health_status["config"] = "error"
            health_status["status"] = "degraded"
        
        logger.debug(f"Health check response: {health_status}")
        return health_status
        
    except Exception as e:
        logger.error(f"Error in health check endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Health check failed"
        )


@app.get("/characters", 
         response_model=CharactersListResponse,
         summary="Get available characters",
         description="Retrieve a list of all available character names in the simulator",
         responses={
             200: {
                 "description": "Successfully retrieved character list",
                 "model": CharactersListResponse
             },
             404: {
                 "description": "Characters not found or not available",
                 "model": ErrorResponse
             },
             500: {
                 "description": "Internal server error",
                 "model": ErrorResponse
             }
         })
async def get_characters() -> CharactersListResponse:
    """
    Get list of available characters.
    
    Retrieves all character names that are available for use in the
    Warhammer 40k Multi-Agent Simulator. This endpoint provides the
    character roster that can be used for simulation scenarios.
    
    Returns:
        CharactersListResponse: JSON response containing array of character names
        
    Raises:
        HTTPException: 404 if characters directory not found
        HTTPException: 500 if an internal error occurs
    """
    try:
        logger.info("Characters endpoint accessed")
        
        # 获取角色目录圣域路径，沿循CharacterFactory的神圣逻辑...
        characters_path = _get_characters_directory_path()
        
        # 检视角色目录圣域是否存在，确认英灵殿的物理形态...
        if not os.path.exists(characters_path):
            logger.warning(f"Characters directory not found: {characters_path}")
            raise HTTPException(
                status_code=404,
                detail="Characters directory not found"
            )
        
        if not os.path.isdir(characters_path):
            logger.error(f"Characters path exists but is not a directory: {characters_path}")
            raise HTTPException(
                status_code=500,
                detail="Characters path is not a directory"
            )
        
        # 扫描目录以寻觅角色子域，遍历英灵殿中的每个圣室...
        try:
            characters = []
            for item in os.listdir(characters_path):
                item_path = os.path.join(characters_path, item)
                if os.path.isdir(item_path):
                    characters.append(item)
            
            # 执行排序仪式，确保角色名单的神圣秩序...
            characters.sort()
            
            logger.info(f"Found {len(characters)} available characters: {characters}")
            
            return CharactersListResponse(characters=characters)
            
        except PermissionError as e:
            logger.error(f"Permission denied accessing characters directory: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Permission denied accessing characters directory"
            )
        except OSError as e:
            logger.error(f"OS error accessing characters directory: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error accessing characters directory"
            )
        
    except HTTPException:
        # 重新抛出HTTP异常(404, 500)，将数据流创伤传递给上层净化机制...
        raise
    except Exception as e:
        logger.error(f"Unexpected error in characters endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve characters"
        )


@app.get("/characters/{character_name}",
         response_model=CharacterDetailResponse,
         summary="Get character details",
         description="Retrieve complete character context including narrative and structured data for a specific character",
         responses={
             200: {
                 "description": "Successfully retrieved character details",
                 "model": CharacterDetailResponse
             },
             404: {
                 "description": "Character not found",
                 "model": ErrorResponse
             },
             500: {
                 "description": "Internal server error",
                 "model": ErrorResponse
             }
         })
async def get_character_details(character_name: str) -> CharacterDetailResponse:
    """
    Get detailed information for a specific character.
    
    Retrieves the complete character context including:
    - All narrative context from markdown files (concatenated)
    - Structured data from YAML files (parsed and combined)
    - Character name validation
    - File count statistics
    
    Args:
        character_name (str): The name of the character to retrieve
        
    Returns:
        CharacterDetailResponse: Complete character context with narrative and structured data
        
    Raises:
        HTTPException: 404 if character not found
        HTTPException: 500 if an internal error occurs
    """
    try:
        logger.info(f"Character details endpoint accessed for character: {character_name}")
        
        # 验证角色名称的神圣性，确保其符合机械教条...
        if not character_name or not character_name.strip():
            logger.warning(f"Invalid character name: '{character_name}'")
            raise HTTPException(
                status_code=404,
                detail="Character not found"
            )
        
        # 初始化CharacterFactory神圣工厂，采用与/characters端点相同的路径解析仪式...
        characters_path = _get_characters_directory_path()
        
        # 为CharacterFactory使用来自项目根目录的相对路径圣标...
        base_character_path = "characters"
        character_factory = CharacterFactory(base_character_path)
        
        # 使用CharacterFactory神圣工厂创建角色实例，唤醒沉睡的人格机灵...
        try:
            persona_agent = character_factory.create_character(character_name.strip())
            logger.info(f"Successfully loaded character: {character_name}")
        
        except FileNotFoundError as e:
            logger.warning(f"Character not found: {character_name} - {str(e)}")
            raise HTTPException(
                status_code=404,
                detail=f"Character '{character_name}' not found"
            )
        except ValueError as e:
            logger.warning(f"Invalid character name: {character_name} - {str(e)}")
            raise HTTPException(
                status_code=404,
                detail="Character not found"
            )
        
        # 从人格代理中提取混合语境数据圣物，获取完整的角色灵魂信息...
        try:
            hybrid_context = persona_agent.character_data.get('hybrid_context', {})
            
            if not hybrid_context:
                logger.error(f"No hybrid context found for character: {character_name}")
                raise HTTPException(
                    status_code=500,
                    detail="Character data could not be loaded"
                )
            
            # 提取叙事语境圣物（连接的markdown内容），还原角色的传说记忆...
            narrative_context = hybrid_context.get('markdown_content', '')
            
            # 提取结构化数据圣物（解析的YAML文件），获取角色的机械属性...
            structured_data = hybrid_context.get('yaml_data', {})
            
            # 提取文件计数统计圣物，记录数据载体的数量信息...
            file_count_data = hybrid_context.get('file_count', {'md': 0, 'yaml': 0})
            file_count = FileCount(
                md=file_count_data.get('md', 0),
                yaml=file_count_data.get('yaml', 0)
            )
            
            # 构建响应圣物，将所有角色信息汇聚成完整的数据包...
            response = CharacterDetailResponse(
                narrative_context=narrative_context,
                structured_data=structured_data,
                character_name=character_name,
                file_count=file_count
            )
            
            logger.info(f"Successfully retrieved character details for: {character_name} "
                       f"(md files: {file_count.md}, yaml files: {file_count.yaml})")
            
            return response
            
        except Exception as e:
            logger.error(f"Error extracting character data for {character_name}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process character data"
            )
    
    except HTTPException:
        # 重新抛出HTTP异常(404, 500)，将数据流创伤传递给上层净化机制...
        raise
    except Exception as e:
        logger.error(f"Unexpected error in character details endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve character details"
        )


@app.post("/characters",
          response_model=CharacterCreationResponse,
          status_code=201,
          summary="Create new character with AI Scribe enhancement",
          description="Invoke the sacred AI Scribe ritual to create a complete character with contextual file uploads and Gemini API enhancement",
          responses={
              201: {
                  "description": "Character creation completed successfully with AI Scribe enhancement",
                  "model": CharacterCreationResponse,
                  "content": {
                      "application/json": {
                          "example": {
                              "name": "new_warrior",
                              "status": "ai_scribe_enhanced_complete",
                              "ai_scribe_enhanced": True,
                              "files_processed": 2
                          }
                      }
                  }
              },
              400: {
                  "description": "Invalid request parameters or validation errors",
                  "model": ErrorResponse,
                  "content": {
                      "application/json": {
                          "examples": {
                              "invalid_name_format": {
                                  "summary": "Invalid character name format",
                                  "value": {
                                      "error": "Validation Error",
                                      "detail": "Character name must contain only alphanumeric characters and underscores"
                                  }
                              },
                              "name_too_short": {
                                  "summary": "Character name too short",
                                  "value": {
                                      "error": "Validation Error",
                                      "detail": "Character name must be at least 3 characters long"
                                  }
                              },
                              "description_too_short": {
                                  "summary": "Character description too short",
                                  "value": {
                                      "error": "Validation Error",
                                      "detail": "Character description must contain at least 10 characters"
                                  }
                              },
                              "file_processing_error": {
                                  "summary": "File processing failed",
                                  "value": {
                                      "error": "File Processing Error",
                                      "detail": "Failed to process uploaded file: document.txt"
                                  }
                              }
                          }
                      }
                  }
              },
              409: {
                  "description": "Character name already exists",
                  "model": ErrorResponse,
                  "content": {
                      "application/json": {
                          "example": {
                              "error": "Conflict",
                              "detail": "Character 'warrior_name' already exists"
                          }
                      }
                  }
              },
              500: {
                  "description": "Internal server error during character creation",
                  "model": ErrorResponse,
                  "content": {
                      "application/json": {
                          "example": {
                              "error": "AI Scribe Error",
                              "detail": "Failed to complete AI Scribe enhancement process"
                          }
                      }
                  }
              }
          })
async def create_character_with_ai_scribe(
    name: str = Form(..., min_length=3, max_length=50, description="Character's sacred designation"),
    description: str = Form(..., min_length=10, max_length=2000, description="Character's narrative description"),
    files: TypingList[UploadFile] = File(default=[], description="Optional context files to enhance character creation")
) -> CharacterCreationResponse:
    """
    Create a new character using the sacred AI Scribe enhancement ritual.
    
    This enhanced endpoint combines user description with uploaded file context
    to invoke the Gemini API Master Context Engineer. The AI Scribe generates
    comprehensive character files following the V2 codex architecture:
    
    - 1_core.md: Core identity and physical description
    - 2_history.md: Detailed character backstory and events
    - 3_profile.yaml: Structured statistics and equipment data
    - 4_lore.md: Cultural background and philosophical details
    
    The AI Scribe process:
    1. Validates character name uniqueness and format compliance
    2. Processes uploaded files to extract contextual information
    3. Combines user description with file content for enhanced context
    4. Invokes Gemini API with Master Context Engineer prompt
    5. Parses generated content into structured V2 character files
    6. Writes complete character data to the character directory
    
    Args:
        name: Sacred character designation (3-50 chars, alphanumeric + underscores)
        description: Character's narrative description (10-2000 chars)
        files: Optional uploaded files for additional context (supports .txt, .md, .yaml, .json)
    
    Returns:
        CharacterCreationResponse: Creation confirmation with AI enhancement status
    
    Raises:
        HTTPException: 400 for validation errors or file processing failures
        HTTPException: 409 if character name already exists
        HTTPException: 500 for AI Scribe enhancement or internal errors
    """
    try:
        # Sanitize and validate input parameters
        name = name.strip().lower()
        description = description.strip()
        
        # Validate name format - sacred naming conventions
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            raise HTTPException(
                status_code=400,
                detail="Character name must contain only alphanumeric characters and underscores"
            )
        
        if len(description.split()) < 3:
            raise HTTPException(
                status_code=400,
                detail="Character description must contain at least 3 words"
            )
        
        logger.info(f"AI Scribe character creation initiated for: {name}")
        logger.info(f"Description length: {len(description)} characters, Files uploaded: {len(files)}")
        
        # Step 1: Validate character name uniqueness
        characters_path = _get_characters_directory_path()
        
        if os.path.exists(characters_path):
            character_dir_path = os.path.join(characters_path, name)
            if os.path.exists(character_dir_path):
                logger.warning(f"Character already exists: {name}")
                raise HTTPException(
                    status_code=409,
                    detail=f"Character '{name}' already exists"
                )
        
        # Step 2: Process uploaded files for context enhancement
        file_content = ""
        files_processed = 0
        
        if files:
            try:
                file_content = await _process_uploaded_files(files)
                files_processed = len(files)
                logger.info(f"Successfully processed {files_processed} uploaded files")
            except HTTPException:
                raise  # Re-raise HTTP exceptions from file processing
            except Exception as e:
                logger.error(f"Unexpected error processing files: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail="Failed to process uploaded files"
                )
        
        # Step 3: Create character directory structure
        try:
            os.makedirs(characters_path, exist_ok=True)
            character_dir_path = os.path.join(characters_path, name)
            os.makedirs(character_dir_path, exist_ok=False)
            logger.info(f"Created character directory: {character_dir_path}")
            
        except FileExistsError:
            logger.warning(f"Character directory already exists during creation: {name}")
            raise HTTPException(
                status_code=409,
                detail=f"Character '{name}' already exists"
            )
        except (PermissionError, OSError) as e:
            logger.error(f"Error creating character directory: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create character directory"
            )
        
        # Step 4: Invoke AI Scribe with Gemini API
        ai_scribe_enhanced = False
        api_key = _validate_gemini_api_key()
        
        if api_key:
            try:
                # Create Master Context Engineer prompt
                prompt = _create_master_context_engineer_prompt(name, description, file_content)
                
                logger.info(f"Invoking AI Scribe with prompt length: {len(prompt)} characters")
                
                # Make Gemini API call
                generated_content = _make_gemini_api_request(prompt, api_key, timeout=60)
                
                if generated_content:
                    logger.info(f"AI Scribe generated content: {len(generated_content)} characters")
                    
                    # Parse generated content into files
                    parsed_files = _parse_generated_content(generated_content)
                    
                    # Write V2 character files
                    await _write_v2_character_files(character_dir_path, parsed_files)
                    
                    ai_scribe_enhanced = True
                    logger.info(f"AI Scribe enhancement completed successfully for: {name}")
                    
                else:
                    logger.warning("AI Scribe returned empty response, falling back to basic creation")
                    
            except Exception as e:
                logger.error(f"AI Scribe enhancement failed: {str(e)}")
                # Continue with basic character creation as fallback
        else:
            logger.info("Gemini API key not available, proceeding with basic character creation")
        
        # Step 5: Fallback to basic character creation if AI Scribe failed
        if not ai_scribe_enhanced:
            try:
                # Create basic character file as fallback
                basic_md_path = os.path.join(character_dir_path, f"character_{name}.md")
                basic_md_content = f"""# Character Sheet: {name.title()}

## Core Identity
- **Name**: {name.title()}
- **Origin**: API Created
- **Status**: Basic Creation (AI Scribe unavailable)

## Description
{description}

{file_content if file_content else ""}

*Basic character template - AI Scribe enhancement was not available*
"""
                
                with open(basic_md_path, 'w', encoding='utf-8') as f:
                    f.write(basic_md_content)
                
                # Create basic stats file
                basic_stats_path = os.path.join(character_dir_path, "stats.yaml")
                basic_stats_content = f"""character:
  name: "{name.title()}"
  origin: "API Created"
  status: "Basic Template"

combat_stats:
  marksmanship: 5
  melee: 5
  tactics: 5
  leadership: 5
  endurance: 5

psychological_profile:
  loyalty: 5
  aggression: 5
  caution: 5
  morale: 5
"""
                
                with open(basic_stats_path, 'w', encoding='utf-8') as f:
                    f.write(basic_stats_content)
                
                logger.info(f"Basic character creation completed for: {name}")
                
            except (IOError, OSError) as e:
                # Clean up directory on failure
                logger.error(f"Error creating basic character files: {str(e)}")
                try:
                    if os.path.exists(character_dir_path):
                        shutil.rmtree(character_dir_path)
                        logger.info(f"Cleaned up character directory after failure: {character_dir_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Could not clean up character directory: {str(cleanup_error)}")
                
                raise HTTPException(
                    status_code=500,
                    detail="Failed to complete character creation process"
                )
        
        # Step 6: Return success response
        status = "ai_scribe_enhanced_complete" if ai_scribe_enhanced else "basic_creation_complete"
        
        logger.info(f"Character creation completed for {name}: {status}")
        
        return CharacterCreationResponse(
            name=name,
            status=status,
            ai_scribe_enhanced=ai_scribe_enhanced,
            files_processed=files_processed
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error during AI Scribe character creation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to complete AI Scribe character creation process"
        )


@app.post("/simulations",
          response_model=SimulationResponse,
          summary="Run character simulation",
          description="Execute a Warhammer 40k character simulation with specified participants and return the generated narrative",
          responses={
              200: {
                  "description": "Simulation completed successfully",
                  "model": SimulationResponse,
                  "content": {
                      "application/json": {
                          "example": {
                              "story": "In the grim darkness of the far future, Commissar Krieg and the Ork Warboss clashed in epic battle...",
                              "participants": ["krieg", "ork"],
                              "turns_executed": 3,
                              "duration_seconds": 15.7
                          }
                      }
                  }
              },
              400: {
                  "description": "Invalid request parameters or validation errors",
                  "model": ErrorResponse,
                  "content": {
                      "application/json": {
                          "examples": {
                              "insufficient_characters": {
                                  "summary": "Not enough characters",
                                  "value": {
                                      "error": "Validation Error",
                                      "detail": "At least 2 character names are required"
                                  }
                              },
                              "invalid_turns": {
                                  "summary": "Invalid turn count",
                                  "value": {
                                      "error": "Validation Error", 
                                      "detail": "Turns must be between 1 and 10"
                                  }
                              },
                              "invalid_style": {
                                  "summary": "Invalid narrative style",
                                  "value": {
                                      "error": "Validation Error",
                                      "detail": "Narrative style must be one of: epic, detailed, concise"
                                  }
                              }
                          }
                      }
                  }
              },
              404: {
                  "description": "One or more characters not found",
                  "model": ErrorResponse,
                  "content": {
                      "application/json": {
                          "example": {
                              "error": "Characters Not Found",
                              "detail": "Characters not found: unknown_character, invalid_name"
                          }
                      }
                  }
              },
              500: {
                  "description": "Internal server error during simulation",
                  "model": ErrorResponse,
                  "content": {
                      "application/json": {
                          "example": {
                              "error": "Simulation Error",
                              "detail": "Failed to execute simulation due to internal error"
                          }
                      }
                  }
              }
          })
async def run_simulation(request: SimulationRequest) -> SimulationResponse:
    """
    Execute a Warhammer 40k character simulation.
    
    Runs a multi-agent simulation with the specified characters, generating
    an epic narrative through the interaction of PersonaAgents, DirectorAgent,
    and ChroniclerAgent. The simulation executes for the specified number of
    turns and returns the final narrative story.
    
    The simulation process:
    1. Validates all character names exist and are available
    2. Initializes PersonaAgents for each character
    3. Runs the simulation for the specified number of turns
    4. Generates the final narrative using ChroniclerAgent
    5. Returns the complete story with execution metadata
    
    Args:
        request (SimulationRequest): Simulation parameters including:
            - character_names: List of 2-6 character names to participate
            - turns: Optional number of turns (1-10, defaults to config value)
            - narrative_style: Optional style preference (epic/detailed/concise)
    
    Returns:
        SimulationResponse: Complete simulation results including:
            - story: Final narrative generated by ChroniclerAgent
            - participants: List of characters that participated
            - turns_executed: Actual number of turns completed
            - duration_seconds: Total simulation execution time
    
    Raises:
        HTTPException: 400 for validation errors (invalid parameters)
        HTTPException: 404 if any specified characters are not found
        HTTPException: 500 for internal simulation errors
    """
    start_time = time.time()
    
    logger.info(f"Simulation endpoint accessed with characters: {request.character_names}")
    logger.info(f"Simulation parameters - turns: {request.turns}, style: {request.narrative_style}")
    
    try:
        # 第一步神圣仪式：获取配置以确定默认回合数值，遵循机械教条的参数...
        config = get_config()
        turns_to_execute = request.turns if request.turns is not None else config.simulation.turns
        
        logger.info(f"Executing simulation for {turns_to_execute} turns")
        
        # 第二步神圣仪式：验证并创建角色实例，召唤参战英灵的机器灵魂...
        character_factory = CharacterFactory()
        character_agents = []
        not_found_characters = []
        
        for character_name in request.character_names:
            try:
                logger.info(f"Creating character: {character_name}")
                agent = character_factory.create_character(character_name)
                character_agents.append(agent)
                logger.info(f"Successfully created agent for {character_name}: {agent.agent_id}")
            except FileNotFoundError as e:
                logger.warning(f"Character not found: {character_name}")
                not_found_characters.append(character_name)
            except Exception as e:
                logger.error(f"Error creating character {character_name}: {str(e)}")
                not_found_characters.append(character_name)
        
        # 检视是否有角色未能寻获，确认所有参战英灵是否准备就绪...
        if not_found_characters:
            logger.error(f"Characters not found: {not_found_characters}")
            raise HTTPException(
                status_code=404,
                detail=f"Characters not found: {', '.join(not_found_characters)}"
            )
        
        # 第三步神圣仪式：初始化DirectorAgent指挥代理，创建独特的战役记录圣典...
        simulation_id = str(uuid.uuid4())[:8]
        campaign_log_path = f"simulation_{simulation_id}_campaign_log.md"
        
        logger.info(f"Initializing DirectorAgent with campaign log: {campaign_log_path}")
        director = DirectorAgent(campaign_log_path=campaign_log_path)
        
        # 第四步神圣仪式：将所有角色代理注册至指挥官，建立指挥链路...
        for agent in character_agents:
            success = director.register_agent(agent)
            if not success:
                logger.error(f"Failed to register agent: {agent.agent_id}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to register character agent: {agent.agent_id}"
                )
        
        logger.info(f"Successfully registered {len(character_agents)} agents with DirectorAgent")
        
        # 第五步神圣仪式：执行模拟回合，让英灵们在虚拟战场中展开史诗冲突...
        logger.info(f"Starting simulation execution for {turns_to_execute} turns")
        turns_executed = 0
        
        for turn in range(turns_to_execute):
            try:
                logger.info(f"Executing turn {turn + 1}/{turns_to_execute}")
                turn_result = director.run_turn()
                turns_executed += 1
                logger.info(f"Turn {turn + 1} completed successfully")
            except Exception as e:
                logger.error(f"Error during turn {turn + 1}: {str(e)}")
                # 继续执行剩余回合而非完全失败，机器灵魂坚韧不屈...
                continue
        
        logger.info(f"Simulation execution completed: {turns_executed}/{turns_to_execute} turns successful")
        
        # 第六步神圣仪式：使用ChroniclerAgent史官代理生成叙事，记录英雄传说...
        logger.info("Starting narrative generation with ChroniclerAgent")
        
        # 若提供了叙事风格则进行设定，调整史官的记录模式...
        narrative_style = request.narrative_style or "epic"
        # 将API叙事风格映射至ChroniclerAgent风格，转换用户意图为机械指令...
        style_mapping = {
            "epic": "grimdark_dramatic",
            "detailed": "grimdark_dramatic", 
            "concise": "tactical"
        }
        chronicler_style = style_mapping.get(narrative_style, "grimdark_dramatic")
        
        chronicler = ChroniclerAgent(narrative_style=chronicler_style)
        
        # 从战役记录圣典生成故事，让史官代理编织英雄传奇...
        try:
            story = chronicler.transcribe_log(campaign_log_path)
            logger.info(f"Narrative generation completed: {len(story)} characters generated")
        except Exception as e:
            logger.error(f"Error during narrative generation: {str(e)}")
            # 提供后备叙事，即使史官代理失效也要保留英雄事迹的基本记录...
            story = (
                f"In the grim darkness of the far future, {', '.join(request.character_names)} "
                f"engaged in epic conflict across {turns_executed} turns of battle. "
                f"Though the full chronicle was lost to the chaos of war, their deeds "
                f"shall be remembered in the annals of the Imperium."
            )
        
        # 第七步神圣仪式：计算执行时间并构建响应，完成整个模拟循环...
        end_time = time.time()
        duration_seconds = round(end_time - start_time, 3)
        
        response = SimulationResponse(
            story=story,
            participants=request.character_names.copy(),
            turns_executed=turns_executed,
            duration_seconds=duration_seconds
        )
        
        logger.info(f"Simulation completed successfully:")
        logger.info(f"  - Characters: {len(request.character_names)}")
        logger.info(f"  - Turns executed: {turns_executed}/{turns_to_execute}")
        logger.info(f"  - Duration: {duration_seconds} seconds")
        logger.info(f"  - Story length: {len(story)} characters")
        
        # 清理战役记录文件（可选），净化临时数据圣物...
        try:
            if os.path.exists(campaign_log_path):
                os.remove(campaign_log_path)
                logger.debug(f"Cleaned up campaign log: {campaign_log_path}")
        except Exception as e:
            logger.warning(f"Could not clean up campaign log {campaign_log_path}: {e}")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (404, 500) as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error during simulation: {str(e)}")
        # 为错误响应计算部分持续时间，记录失败仪式的执行时长...
        error_duration = round(time.time() - start_time, 3)
        raise HTTPException(
            status_code=500,
            detail=f"Simulation execution failed: {str(e)}"
        )


@app.get("/campaigns",
         response_model=CampaignsListResponse,
         summary="Get available campaigns",
         description="Retrieve a list of all available campaign directories in the sacred codex",
         responses={
             200: {
                 "description": "Successfully retrieved campaign list",
                 "model": CampaignsListResponse
             },
             404: {
                 "description": "Campaigns directory not found or not available",
                 "model": ErrorResponse
             },
             500: {
                 "description": "Internal server error",
                 "model": ErrorResponse
             }
         })
async def get_campaigns() -> CampaignsListResponse:
    """
    Get list of available campaigns.
    
    Sacred ritual to retrieve all campaign directories from the blessed
    codex/campaigns storage realm. Each campaign represents a complete
    narrative scenario ready for simulation deployment.
    
    Returns:
        CampaignsListResponse: JSON response containing array of campaign names
        
    Raises:
        HTTPException: 404 if campaigns directory not found
        HTTPException: 500 if an internal error occurs
    """
    try:
        logger.info("Campaigns endpoint accessed - retrieving sacred campaign codex")
        
        # 获取战役目录圣域路径，定位战役典籍的神圣殿堂...
        campaigns_path = _get_campaigns_directory_path()
        
        # 检视战役目录圣域是否存在于物理形态中...
        if not os.path.exists(campaigns_path):
            logger.warning(f"Campaigns directory not found: {campaigns_path}")
            raise HTTPException(
                status_code=404,
                detail="Campaigns directory not found - the sacred codex awaits initialization"
            )
        
        if not os.path.isdir(campaigns_path):
            logger.error(f"Campaigns path exists but is not a directory: {campaigns_path}")
            raise HTTPException(
                status_code=500,
                detail="Campaigns path is not a directory"
            )
        
        # 扫描目录寻觅战役子域，遍历战役典籍中的每个神圣卷轴...
        try:
            campaigns = []
            for item in os.listdir(campaigns_path):
                item_path = os.path.join(campaigns_path, item)
                if os.path.isdir(item_path):
                    campaigns.append(item)
            
            # 执行排序仪式，确保战役名单的神圣秩序...
            campaigns.sort()
            
            logger.info(f"Found {len(campaigns)} available campaigns: {campaigns}")
            
            return CampaignsListResponse(campaigns=campaigns)
            
        except PermissionError as e:
            logger.error(f"Permission denied accessing campaigns directory: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Permission denied accessing campaigns directory"
            )
        except OSError as e:
            logger.error(f"OS error accessing campaigns directory: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error accessing campaigns directory"
            )
        
    except HTTPException:
        # 重新抛出HTTP异常，将数据流创伤传递给上层净化机制...
        raise
    except Exception as e:
        logger.error(f"Unexpected error in campaigns endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve campaigns"
        )


def _generate_campaign_brief(campaign_name: str, description: str) -> Optional[str]:
    """
    Generate AI-powered campaign brief using Gemini API.
    
    Sacred ritual to invoke the machine-spirit wisdom for campaign brief generation.
    Uses the blessed Gemini API to transform campaign description into detailed
    mission briefing following Imperial doctrine.
    
    Args:
        campaign_name: Sacred campaign designation
        description: Campaign overview for brief generation
        
    Returns:
        Optional[str]: Generated campaign brief or None if generation failed
    """
    try:
        logger.info(f"Initiating AI campaign brief generation for: {campaign_name}")
        
        # Construct sacred prompt for campaign brief generation
        prompt = f"""
        # SACRED MISSION BRIEFING GENERATION PROTOCOL

        **Campaign Designation**: {campaign_name}
        **Mission Overview**: {description}

        As an Imperial Strategist and Campaign Coordinator, generate a comprehensive mission briefing for this Warhammer 40,000 campaign. The briefing should follow Imperial military doctrine and include:

        ## Structure Required:
        1. **Campaign Brief**: [Campaign Name]
        2. **Mission Overview** - Strategic situation summary
        3. **Primary Objectives** - 3-5 numbered mission goals
        4. **Secondary Objectives** - 2-3 additional tactical goals
        5. **Threat Assessment** - Enemy forces and environmental hazards
        6. **Resources Assigned** - Available Imperial forces and equipment
        7. **Rules of Engagement** - Tactical constraints and protocols
        8. **Expected Duration** - Campaign timeline estimate

        ## Tone and Style:
        - Use authentic Warhammer 40k terminology and atmosphere
        - Maintain Imperial military briefing format
        - Include appropriate faction references
        - Balance grimdark atmosphere with tactical clarity
        - Ensure the briefing feels authentic to the 40k universe

        Generate the complete mission briefing now:
        """
        
        # Invoke the sacred Gemini API for brief generation
        brief_response = _make_gemini_api_request(prompt)
        
        if brief_response:
            logger.info(f"Successfully generated campaign brief for: {campaign_name}")
            return brief_response.strip()
        else:
            logger.warning(f"Gemini API failed to generate brief for: {campaign_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating campaign brief: {str(e)}")
        return None


def _save_campaign_brief(campaign_directory: str, campaign_name: str, brief_content: str) -> bool:
    """
    Save generated campaign brief to the campaign directory.
    
    Sacred ritual to inscribe the generated mission briefing into the
    campaign codex for future reference by Imperial command.
    
    Args:
        campaign_directory: Path to campaign directory
        campaign_name: Campaign designation for filename
        brief_content: Generated brief content to save
        
    Returns:
        bool: True if brief saved successfully, False otherwise
    """
    try:
        brief_filename = f"{campaign_name}_mission_brief.md"
        brief_filepath = os.path.join(campaign_directory, brief_filename)
        
        with open(brief_filepath, 'w', encoding='utf-8') as f:
            f.write(brief_content)
        
        logger.info(f"Campaign brief saved successfully: {brief_filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save campaign brief: {str(e)}")
        return False


@app.post("/campaigns",
          response_model=CampaignCreationResponse,
          status_code=201,
          summary="Create new campaign directory with AI-powered brief generation",
          description="Invoke the sacred campaign creation ritual to establish a new campaign in the codex with optional AI-generated mission briefing",
          responses={
              201: {
                  "description": "Campaign directory created successfully",
                  "model": CampaignCreationResponse,
                  "content": {
                      "application/json": {
                          "examples": {
                              "with_brief": {
                                  "summary": "Campaign created with AI-generated brief",
                                  "value": {
                                      "campaign_name": "serenitas_shadow",
                                      "status": "created",
                                      "directory_path": "/path/to/codex/campaigns/serenitas_shadow",
                                      "brief_generated": True
                                  }
                              },
                              "without_brief": {
                                  "summary": "Campaign created without brief generation",
                                  "value": {
                                      "campaign_name": "simple_campaign",
                                      "status": "created", 
                                      "directory_path": "/path/to/codex/campaigns/simple_campaign",
                                      "brief_generated": False
                                  }
                              }
                          }
                      }
                  }
              },
              400: {
                  "description": "Invalid campaign name format or validation errors",
                  "model": ErrorResponse,
                  "content": {
                      "application/json": {
                          "examples": {
                              "invalid_name_format": {
                                  "summary": "Invalid campaign name format",
                                  "value": {
                                      "error": "Validation Error",
                                      "detail": "Campaign name must contain only alphanumeric characters and underscores"
                                  }
                              },
                              "name_too_short": {
                                  "summary": "Campaign name too short",
                                  "value": {
                                      "error": "Validation Error",
                                      "detail": "Campaign name must be at least 3 characters long"
                                  }
                              }
                          }
                      }
                  }
              },
              409: {
                  "description": "Campaign already exists",
                  "model": ErrorResponse,
                  "content": {
                      "application/json": {
                          "example": {
                              "error": "Conflict",
                              "detail": "Campaign 'serenitas_shadow' already exists"
                          }
                      }
                  }
              },
              500: {
                  "description": "Internal server error during campaign creation",
                  "model": ErrorResponse,
                  "content": {
                      "application/json": {
                          "example": {
                              "error": "Campaign Creation Error",
                              "detail": "Failed to create campaign directory"
                          }
                      }
                  }
              }
          })
async def create_campaign(request: CampaignCreationRequest) -> CampaignCreationResponse:
    """
    Create a new campaign directory in the sacred codex.
    
    Sacred ritual to establish a new campaign storage realm within the
    blessed codex/campaigns directory structure. Each campaign directory
    serves as a container for all scenario data, character interactions,
    and narrative documentation.
    
    Args:
        request (CampaignCreationRequest): Campaign creation parameters including:
            - campaign_name: Sacred designation for the new campaign (3-50 chars)
    
    Returns:
        CampaignCreationResponse: Confirmation of campaign creation with:
            - campaign_name: Confirmed campaign designation
            - status: Creation process status
            - directory_path: Full path to created campaign directory
    
    Raises:
        HTTPException: 400 for validation errors (invalid name format)
        HTTPException: 409 if campaign name already exists
        HTTPException: 500 for internal directory creation errors
    """
    try:
        campaign_name = request.campaign_name
        logger.info(f"Campaign creation ritual initiated for: {campaign_name}")
        
        # 第一步神圣仪式：获取战役根目录路径，定位典籍存储殿堂...
        campaigns_root_path = _get_campaigns_directory_path()
        campaign_directory_path = os.path.join(campaigns_root_path, campaign_name)
        
        # 第二步神圣仪式：验证战役名称的唯一性，确保神圣典籍无重复...
        if os.path.exists(campaign_directory_path):
            logger.warning(f"Campaign already exists: {campaign_name}")
            raise HTTPException(
                status_code=409,
                detail=f"Campaign '{campaign_name}' already exists"
            )
        
        # 第三步神圣仪式：创建战役目录结构，建立神圣存储殿堂...
        try:
            # 确保父目录存在，为战役典籍建立基础框架...
            os.makedirs(campaigns_root_path, exist_ok=True)
            logger.debug(f"Ensured campaigns root directory exists: {campaigns_root_path}")
            
            # 创建具体的战役目录，为特定战役建立专属圣域...
            os.makedirs(campaign_directory_path, exist_ok=False)
            logger.info(f"Successfully created campaign directory: {campaign_directory_path}")
            
        except FileExistsError:
            # 双重检查防护，确保战役目录创建过程的原子性...
            logger.warning(f"Campaign directory already exists during creation: {campaign_name}")
            raise HTTPException(
                status_code=409,
                detail=f"Campaign '{campaign_name}' already exists"
            )
        except (PermissionError, OSError) as e:
            logger.error(f"Error creating campaign directory: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create campaign directory - insufficient permissions or disk space"
            )
        
        # 第四步神圣仪式：尝试生成AI驱动的战役简报，调用机械神谕的智慧...
        brief_generated = False
        if request.description and request.description.strip():
            logger.info(f"Attempting AI brief generation for campaign: {campaign_name}")
            
            generated_brief = _generate_campaign_brief(campaign_name, request.description)
            if generated_brief:
                # 成功生成简报，将其保存到战役目录中...
                if _save_campaign_brief(campaign_directory_path, campaign_name, generated_brief):
                    brief_generated = True
                    logger.info(f"AI campaign brief generated and saved for: {campaign_name}")
                else:
                    logger.warning(f"Brief generated but failed to save for: {campaign_name}")
            else:
                logger.warning(f"Failed to generate AI brief for: {campaign_name}")
        else:
            logger.debug(f"No description provided, skipping brief generation for: {campaign_name}")
        
        # 第五步神圣仪式：构建成功响应圣物，确认战役创建仪式完成...
        response = CampaignCreationResponse(
            campaign_name=campaign_name,
            status="created",
            directory_path=campaign_directory_path,
            brief_generated=brief_generated
        )
        
        logger.info(f"Campaign creation completed successfully for: {campaign_name}")
        logger.info(f"Campaign directory path: {campaign_directory_path}")
        logger.info(f"AI brief generated: {brief_generated}")
        
        return response
        
    except HTTPException:
        # 重新抛出HTTP异常，保持错误处理的纯净性...
        raise
    except Exception as e:
        logger.error(f"Unexpected error during campaign creation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to complete campaign creation process"
        )


# 错误处理净化仪式 - 安抚受损的数据流灵魂...
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions that are not from FastAPI endpoints (e.g., missing routes)."""
    if exc.status_code == 404:
        # 检查这是否为有效端点路径但存在业务逻辑404错误
        if (request.url.path in ["/characters", "/simulations", "/campaigns"] or 
            request.url.path.startswith("/characters/")):
            # 这是有效端点的业务逻辑404错误，直接传递原始详情
            return JSONResponse(
                status_code=404,
                content={"detail": exc.detail}
            )
        else:
            # 这是真正缺失的端点
            logger.warning(f"404 error for path: {request.url.path}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Not Found", 
                    "detail": "The requested endpoint does not exist"
                }
            )
    # 对于其他HTTP异常，使用默认处理
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 Internal Server errors."""
    logger.error(f"500 error for path: {request.url.path} - {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred"
        }
    )


def run_server(host: str = "127.0.0.1", port: int = 8000, debug: bool = False):
    """
    Run the FastAPI server using uvicorn.
    
    Args:
        host (str): Host address to bind the server
        port (int): Port number to run the server on
        debug (bool): Enable debug mode with auto-reload
    """
    logger.info(f"Starting FastAPI server on {host}:{port}")
    
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )


if __name__ == "__main__":
    # 开发服务器配置圣典...
    # 生产环境请使用properly ASGI服务器如uvicorn，配置适当的机械参数...
    run_server(host="127.0.0.1", port=8000, debug=True)