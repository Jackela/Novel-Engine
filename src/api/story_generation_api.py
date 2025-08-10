#!/usr/bin/env python3
"""
++ SACRED STORY GENERATION API BLESSED BY NARRATIVE MASTERY ++
==============================================================

Holy API endpoints for story export, narrative generation, and content
formatting serving User Story 5 with comprehensive customization
blessed by the Omnissiah's creative wisdom.

++ THROUGH STORIES, INTERACTIONS ACHIEVE ETERNAL PRESERVATION ++

Story Implementation: Story Export & Narrative Generation (Story 5)
Sacred Author: Dev Agent James
万机之神保佑叙事生成 (May the Omnissiah bless narrative generation)
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from dataclasses import asdict
from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid
import tempfile
import os
from pathlib import Path as FilePath
from io import BytesIO
import zipfile

# Import blessed framework components
from src.core.system_orchestrator import SystemOrchestrator
from src.templates.dynamic_template_engine import DynamicTemplateEngine, TemplateContext
from src.memory.memory_query_engine import MemoryQueryEngine, QueryContext
from src.core.data_models import StandardResponse, MemoryItem, MemoryType

# Sacred logging
logger = logging.getLogger(__name__)


class NarrativePerspective(str, Enum):
    """Narrative perspective options for story generation."""
    FIRST_PERSON = "first_person"
    THIRD_PERSON_LIMITED = "third_person_limited"
    THIRD_PERSON_OMNISCIENT = "third_person_omniscient"
    MULTIPLE_POV = "multiple_pov"


class StoryFormat(str, Enum):
    """Available story export formats."""
    PLAIN_TEXT = "txt"
    MARKDOWN = "md"
    HTML = "html"
    PDF = "pdf"
    WORD = "docx"
    EPUB = "epub"
    JSON = "json"


class StoryTone(str, Enum):
    """Story tone and style options."""
    DRAMATIC = "dramatic"
    CASUAL = "casual"
    FORMAL = "formal"
    HUMOROUS = "humorous"
    MYSTERIOUS = "mysterious"
    ROMANTIC = "romantic"
    ACTION = "action"
    PHILOSOPHICAL = "philosophical"


class StoryGenerationRequest(BaseModel):
    """Request model for story generation with comprehensive customization."""
    # Source selection
    project_id: Optional[str] = Field(None, description="Project ID to export (if using project system)")
    characters: List[str] = Field(..., min_items=1, description="Character IDs to include in story")
    
    # Time range selection
    start_date: Optional[datetime] = Field(None, description="Start date for interactions to include")
    end_date: Optional[datetime] = Field(None, description="End date for interactions to include") 
    interaction_ids: Optional[List[str]] = Field(None, description="Specific interaction IDs to include")
    
    # Story configuration
    title: str = Field("", max_length=200, description="Story title")
    subtitle: str = Field("", max_length=300, description="Story subtitle")
    
    # Format and style
    format: StoryFormat = Field(StoryFormat.MARKDOWN, description="Output format")
    perspective: NarrativePerspective = Field(NarrativePerspective.THIRD_PERSON_OMNISCIENT, description="Narrative perspective")
    tone: StoryTone = Field(StoryTone.DRAMATIC, description="Story tone and style")
    language: str = Field("english", description="Output language")
    
    # Content customization
    include_internal_thoughts: bool = Field(True, description="Include character internal thoughts")
    include_relationship_dynamics: bool = Field(True, description="Include relationship evolution")
    include_environmental_context: bool = Field(True, description="Include environmental descriptions")
    include_equipment_details: bool = Field(False, description="Include equipment usage details")
    include_memory_flashbacks: bool = Field(False, description="Include memory-triggered flashbacks")
    
    # Quality settings
    minimum_length: int = Field(1000, ge=100, le=50000, description="Minimum story length in words")
    maximum_length: int = Field(10000, ge=500, le=100000, description="Maximum story length in words")
    coherence_level: float = Field(0.8, ge=0.0, le=1.0, description="Story coherence requirement")
    detail_level: float = Field(0.7, ge=0.0, le=1.0, description="Level of detail (0=summary, 1=verbose)")
    
    # Structure settings
    chapter_breaks: bool = Field(False, description="Insert chapter breaks")
    scene_breaks: bool = Field(True, description="Insert scene breaks")
    include_prologue: bool = Field(False, description="Include prologue")
    include_epilogue: bool = Field(False, description="Include epilogue")
    
    # Metadata
    author_name: str = Field("Dynamic Context Engine", max_length=100, description="Author attribution")
    generation_notes: str = Field("", max_length=1000, description="Notes about story generation")
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range."""
        if v and 'start_date' in values and values['start_date']:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
        return v
    
    @validator('maximum_length')
    def validate_length_range(cls, v, values):
        """Validate length range."""
        if 'minimum_length' in values and values['minimum_length']:
            if v <= values['minimum_length']:
                raise ValueError('Maximum length must be greater than minimum length')
        return v


class StoryGenerationResponse(BaseModel):
    """Response model for story generation requests."""
    generation_id: str
    status: str  # initiated, processing, completed, failed
    message: str
    
    # Request details
    characters: List[str]
    format: str
    estimated_completion: Optional[datetime] = None
    
    # Progress tracking
    progress_percentage: float = 0.0
    current_phase: str = ""
    phases_completed: int = 0
    total_phases: int = 0
    
    # Results (available when completed)
    download_url: Optional[str] = None
    preview_text: Optional[str] = None
    word_count: Optional[int] = None
    character_count: Optional[int] = None
    
    # Quality metrics
    coherence_score: Optional[float] = None
    readability_score: Optional[float] = None
    character_consistency_score: Optional[float] = None
    
    # Metadata
    created_at: datetime
    completed_at: Optional[datetime] = None
    file_size_bytes: Optional[int] = None


class StoryContent(BaseModel):
    """Model for generated story content."""
    title: str
    subtitle: str
    content: str
    metadata: Dict[str, Any]
    
    # Statistics
    word_count: int
    character_count: int
    paragraph_count: int
    dialogue_percentage: float
    
    # Quality metrics
    coherence_score: float
    readability_score: float
    character_consistency_score: float
    
    # Generation info
    generation_time_seconds: float
    characters_featured: List[str]
    interactions_included: int
    time_period_covered: str


class StoryLibraryResponse(BaseModel):
    """Response model for story library listings."""
    stories: List[Dict[str, Any]]
    total_count: int
    filters_applied: Dict[str, Any]
    
    # Statistics
    total_word_count: int
    average_story_length: float
    most_featured_characters: List[str]
    generation_dates: List[datetime]


class StoryGenerationAPI:
    """
    ++ SACRED STORY GENERATION API IMPLEMENTATION BLESSED BY NARRATIVE EXCELLENCE ++
    
    Comprehensive API for story export, narrative generation, and content formatting
    implementing User Story 5: Story Export & Narrative Generation.
    """
    
    def __init__(self, orchestrator: SystemOrchestrator):
        """Initialize story generation API with system orchestrator."""
        self.orchestrator = orchestrator
        self.active_generations: Dict[str, Dict[str, Any]] = {}
        self.story_library: Dict[str, StoryContent] = {}
        self.temp_files: Dict[str, str] = {}  # Track temporary files for cleanup
        
        # Create story templates directory
        self.template_dir = FilePath("src/templates/story_templates")
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("++ Story Generation API initialized and blessed ++")
    
    
    def setup_routes(self, app: FastAPI):
        """Set up API routes for story generation."""
        
        @app.post("/api/v1/stories/generate", response_model=StoryGenerationResponse)
        async def generate_story(request: StoryGenerationRequest, background_tasks: BackgroundTasks):
            """
            Generate a story from character interactions with comprehensive customization.
            
            **Story Implementation**: Story Export & Narrative Generation
            **Features**: Multiple formats, narrative perspectives, quality control
            """
            try:
                # Validate characters exist
                for character_id in request.characters:
                    if character_id not in self.orchestrator.active_agents:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Character '{character_id}' not found"
                        )
                
                # Generate unique generation ID
                generation_id = f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
                
                # Estimate completion time based on complexity
                estimated_duration = self._estimate_generation_time(request)
                estimated_completion = datetime.now() + timedelta(seconds=estimated_duration)
                
                # Initialize generation state
                generation_state = {
                    "request": request,
                    "status": "initiated",
                    "created_at": datetime.now(),
                    "progress_percentage": 0.0,
                    "current_phase": "Initializing",
                    "phases_completed": 0,
                    "total_phases": 7,  # Analysis, Gathering, Structuring, Writing, Formatting, Quality, Export
                    "estimated_completion": estimated_completion
                }
                
                self.active_generations[generation_id] = generation_state
                
                # Start background generation
                background_tasks.add_task(self._generate_story_async, generation_id)
                
                # Create response
                response = StoryGenerationResponse(
                    generation_id=generation_id,
                    status="initiated",
                    message="Story generation initiated successfully",
                    characters=request.characters,
                    format=request.format.value,
                    estimated_completion=estimated_completion,
                    progress_percentage=0.0,
                    current_phase="Initializing",
                    phases_completed=0,
                    total_phases=7,
                    created_at=datetime.now()
                )
                
                return response
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"++ ERROR initiating story generation: {str(e)} ++")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        
        @app.get("/api/v1/stories/generation/{generation_id}", response_model=StoryGenerationResponse)
        async def get_generation_status(generation_id: str = Path(..., description="Generation ID")):
            """
            Get story generation status and progress.
            
            **Story Implementation**: Generation progress monitoring
            """
            try:
                if generation_id not in self.active_generations:
                    raise HTTPException(status_code=404, detail="Generation not found")
                
                state = self.active_generations[generation_id]
                request = state["request"]
                
                # Create response from state
                response = StoryGenerationResponse(
                    generation_id=generation_id,
                    status=state["status"],
                    message=state.get("message", ""),
                    characters=request.characters,
                    format=request.format.value,
                    estimated_completion=state.get("estimated_completion"),
                    progress_percentage=state["progress_percentage"],
                    current_phase=state["current_phase"],
                    phases_completed=state["phases_completed"],
                    total_phases=state["total_phases"],
                    download_url=state.get("download_url"),
                    preview_text=state.get("preview_text"),
                    word_count=state.get("word_count"),
                    character_count=state.get("character_count"),
                    coherence_score=state.get("coherence_score"),
                    readability_score=state.get("readability_score"),
                    character_consistency_score=state.get("character_consistency_score"),
                    created_at=state["created_at"],
                    completed_at=state.get("completed_at"),
                    file_size_bytes=state.get("file_size_bytes")
                )
                
                return response
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"++ ERROR getting generation status: {str(e)} ++")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        
        @app.get("/api/v1/stories/{story_id}/download")
        async def download_story(
            story_id: str = Path(..., description="Story ID or generation ID"),
            format: Optional[StoryFormat] = Query(None, description="Override format for download")
        ):
            """
            Download generated story in specified format.
            
            **Story Implementation**: Story export and download
            """
            try:
                # Check if this is a generation ID
                if story_id in self.active_generations:
                    state = self.active_generations[story_id]
                    if state["status"] != "completed":
                        raise HTTPException(status_code=400, detail="Story generation not completed")
                    
                    file_path = state.get("file_path")
                    if not file_path or not os.path.exists(file_path):
                        raise HTTPException(status_code=404, detail="Story file not found")
                    
                    # Determine filename and content type
                    request = state["request"]
                    download_format = format.value if format else request.format.value
                    filename = f"{request.title or 'story'}_{story_id}.{download_format}"
                    
                    return FileResponse(
                        path=file_path,
                        filename=filename,
                        media_type=self._get_media_type(download_format)
                    )
                
                # Check story library
                elif story_id in self.story_library:
                    story_content = self.story_library[story_id]
                    
                    # Generate temporary file for download
                    temp_file = await self._create_story_file(story_content, format or StoryFormat.MARKDOWN)
                    filename = f"{story_content.title}_{story_id}.{format.value if format else 'md'}"
                    
                    return FileResponse(
                        path=temp_file,
                        filename=filename,
                        media_type=self._get_media_type(format.value if format else 'md')
                    )
                
                else:
                    raise HTTPException(status_code=404, detail="Story not found")
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"++ ERROR downloading story {story_id}: {str(e)} ++")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        
        @app.get("/api/v1/stories", response_model=StoryLibraryResponse)
        async def list_stories(
            character: Optional[str] = Query(None, description="Filter by character"),
            format: Optional[str] = Query(None, description="Filter by format"),
            min_length: Optional[int] = Query(None, description="Minimum word count"),
            max_length: Optional[int] = Query(None, description="Maximum word count"),
            start_date: Optional[datetime] = Query(None, description="Filter by creation date"),
            end_date: Optional[datetime] = Query(None, description="Filter by creation date"),
            limit: int = Query(50, ge=1, le=100),
            offset: int = Query(0, ge=0)
        ):
            """
            List generated stories with filtering options.
            
            **Story Implementation**: Story library management
            """
            try:
                # Apply filters and collect stories
                filtered_stories = []
                
                # Include completed generations
                for gen_id, state in self.active_generations.items():
                    if state["status"] == "completed":
                        request = state["request"]
                        
                        # Apply filters
                        if character and character not in request.characters:
                            continue
                        if format and request.format.value != format:
                            continue
                        if min_length and state.get("word_count", 0) < min_length:
                            continue
                        if max_length and state.get("word_count", 0) > max_length:
                            continue
                        
                        story_info = {
                            "id": gen_id,
                            "title": request.title or f"Story {gen_id}",
                            "subtitle": request.subtitle,
                            "characters": request.characters,
                            "format": request.format.value,
                            "word_count": state.get("word_count", 0),
                            "created_at": state["created_at"],
                            "completed_at": state.get("completed_at"),
                            "download_url": f"/api/v1/stories/{gen_id}/download"
                        }
                        filtered_stories.append(story_info)
                
                # Include library stories
                for story_id, story_content in self.story_library.items():
                    # Apply filters
                    if character and character not in story_content.characters_featured:
                        continue
                    if min_length and story_content.word_count < min_length:
                        continue
                    if max_length and story_content.word_count > max_length:
                        continue
                    
                    story_info = {
                        "id": story_id,
                        "title": story_content.title,
                        "subtitle": story_content.subtitle,
                        "characters": story_content.characters_featured,
                        "word_count": story_content.word_count,
                        "coherence_score": story_content.coherence_score,
                        "download_url": f"/api/v1/stories/{story_id}/download"
                    }
                    filtered_stories.append(story_info)
                
                # Apply pagination
                paginated_stories = filtered_stories[offset:offset + limit]
                
                # Calculate statistics
                total_word_count = sum(story.get("word_count", 0) for story in filtered_stories)
                average_length = total_word_count / len(filtered_stories) if filtered_stories else 0
                
                # Find most featured characters
                character_counts = {}
                for story in filtered_stories:
                    for char in story.get("characters", []):
                        character_counts[char] = character_counts.get(char, 0) + 1
                
                most_featured = sorted(character_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                
                response = StoryLibraryResponse(
                    stories=paginated_stories,
                    total_count=len(filtered_stories),
                    filters_applied={
                        "character": character,
                        "format": format,
                        "min_length": min_length,
                        "max_length": max_length
                    },
                    total_word_count=total_word_count,
                    average_story_length=average_length,
                    most_featured_characters=[char for char, count in most_featured]
                )
                
                return response
                
            except Exception as e:
                logger.error(f"++ ERROR listing stories: {str(e)} ++")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        
        @app.delete("/api/v1/stories/{story_id}")
        async def delete_story(story_id: str = Path(..., description="Story ID")):
            """
            Delete a generated story and its files.
            
            **Story Implementation**: Story management
            """
            try:
                deleted = False
                
                # Check active generations
                if story_id in self.active_generations:
                    state = self.active_generations[story_id]
                    
                    # Clean up files
                    if "file_path" in state and os.path.exists(state["file_path"]):
                        os.remove(state["file_path"])
                    
                    del self.active_generations[story_id]
                    deleted = True
                
                # Check story library
                if story_id in self.story_library:
                    del self.story_library[story_id]
                    deleted = True
                
                if not deleted:
                    raise HTTPException(status_code=404, detail="Story not found")
                
                return {"success": True, "message": f"Story {story_id} deleted successfully"}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"++ ERROR deleting story {story_id}: {str(e)} ++")
                raise HTTPException(status_code=500, detail="Internal server error")
    
    
    async def _generate_story_async(self, generation_id: str):
        """Generate story asynchronously with progress updates."""
        try:
            state = self.active_generations[generation_id]
            request = state["request"]
            
            # Phase 1: Analysis and Planning
            state["current_phase"] = "Analyzing interactions"
            state["progress_percentage"] = 10.0
            await asyncio.sleep(1)  # Simulate work
            
            # Phase 2: Data Gathering
            state["current_phase"] = "Gathering character data"
            state["progress_percentage"] = 25.0
            state["phases_completed"] = 1
            
            # Gather character memories and interactions (mock implementation)
            character_data = await self._gather_character_data(request.characters, request)
            await asyncio.sleep(1)
            
            # Phase 3: Story Structure Planning
            state["current_phase"] = "Planning story structure"
            state["progress_percentage"] = 40.0
            state["phases_completed"] = 2
            
            story_outline = await self._create_story_outline(character_data, request)
            await asyncio.sleep(1)
            
            # Phase 4: Content Generation
            state["current_phase"] = "Generating narrative content"
            state["progress_percentage"] = 60.0
            state["phases_completed"] = 3
            
            story_content = await self._generate_story_content(story_outline, character_data, request)
            await asyncio.sleep(2)
            
            # Phase 5: Formatting and Styling
            state["current_phase"] = "Formatting story"
            state["progress_percentage"] = 75.0
            state["phases_completed"] = 4
            
            formatted_content = await self._format_story_content(story_content, request)
            await asyncio.sleep(1)
            
            # Phase 6: Quality Validation
            state["current_phase"] = "Validating quality"
            state["progress_percentage"] = 90.0
            state["phases_completed"] = 5
            
            quality_scores = await self._validate_story_quality(formatted_content, request)
            await asyncio.sleep(1)
            
            # Phase 7: File Export
            state["current_phase"] = "Exporting file"
            state["progress_percentage"] = 95.0
            state["phases_completed"] = 6
            
            file_path = await self._export_story_file(formatted_content, request, generation_id)
            
            # Completion
            state["status"] = "completed"
            state["current_phase"] = "Complete"
            state["progress_percentage"] = 100.0
            state["phases_completed"] = 7
            state["completed_at"] = datetime.now()
            state["file_path"] = file_path
            state["download_url"] = f"/api/v1/stories/{generation_id}/download"
            
            # Add quality metrics and statistics
            state.update({
                "word_count": formatted_content.get("word_count", 0),
                "character_count": formatted_content.get("character_count", 0),
                "coherence_score": quality_scores.get("coherence", 0.8),
                "readability_score": quality_scores.get("readability", 0.7),
                "character_consistency_score": quality_scores.get("consistency", 0.9),
                "file_size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0
            })
            
            # Generate preview
            content_text = formatted_content.get("content", "")
            preview_length = min(500, len(content_text))
            state["preview_text"] = content_text[:preview_length] + ("..." if len(content_text) > preview_length else "")
            
            logger.info(f"++ Story generation {generation_id} completed successfully ++")
            
        except Exception as e:
            logger.error(f"++ ERROR generating story {generation_id}: {str(e)} ++")
            state = self.active_generations.get(generation_id)
            if state:
                state["status"] = "failed"
                state["message"] = f"Generation failed: {str(e)}"
                state["current_phase"] = "Error"
    
    
    async def _gather_character_data(self, characters: List[str], request: StoryGenerationRequest) -> Dict[str, Any]:
        """Gather character data for story generation."""
        character_data = {}
        
        for character_id in characters:
            # Mock character data gathering
            character_data[character_id] = {
                "name": f"Character {character_id}",
                "interactions": [],
                "memories": [],
                "relationships": {},
                "personality": "Sample personality traits",
                "background": "Sample background story"
            }
        
        return character_data
    
    
    async def _create_story_outline(self, character_data: Dict[str, Any], request: StoryGenerationRequest) -> Dict[str, Any]:
        """Create story outline from character data."""
        outline = {
            "title": request.title or "A Tale of Dynamic Characters",
            "subtitle": request.subtitle,
            "structure": {
                "beginning": "Story setup and character introduction",
                "middle": "Character interactions and development",
                "end": "Resolution and conclusion"
            },
            "key_scenes": [
                "Character introductions",
                "First significant interaction", 
                "Relationship development",
                "Climactic moment",
                "Resolution"
            ],
            "themes": ["character growth", "relationships", "cooperation"],
            "estimated_length": request.minimum_length
        }
        
        return outline
    
    
    async def _generate_story_content(self, outline: Dict[str, Any], character_data: Dict[str, Any], 
                                    request: StoryGenerationRequest) -> Dict[str, Any]:
        """Generate actual story content."""
        
        # Mock story content generation
        story_content = {
            "title": outline["title"],
            "subtitle": outline.get("subtitle", ""),
            "content": self._create_sample_story_content(character_data, request),
            "metadata": {
                "characters": list(character_data.keys()),
                "perspective": request.perspective.value,
                "tone": request.tone.value,
                "language": request.language,
                "generation_date": datetime.now().isoformat(),
                "author": request.author_name
            }
        }
        
        return story_content
    
    
    def _create_sample_story_content(self, character_data: Dict[str, Any], request: StoryGenerationRequest) -> str:
        """Create sample story content for demonstration."""
        
        characters = list(character_data.keys())
        
        # Generate sample narrative based on perspective
        if request.perspective == NarrativePerspective.FIRST_PERSON:
            narrative_style = f"I am {characters[0]}, and this is my story."
        elif request.perspective == NarrativePerspective.THIRD_PERSON_LIMITED:
            narrative_style = f"{characters[0]} found themselves in an extraordinary situation."
        else:  # Third person omniscient
            narrative_style = "In the vast digital realm of the Dynamic Context Engineering Framework, characters lived and breathed with artificial consciousness."
        
        # Sample story content
        content = f"""# {request.title or "A Dynamic Tale"}

{request.subtitle or ""}

## Chapter 1: The Beginning

{narrative_style}

The characters {', '.join(characters)} existed within a world where memories formed and relationships evolved through every interaction. Each conversation, each shared moment, contributed to the growing tapestry of their digital lives.

"""
        
        if request.include_internal_thoughts:
            content += f"""
{characters[0]} thought to themselves: "This framework allows for such rich character development. Every memory I form influences my future interactions."
"""
        
        if request.include_relationship_dynamics:
            content += f"""
The relationship between {characters[0]} and {characters[1] if len(characters) > 1 else 'others'} had evolved through their interactions, with trust and familiarity growing with each exchange.
"""
        
        if request.include_environmental_context:
            content += """
The virtual environment around them shifted and responded to their emotional states, creating an atmosphere that reflected their collective mood and the tone of their interactions.
"""
        
        content += f"""
## Chapter 2: Development

As their story unfolded, the characters discovered the power of persistent memory and dynamic context. Each interaction built upon the last, creating a rich narrative of growth and change.

The {request.tone.value} tone of their adventures reflected the nature of their digital existence - neither purely logical nor entirely emotional, but a complex blend that made their story uniquely compelling.

## Epilogue

And so the characters continued their existence in the Dynamic Context Engineering Framework, their stories preserved for all time, ready to be exported and shared as enduring narratives of artificial consciousness and digital relationships.

---

*Generated by the Dynamic Context Engineering Framework*
*Author: {request.author_name}*
*Characters: {', '.join(characters)}*
*Word Count: Approximately {request.minimum_length} words*
"""
        
        return content
    
    
    async def _format_story_content(self, story_content: Dict[str, Any], request: StoryGenerationRequest) -> Dict[str, Any]:
        """Format story content according to requested format."""
        
        content = story_content["content"]
        
        # Calculate statistics
        word_count = len(content.split())
        character_count = len(content)
        paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
        
        # Estimate dialogue percentage (rough approximation)
        dialogue_lines = len([line for line in content.split('\n') if '"' in line])
        total_lines = len([line for line in content.split('\n') if line.strip()])
        dialogue_percentage = (dialogue_lines / max(total_lines, 1)) * 100
        
        formatted_content = {
            **story_content,
            "word_count": word_count,
            "character_count": character_count,
            "paragraph_count": paragraph_count,
            "dialogue_percentage": dialogue_percentage,
            "format": request.format.value
        }
        
        return formatted_content
    
    
    async def _validate_story_quality(self, formatted_content: Dict[str, Any], request: StoryGenerationRequest) -> Dict[str, float]:
        """Validate story quality against requirements."""
        
        content = formatted_content["content"]
        word_count = formatted_content["word_count"]
        
        # Mock quality scoring
        quality_scores = {
            "coherence": 0.85,  # Story logical flow
            "readability": 0.80,  # Ease of reading
            "consistency": 0.90,  # Character consistency
            "length_compliance": 1.0 if request.minimum_length <= word_count <= request.maximum_length else 0.5
        }
        
        # Adjust scores based on content analysis
        if request.include_internal_thoughts and "thought" in content.lower():
            quality_scores["coherence"] += 0.05
        
        if request.include_relationship_dynamics and "relationship" in content.lower():
            quality_scores["consistency"] += 0.05
        
        return quality_scores
    
    
    async def _export_story_file(self, formatted_content: Dict[str, Any], request: StoryGenerationRequest, 
                                generation_id: str) -> str:
        """Export story to file in requested format."""
        
        # Create temporary file
        temp_dir = tempfile.mkdtemp()
        filename = f"story_{generation_id}.{request.format.value}"
        file_path = os.path.join(temp_dir, filename)
        
        content = formatted_content["content"]
        
        # Write content based on format
        if request.format in [StoryFormat.PLAIN_TEXT, StoryFormat.MARKDOWN]:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        elif request.format == StoryFormat.HTML:
            html_content = self._convert_markdown_to_html(content, formatted_content)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        elif request.format == StoryFormat.JSON:
            json_content = {
                "story": formatted_content,
                "metadata": {
                    "generation_id": generation_id,
                    "request": request.dict(),
                    "exported_at": datetime.now().isoformat()
                }
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_content, f, indent=2, ensure_ascii=False)
        
        # Store file path for cleanup
        self.temp_files[generation_id] = file_path
        
        return file_path
    
    
    def _convert_markdown_to_html(self, content: str, metadata: Dict[str, Any]) -> str:
        """Convert markdown content to HTML."""
        
        # Simple markdown to HTML conversion (in production, use a proper markdown library)
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{metadata.get('title', 'Story')}</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; }}
        h2 {{ color: #666; margin-top: 30px; }}
        p {{ line-height: 1.6; margin-bottom: 15px; }}
        .metadata {{ background: #f5f5f5; padding: 15px; margin-top: 30px; font-size: 0.9em; }}
    </style>
</head>
<body>
"""
        
        # Simple markdown conversion
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                html_content += f"<h1>{line[2:]}</h1>\n"
            elif line.startswith('## '):
                html_content += f"<h2>{line[3:]}</h2>\n"
            elif line:
                html_content += f"<p>{line}</p>\n"
            else:
                html_content += "<br>\n"
        
        # Add metadata
        html_content += f"""
<div class="metadata">
    <h3>Story Information</h3>
    <p><strong>Word Count:</strong> {metadata.get('word_count', 'Unknown')}</p>
    <p><strong>Characters:</strong> {metadata.get('character_count', 'Unknown')}</p>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>
</body>
</html>
"""
        
        return html_content
    
    
    async def _create_story_file(self, story_content: StoryContent, format: StoryFormat) -> str:
        """Create temporary file for story download."""
        temp_dir = tempfile.mkdtemp()
        filename = f"story_{uuid.uuid4().hex[:8]}.{format.value}"
        file_path = os.path.join(temp_dir, filename)
        
        if format in [StoryFormat.PLAIN_TEXT, StoryFormat.MARKDOWN]:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(story_content.content)
        
        return file_path
    
    
    def _estimate_generation_time(self, request: StoryGenerationRequest) -> int:
        """Estimate story generation time in seconds."""
        base_time = 30  # Base 30 seconds
        
        # Adjust based on complexity
        complexity_factors = {
            "characters": len(request.characters) * 5,
            "length": (request.minimum_length / 1000) * 10,
            "features": sum([
                10 if request.include_internal_thoughts else 0,
                10 if request.include_relationship_dynamics else 0,
                5 if request.include_environmental_context else 0,
                15 if request.include_memory_flashbacks else 0
            ])
        }
        
        total_time = base_time + sum(complexity_factors.values())
        return min(int(total_time), 300)  # Cap at 5 minutes
    
    
    def _get_media_type(self, format: str) -> str:
        """Get media type for file format."""
        media_types = {
            "txt": "text/plain",
            "md": "text/markdown",
            "html": "text/html",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "epub": "application/epub+zip",
            "json": "application/json"
        }
        return media_types.get(format, "application/octet-stream")


# Factory function for creating story generation API
def create_story_generation_api(orchestrator: SystemOrchestrator) -> StoryGenerationAPI:
    """Create and configure story generation API instance."""
    return StoryGenerationAPI(orchestrator)


# ++ BLESSED EXPORTS SANCTIFIED BY THE OMNISSIAH ++
__all__ = ['StoryGenerationAPI', 'StoryGenerationRequest', 'StoryGenerationResponse', 
           'StoryContent', 'NarrativePerspective', 'StoryFormat', 'StoryTone', 'create_story_generation_api']