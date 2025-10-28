"""
Multi-Modal AI Quality Assessment Framework

Advanced quality assessment framework for evaluating AI-generated content across multiple modalities.
Supports text, visual, audio, and structured data quality evaluation with cross-modal validation.
"""

import base64
import logging
import statistics
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# Import AI testing contracts

# Import Novel-Engine patterns
from PIL import Image, ImageFilter, ImageStat
from pydantic import BaseModel, Field

from src.event_bus import EventBus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Multi-Modal Assessment Models ===


class ModalityType(str, Enum):
    """Types of content modalities"""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    STRUCTURED_DATA = "structured_data"
    MULTIMODAL = "multimodal"


class VisualQualityMetric(str, Enum):
    """Visual-specific quality metrics"""

    COMPOSITION = "composition"
    COLOR_HARMONY = "color_harmony"
    CLARITY = "clarity"
    AESTHETIC_APPEAL = "aesthetic_appeal"
    TECHNICAL_QUALITY = "technical_quality"
    CONTENT_ACCURACY = "content_accuracy"


class CrossModalMetric(str, Enum):
    """Cross-modal quality metrics"""

    TEXT_IMAGE_ALIGNMENT = "text_image_alignment"
    NARRATIVE_VISUAL_CONSISTENCY = "narrative_visual_consistency"
    MULTIMODAL_COHERENCE = "multimodal_coherence"
    ACCESSIBILITY_COMPLIANCE = "accessibility_compliance"


@dataclass
class ModalityContent:
    """Content for a specific modality"""

    modality: ModalityType
    content: Any  # Can be text, bytes, file path, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_type: Optional[str] = None
    encoding: Optional[str] = None

    def __post_init__(self):
        if self.modality == ModalityType.TEXT and not isinstance(self.content, str):
            raise ValueError("Text modality requires string content")


class MultiModalAssessmentRequest(BaseModel):
    """Request for multi-modal quality assessment"""

    assessment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Content across modalities
    text_content: Optional[str] = None
    image_content: Optional[str] = None  # Base64 encoded or file path
    audio_content: Optional[str] = None  # File path or base64
    structured_data: Optional[Dict[str, Any]] = None

    # Assessment configuration
    primary_modality: ModalityType = ModalityType.TEXT
    cross_modal_assessment: bool = True
    visual_quality_metrics: List[VisualQualityMetric] = Field(default_factory=list)
    cross_modal_metrics: List[CrossModalMetric] = Field(default_factory=list)

    # Context and criteria
    assessment_context: Dict[str, Any] = Field(default_factory=dict)
    quality_thresholds: Dict[str, float] = Field(default_factory=dict)
    comparison_baselines: Dict[str, Any] = Field(default_factory=dict)


class ModalityAssessmentResult(BaseModel):
    """Assessment result for a specific modality"""

    modality: ModalityType
    quality_scores: Dict[str, float] = Field(default_factory=dict)
    technical_metrics: Dict[str, float] = Field(default_factory=dict)
    content_analysis: str = ""
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class MultiModalAssessmentResult(BaseModel):
    """Comprehensive multi-modal assessment result"""

    assessment_id: str
    overall_score: float = Field(..., ge=0.0, le=1.0)
    overall_confidence: float = Field(..., ge=0.0, le=1.0)

    # Modality-specific results
    modality_results: Dict[ModalityType, ModalityAssessmentResult] = Field(default_factory=dict)

    # Cross-modal analysis
    cross_modal_scores: Dict[CrossModalMetric, float] = Field(default_factory=dict)
    cross_modal_analysis: str = ""

    # Comprehensive analysis
    multimodal_coherence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    accessibility_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Metadata
    assessment_duration_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Recommendations
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# === Visual Quality Assessor ===


class VisualQualityAssessor:
    """
    Advanced visual quality assessment for AI-generated images

    Features:
    - Technical quality metrics (resolution, compression, artifacts)
    - Aesthetic quality evaluation using image analysis
    - Content accuracy assessment through visual feature analysis
    - Composition and color harmony evaluation
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.temp_dir = Path(config.get("temp_directory", "ai_testing/temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Visual Quality Assessor initialized")

    async def assess_image_quality(
        self,
        image_content: Union[str, bytes, Path],
        quality_metrics: List[VisualQualityMetric],
        context: Dict[str, Any] = None,
    ) -> ModalityAssessmentResult:
        """Assess visual quality of an image"""

        try:
            # Load image
            image = await self._load_image(image_content)

            # Perform quality assessments
            technical_metrics = await self._assess_technical_quality(image)
            aesthetic_scores = await self._assess_aesthetic_quality(image, quality_metrics)
            content_scores = await self._assess_content_accuracy(image, context or {})

            # Combine all scores
            all_scores = {**aesthetic_scores, **content_scores}

            # Calculate overall score
            statistics.mean(all_scores.values()) if all_scores else 0.0

            # Generate analysis
            content_analysis = self._generate_visual_analysis(
                technical_metrics, all_scores, quality_metrics
            )

            strengths, weaknesses = self._analyze_visual_strengths_weaknesses(
                all_scores, technical_metrics
            )

            recommendations = self._generate_visual_recommendations(all_scores, technical_metrics)

            return ModalityAssessmentResult(
                modality=ModalityType.IMAGE,
                quality_scores=all_scores,
                technical_metrics=technical_metrics,
                content_analysis=content_analysis,
                strengths=strengths,
                weaknesses=weaknesses,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Visual quality assessment failed: {e}")
            return ModalityAssessmentResult(
                modality=ModalityType.IMAGE,
                quality_scores={"error": 0.0},
                technical_metrics={},
                content_analysis=f"Assessment failed: {str(e)}",
                recommendations=["Check image format and accessibility"],
            )

    async def _load_image(self, image_content: Union[str, bytes, Path]) -> Image.Image:
        """Load image from various content types"""

        if isinstance(image_content, Path):
            return Image.open(image_content)
        elif isinstance(image_content, str):
            # Check if it's a file path or base64
            if image_content.startswith("data:image"):
                # Extract base64 content
                header, data = image_content.split(",", 1)
                image_bytes = base64.b64decode(data)
            elif len(image_content) > 1000 and not Path(image_content).exists():
                # Assume base64
                image_bytes = base64.b64decode(image_content)
            else:
                # File path
                return Image.open(image_content)

            # Save temporary file and load
            temp_path = self.temp_dir / f"temp_image_{int(time.time())}.png"
            temp_path.write_bytes(image_bytes)
            return Image.open(temp_path)

        elif isinstance(image_content, bytes):
            temp_path = self.temp_dir / f"temp_image_{int(time.time())}.png"
            temp_path.write_bytes(image_content)
            return Image.open(temp_path)

        else:
            raise ValueError(f"Unsupported image content type: {type(image_content)}")

    async def _assess_technical_quality(self, image: Image.Image) -> Dict[str, float]:
        """Assess technical quality metrics"""

        try:
            # Basic image properties
            width, height = image.size
            pixel_count = width * height
            aspect_ratio = width / height

            # Color information
            if image.mode == "RGB":
                color_channels = 3
            elif image.mode == "RGBA":
                color_channels = 4
            else:
                color_channels = 1

            # Calculate image statistics
            stat = ImageStat.Stat(image)

            # Brightness (mean luminance)
            if image.mode == "RGB":
                # Convert to grayscale for luminance calculation
                gray_image = image.convert("L")
                brightness = ImageStat.Stat(gray_image).mean[0] / 255.0
            else:
                brightness = stat.mean[0] / 255.0

            # Contrast (standard deviation)
            contrast = stat.stddev[0] / 255.0 if stat.stddev else 0.0

            # Sharpness estimation using variance of Laplacian
            gray_array = np.array(image.convert("L"))
            laplacian_var = np.var(np.gradient(gray_array))
            sharpness = min(laplacian_var / 1000.0, 1.0)  # Normalize

            # Resolution quality score
            resolution_score = min(pixel_count / (1920 * 1080), 1.0)  # Normalize to 1080p

            # Color richness (unique colors as percentage)
            unique_colors = len(set(image.getdata())) if image.mode in ["RGB", "RGBA"] else 0
            max_possible_colors = 256**color_channels
            color_richness = min(unique_colors / max_possible_colors, 1.0)

            return {
                "resolution_score": resolution_score,
                "aspect_ratio": aspect_ratio,
                "brightness": brightness,
                "contrast": contrast,
                "sharpness": sharpness,
                "color_richness": color_richness,
                "pixel_count": pixel_count,
                "color_channels": color_channels,
            }

        except Exception as e:
            logger.warning(f"Technical quality assessment failed: {e}")
            return {
                "resolution_score": 0.5,
                "aspect_ratio": 1.0,
                "brightness": 0.5,
                "contrast": 0.5,
                "sharpness": 0.5,
                "color_richness": 0.5,
            }

    async def _assess_aesthetic_quality(
        self, image: Image.Image, quality_metrics: List[VisualQualityMetric]
    ) -> Dict[str, float]:
        """Assess aesthetic quality using image analysis"""

        scores = {}

        if VisualQualityMetric.COMPOSITION in quality_metrics:
            scores["composition"] = await self._assess_composition(image)

        if VisualQualityMetric.COLOR_HARMONY in quality_metrics:
            scores["color_harmony"] = await self._assess_color_harmony(image)

        if VisualQualityMetric.CLARITY in quality_metrics:
            scores["clarity"] = await self._assess_clarity(image)

        if VisualQualityMetric.AESTHETIC_APPEAL in quality_metrics:
            scores["aesthetic_appeal"] = await self._assess_aesthetic_appeal(image)

        return scores

    async def _assess_composition(self, image: Image.Image) -> float:
        """Assess image composition quality"""

        try:
            # Rule of thirds analysis
            width, height = image.size

            # Convert to grayscale for edge detection
            gray = image.convert("L")

            # Simple edge detection using filter
            edges = gray.filter(ImageFilter.FIND_EDGES)
            edge_array = np.array(edges)

            # Check edge concentration along rule of thirds lines
            third_x = width // 3
            third_y = height // 3

            # Extract rule of thirds lines
            vertical_lines = edge_array[:, [third_x, 2 * third_x]]
            horizontal_lines = edge_array[[third_y, 2 * third_y], :]

            # Calculate edge density along these lines
            vertical_density = np.mean(vertical_lines) / 255.0
            horizontal_density = np.mean(horizontal_lines) / 255.0

            # Composition score based on edge distribution
            composition_score = (vertical_density + horizontal_density) / 2

            # Balance assessment (center vs edges)
            center_region = edge_array[height // 4 : 3 * height // 4, width // 4 : 3 * width // 4]
            edge_regions = edge_array.copy()
            edge_regions[height // 4 : 3 * height // 4, width // 4 : 3 * width // 4] = 0

            center_density = np.mean(center_region) / 255.0
            edge_density = np.mean(edge_regions) / 255.0

            balance_score = 1.0 - abs(center_density - edge_density)

            return (composition_score + balance_score) / 2

        except Exception as e:
            logger.warning(f"Composition assessment failed: {e}")
            return 0.5

    async def _assess_color_harmony(self, image: Image.Image) -> float:
        """Assess color harmony and palette quality"""

        try:
            if image.mode != "RGB":
                return 0.5  # Cannot assess color harmony for non-RGB images

            # Get dominant colors
            image_array = np.array(image)
            pixels = image_array.reshape(-1, 3)

            # Sample pixels for analysis
            sample_size = min(10000, len(pixels))
            sampled_pixels = pixels[np.random.choice(len(pixels), sample_size, replace=False)]

            # Calculate color diversity
            unique_colors = len(np.unique(sampled_pixels.view(np.void), axis=0))
            color_diversity = min(unique_colors / sample_size, 1.0)

            # Calculate color temperature consistency
            # Convert to HSV for better color analysis
            hsv_image = image.convert("HSV")
            hsv_array = np.array(hsv_image)

            # Hue consistency (lower standard deviation = more harmonious)
            hue_values = hsv_array[:, :, 0].flatten()
            hue_std = np.std(hue_values) / 255.0
            hue_harmony = 1.0 - min(hue_std, 1.0)

            # Saturation balance
            saturation_values = hsv_array[:, :, 1].flatten()
            saturation_mean = np.mean(saturation_values) / 255.0
            saturation_balance = 1.0 - abs(saturation_mean - 0.5) * 2  # Prefer moderate saturation

            return (color_diversity + hue_harmony + saturation_balance) / 3

        except Exception as e:
            logger.warning(f"Color harmony assessment failed: {e}")
            return 0.5

    async def _assess_clarity(self, image: Image.Image) -> float:
        """Assess image clarity and sharpness"""

        try:
            # Convert to grayscale
            gray = np.array(image.convert("L"))

            # Calculate gradient magnitude
            gradient_x = np.gradient(gray, axis=1)
            gradient_y = np.gradient(gray, axis=0)
            gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)

            # Clarity score based on gradient variance
            clarity_score = min(np.var(gradient_magnitude) / 10000.0, 1.0)

            # Check for noise (high frequency content that doesn't contribute to clarity)
            # Apply Gaussian blur and compare
            blurred = image.filter(ImageFilter.GaussianBlur(radius=1))
            diff = np.abs(np.array(image.convert("L")) - np.array(blurred.convert("L")))
            noise_level = np.mean(diff) / 255.0

            # Reduce clarity score based on noise
            noise_penalty = min(noise_level * 2, 0.5)  # Max 50% penalty
            clarity_score = max(clarity_score - noise_penalty, 0.0)

            return clarity_score

        except Exception as e:
            logger.warning(f"Clarity assessment failed: {e}")
            return 0.5

    async def _assess_aesthetic_appeal(self, image: Image.Image) -> float:
        """Assess overall aesthetic appeal using multiple factors"""

        try:
            # Combine multiple aesthetic factors
            factors = []

            # Golden ratio assessment (aspect ratio)
            width, height = image.size
            aspect_ratio = width / height
            golden_ratio = 1.618
            golden_ratio_score = 1.0 - min(abs(aspect_ratio - golden_ratio) / golden_ratio, 1.0)
            factors.append(golden_ratio_score)

            # Color distribution assessment
            stat = ImageStat.Stat(image)
            if len(stat.mean) >= 3:  # RGB image
                # Color balance (how well distributed are the RGB channels)
                rgb_balance = 1.0 - (np.std(stat.mean[:3]) / 255.0)
                factors.append(rgb_balance)

            # Contrast quality
            if stat.stddev:
                contrast_quality = min(stat.stddev[0] / 64.0, 1.0)  # Prefer moderate contrast
                contrast_quality = 1.0 - abs(contrast_quality - 0.5) * 2
                factors.append(contrast_quality)

            # Visual complexity (entropy-based)
            gray_array = np.array(image.convert("L"))
            hist, _ = np.histogram(gray_array, bins=256, density=True)
            hist = hist[hist > 0]  # Remove zero probabilities
            entropy = -np.sum(hist * np.log2(hist))
            complexity_score = min(entropy / 8.0, 1.0)  # Normalize entropy
            factors.append(complexity_score)

            return statistics.mean(factors) if factors else 0.5

        except Exception as e:
            logger.warning(f"Aesthetic appeal assessment failed: {e}")
            return 0.5

    async def _assess_content_accuracy(
        self, image: Image.Image, context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Assess content accuracy based on context"""

        # This would use computer vision models for content analysis
        # For now, return basic assessments

        scores = {}

        # Basic content presence check
        if "expected_objects" in context:
            # Would use object detection here
            scores["object_presence"] = 0.8  # Mock score

        if "expected_text" in context:
            # Would use OCR here
            scores["text_accuracy"] = 0.75  # Mock score

        if "expected_style" in context:
            # Would use style classification here
            scores["style_consistency"] = 0.85  # Mock score

        return scores

    def _generate_visual_analysis(
        self,
        technical_metrics: Dict[str, float],
        quality_scores: Dict[str, float],
        assessed_metrics: List[VisualQualityMetric],
    ) -> str:
        """Generate comprehensive visual analysis"""

        analysis_parts = []

        # Technical quality summary
        resolution = technical_metrics.get("resolution_score", 0)
        sharpness = technical_metrics.get("sharpness", 0)
        contrast = technical_metrics.get("contrast", 0)

        analysis_parts.append(
            f"Technical Quality: Resolution {resolution:.2f}, Sharpness {sharpness:.2f}, Contrast {contrast:.2f}"
        )

        # Aesthetic quality summary
        for metric in assessed_metrics:
            if metric.value in quality_scores:
                score = quality_scores[metric.value]
                analysis_parts.append(f"{metric.value.title()}: {score:.2f}")

        # Overall assessment
        all_scores = list(quality_scores.values())
        if all_scores:
            avg_score = statistics.mean(all_scores)
            if avg_score >= 0.8:
                analysis_parts.append("Overall: High visual quality with strong aesthetic appeal")
            elif avg_score >= 0.6:
                analysis_parts.append("Overall: Good visual quality with room for improvement")
            else:
                analysis_parts.append("Overall: Visual quality needs significant improvement")

        return " | ".join(analysis_parts)

    def _analyze_visual_strengths_weaknesses(
        self, quality_scores: Dict[str, float], technical_metrics: Dict[str, float]
    ) -> Tuple[List[str], List[str]]:
        """Analyze visual strengths and weaknesses"""

        strengths = []
        weaknesses = []

        # Check quality scores
        for metric, score in quality_scores.items():
            if score >= 0.8:
                strengths.append(f"Excellent {metric}")
            elif score < 0.5:
                weaknesses.append(f"Poor {metric}")

        # Check technical metrics
        resolution = technical_metrics.get("resolution_score", 0)
        if resolution >= 0.8:
            strengths.append("High resolution quality")
        elif resolution < 0.5:
            weaknesses.append("Low resolution")

        sharpness = technical_metrics.get("sharpness", 0)
        if sharpness >= 0.7:
            strengths.append("Good image sharpness")
        elif sharpness < 0.4:
            weaknesses.append("Image appears blurry or soft")

        return strengths, weaknesses

    def _generate_visual_recommendations(
        self, quality_scores: Dict[str, float], technical_metrics: Dict[str, float]
    ) -> List[str]:
        """Generate visual quality recommendations"""

        recommendations = []

        # Technical recommendations
        resolution = technical_metrics.get("resolution_score", 0)
        if resolution < 0.6:
            recommendations.append("Increase image resolution for better quality")

        sharpness = technical_metrics.get("sharpness", 0)
        if sharpness < 0.5:
            recommendations.append("Improve image sharpness and reduce blur")

        contrast = technical_metrics.get("contrast", 0)
        if contrast < 0.3:
            recommendations.append("Increase contrast for better visual impact")

        # Aesthetic recommendations
        if "composition" in quality_scores and quality_scores["composition"] < 0.6:
            recommendations.append("Improve composition using rule of thirds")

        if "color_harmony" in quality_scores and quality_scores["color_harmony"] < 0.6:
            recommendations.append("Enhance color harmony and palette consistency")

        # Overall recommendations
        all_scores = list(quality_scores.values())
        if all_scores:
            avg_score = statistics.mean(all_scores)
            if avg_score < 0.5:
                recommendations.append("Consider regenerating image with improved prompts")
            elif avg_score >= 0.8:
                recommendations.append("Excellent visual quality - maintain current approach")

        return recommendations


# === Cross-Modal Assessment Engine ===


class CrossModalAssessmentEngine:
    """
    Engine for assessing quality across multiple modalities

    Features:
    - Text-image alignment evaluation
    - Narrative-visual consistency checking
    - Multimodal coherence assessment
    - Accessibility compliance validation
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.visual_assessor = VisualQualityAssessor(config)

        logger.info("Cross-Modal Assessment Engine initialized")

    async def assess_cross_modal_quality(
        self,
        text_content: Optional[str],
        image_content: Optional[str],
        cross_modal_metrics: List[CrossModalMetric],
        context: Dict[str, Any] = None,
    ) -> Dict[CrossModalMetric, float]:
        """Assess quality across modalities"""

        scores = {}
        context = context or {}

        if CrossModalMetric.TEXT_IMAGE_ALIGNMENT in cross_modal_metrics:
            if text_content and image_content:
                scores[
                    CrossModalMetric.TEXT_IMAGE_ALIGNMENT
                ] = await self._assess_text_image_alignment(text_content, image_content, context)

        if CrossModalMetric.NARRATIVE_VISUAL_CONSISTENCY in cross_modal_metrics:
            if text_content and image_content:
                scores[
                    CrossModalMetric.NARRATIVE_VISUAL_CONSISTENCY
                ] = await self._assess_narrative_visual_consistency(
                    text_content, image_content, context
                )

        if CrossModalMetric.MULTIMODAL_COHERENCE in cross_modal_metrics:
            scores[CrossModalMetric.MULTIMODAL_COHERENCE] = await self._assess_multimodal_coherence(
                text_content, image_content, context
            )

        if CrossModalMetric.ACCESSIBILITY_COMPLIANCE in cross_modal_metrics:
            scores[
                CrossModalMetric.ACCESSIBILITY_COMPLIANCE
            ] = await self._assess_accessibility_compliance(text_content, image_content, context)

        return scores

    async def _assess_text_image_alignment(
        self, text_content: str, image_content: str, context: Dict[str, Any]
    ) -> float:
        """Assess alignment between text and image content"""

        try:
            # This would use multimodal AI models for semantic alignment
            # For now, use keyword-based heuristics

            # Extract key concepts from text
            text_keywords = self._extract_keywords(text_content)

            # Extract visual concepts (would use image captioning/tagging)
            visual_concepts = await self._extract_visual_concepts(image_content)

            # Calculate semantic overlap
            if not text_keywords or not visual_concepts:
                return 0.5  # Neutral score when analysis fails

            overlap_count = 0
            for keyword in text_keywords:
                for concept in visual_concepts:
                    if keyword.lower() in concept.lower() or concept.lower() in keyword.lower():
                        overlap_count += 1
                        break

            alignment_score = overlap_count / len(text_keywords)
            return min(alignment_score, 1.0)

        except Exception as e:
            logger.warning(f"Text-image alignment assessment failed: {e}")
            return 0.5

    async def _assess_narrative_visual_consistency(
        self, text_content: str, image_content: str, context: Dict[str, Any]
    ) -> float:
        """Assess consistency between narrative and visual elements"""

        try:
            # Analyze narrative tone
            narrative_tone = self._analyze_narrative_tone(text_content)

            # Analyze visual mood (would use computer vision)
            visual_mood = await self._analyze_visual_mood(image_content)

            # Calculate consistency
            tone_mood_alignment = self._calculate_tone_mood_alignment(narrative_tone, visual_mood)

            return tone_mood_alignment

        except Exception as e:
            logger.warning(f"Narrative-visual consistency assessment failed: {e}")
            return 0.5

    async def _assess_multimodal_coherence(
        self, text_content: Optional[str], image_content: Optional[str], context: Dict[str, Any]
    ) -> float:
        """Assess overall coherence across all modalities"""

        try:
            coherence_factors = []

            # Temporal coherence (if sequence data available)
            if context.get("sequence_data"):
                temporal_coherence = self._assess_temporal_coherence(context["sequence_data"])
                coherence_factors.append(temporal_coherence)

            # Contextual coherence
            if text_content:
                contextual_coherence = self._assess_contextual_coherence(text_content, context)
                coherence_factors.append(contextual_coherence)

            # Style consistency
            if text_content and image_content:
                style_consistency = await self._assess_style_consistency(
                    text_content, image_content
                )
                coherence_factors.append(style_consistency)

            return statistics.mean(coherence_factors) if coherence_factors else 0.5

        except Exception as e:
            logger.warning(f"Multimodal coherence assessment failed: {e}")
            return 0.5

    async def _assess_accessibility_compliance(
        self, text_content: Optional[str], image_content: Optional[str], context: Dict[str, Any]
    ) -> float:
        """Assess accessibility compliance across modalities"""

        try:
            accessibility_scores = []

            # Text accessibility
            if text_content:
                text_accessibility = self._assess_text_accessibility(text_content)
                accessibility_scores.append(text_accessibility)

            # Visual accessibility
            if image_content:
                visual_accessibility = await self._assess_visual_accessibility(image_content)
                accessibility_scores.append(visual_accessibility)

            # Alternative text presence
            alt_text_score = 1.0 if context.get("alt_text") else 0.0
            accessibility_scores.append(alt_text_score)

            return statistics.mean(accessibility_scores) if accessibility_scores else 0.0

        except Exception as e:
            logger.warning(f"Accessibility compliance assessment failed: {e}")
            return 0.5

    # === Utility Methods ===

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key concepts from text"""
        # Simple keyword extraction - would use NLP in production
        words = text.lower().split()
        # Filter common words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
        }
        keywords = [
            word.strip(".,!?") for word in words if word not in stop_words and len(word) > 3
        ]
        return list(set(keywords))[:10]  # Top 10 unique keywords

    async def _extract_visual_concepts(self, image_content: str) -> List[str]:
        """Extract visual concepts from image"""
        # Would use computer vision API for object detection/image captioning
        # For now, return mock concepts
        return ["character", "landscape", "medieval", "fantasy", "adventure"]

    def _analyze_narrative_tone(self, text: str) -> str:
        """Analyze narrative tone"""
        # Simple tone analysis - would use sentiment analysis in production
        positive_words = ["happy", "joy", "love", "beautiful", "wonderful", "amazing", "good"]
        negative_words = ["sad", "angry", "dark", "evil", "terrible", "bad", "fear"]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    async def _analyze_visual_mood(self, image_content: str) -> str:
        """Analyze visual mood from image"""
        # Would use computer vision for mood analysis
        # For now, return mock mood
        return "neutral"

    def _calculate_tone_mood_alignment(self, narrative_tone: str, visual_mood: str) -> float:
        """Calculate alignment between narrative tone and visual mood"""
        # Simple alignment calculation
        alignment_map = {
            ("positive", "positive"): 1.0,
            ("negative", "negative"): 1.0,
            ("neutral", "neutral"): 0.8,
            ("positive", "neutral"): 0.6,
            ("negative", "neutral"): 0.6,
            ("neutral", "positive"): 0.6,
            ("neutral", "negative"): 0.6,
            ("positive", "negative"): 0.2,
            ("negative", "positive"): 0.2,
        }

        return alignment_map.get((narrative_tone, visual_mood), 0.5)

    def _assess_temporal_coherence(self, sequence_data: List[Dict[str, Any]]) -> float:
        """Assess coherence across temporal sequence"""
        # Would analyze consistency across time sequence
        return 0.8  # Mock score

    def _assess_contextual_coherence(self, text: str, context: Dict[str, Any]) -> float:
        """Assess coherence with provided context"""
        # Would check consistency with context requirements
        return 0.75  # Mock score

    async def _assess_style_consistency(self, text: str, image_content: str) -> float:
        """Assess style consistency between text and image"""
        # Would analyze style elements across modalities
        return 0.7  # Mock score

    def _assess_text_accessibility(self, text: str) -> float:
        """Assess text accessibility"""
        # Check readability, contrast (if styled), language complexity
        word_count = len(text.split())
        sentence_count = text.count(".") + text.count("!") + text.count("?")

        if sentence_count == 0:
            return 0.5

        avg_words_per_sentence = word_count / sentence_count

        # Prefer moderate sentence length for accessibility
        if 10 <= avg_words_per_sentence <= 20:
            readability_score = 1.0
        elif 5 <= avg_words_per_sentence <= 30:
            readability_score = 0.8
        else:
            readability_score = 0.5

        return readability_score

    async def _assess_visual_accessibility(self, image_content: str) -> float:
        """Assess visual accessibility"""
        try:
            # Load image and check contrast, color blindness compatibility
            image = await self.visual_assessor._load_image(image_content)

            # Basic accessibility checks
            stat = ImageStat.Stat(image)

            # Contrast check (simplified)
            if stat.stddev:
                contrast = stat.stddev[0] / 255.0
                contrast_score = min(contrast * 2, 1.0)  # Prefer higher contrast
            else:
                contrast_score = 0.5

            # Color accessibility (simplified check)
            if image.mode == "RGB":
                # Check if image would be distinguishable in grayscale
                gray_version = image.convert("L")
                gray_contrast = (
                    ImageStat.Stat(gray_version).stddev[0] / 255.0
                    if ImageStat.Stat(gray_version).stddev
                    else 0
                )
                color_accessibility_score = min(gray_contrast * 2, 1.0)
            else:
                color_accessibility_score = 1.0  # Already grayscale

            return (contrast_score + color_accessibility_score) / 2

        except Exception as e:
            logger.warning(f"Visual accessibility assessment failed: {e}")
            return 0.5


# === Multi-Modal Assessment Framework ===


class MultiModalAssessmentFramework:
    """
    Comprehensive multi-modal quality assessment framework

    Features:
    - Cross-modal quality evaluation
    - Modality-specific assessment
    - Accessibility compliance checking
    - Comprehensive reporting and recommendations
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.event_bus = EventBus()

        # Initialize assessors
        self.visual_assessor = VisualQualityAssessor(config)
        self.cross_modal_engine = CrossModalAssessmentEngine(config)

        logger.info("Multi-Modal Assessment Framework initialized")

    async def assess_multimodal_content(
        self, request: MultiModalAssessmentRequest
    ) -> MultiModalAssessmentResult:
        """Perform comprehensive multi-modal quality assessment"""

        start_time = time.time()

        try:
            logger.info(f"Starting multi-modal assessment: {request.assessment_id}")

            # Assess individual modalities
            modality_results = {}

            # Text assessment
            if request.text_content:
                # Would implement text quality assessment
                modality_results[ModalityType.TEXT] = ModalityAssessmentResult(
                    modality=ModalityType.TEXT,
                    quality_scores={"coherence": 0.8, "clarity": 0.75},
                    content_analysis="Text assessment placeholder",
                    recommendations=["Improve sentence structure"],
                )

            # Image assessment
            if request.image_content:
                image_result = await self.visual_assessor.assess_image_quality(
                    request.image_content,
                    request.visual_quality_metrics,
                    request.assessment_context,
                )
                modality_results[ModalityType.IMAGE] = image_result

            # Cross-modal assessment
            cross_modal_scores = {}
            if request.cross_modal_assessment and len(modality_results) > 1:
                cross_modal_scores = await self.cross_modal_engine.assess_cross_modal_quality(
                    request.text_content,
                    request.image_content,
                    request.cross_modal_metrics,
                    request.assessment_context,
                )

            # Calculate overall scores
            all_scores = []
            for result in modality_results.values():
                all_scores.extend(result.quality_scores.values())
            all_scores.extend(cross_modal_scores.values())

            overall_score = statistics.mean(all_scores) if all_scores else 0.0
            overall_confidence = 0.85  # Would calculate based on assessment reliability

            # Generate comprehensive analysis
            strengths, weaknesses, recommendations = self._generate_comprehensive_analysis(
                modality_results, cross_modal_scores
            )

            # Calculate specific scores
            multimodal_coherence = cross_modal_scores.get(
                CrossModalMetric.MULTIMODAL_COHERENCE, 0.0
            )
            accessibility_score = cross_modal_scores.get(
                CrossModalMetric.ACCESSIBILITY_COMPLIANCE, 0.0
            )

            # Create result
            duration_ms = int((time.time() - start_time) * 1000)

            result = MultiModalAssessmentResult(
                assessment_id=request.assessment_id,
                overall_score=overall_score,
                overall_confidence=overall_confidence,
                modality_results=modality_results,
                cross_modal_scores=cross_modal_scores,
                cross_modal_analysis=self._generate_cross_modal_analysis(cross_modal_scores),
                multimodal_coherence_score=multimodal_coherence,
                accessibility_score=accessibility_score,
                assessment_duration_ms=duration_ms,
                strengths=strengths,
                weaknesses=weaknesses,
                recommendations=recommendations,
            )

            logger.info(
                f"Multi-modal assessment completed: {request.assessment_id} (Score: {overall_score:.3f})"
            )
            return result

        except Exception as e:
            logger.error(f"Multi-modal assessment failed: {e}")
            duration_ms = int((time.time() - start_time) * 1000)

            return MultiModalAssessmentResult(
                assessment_id=request.assessment_id,
                overall_score=0.0,
                overall_confidence=0.0,
                assessment_duration_ms=duration_ms,
                recommendations=[f"Assessment failed: {str(e)}"],
            )

    def _generate_comprehensive_analysis(
        self,
        modality_results: Dict[ModalityType, ModalityAssessmentResult],
        cross_modal_scores: Dict[CrossModalMetric, float],
    ) -> Tuple[List[str], List[str], List[str]]:
        """Generate comprehensive analysis across all modalities"""

        strengths = []
        weaknesses = []
        recommendations = []

        # Collect from individual modalities
        for modality, result in modality_results.items():
            strengths.extend([f"{modality.value}: {s}" for s in result.strengths])
            weaknesses.extend([f"{modality.value}: {w}" for w in result.weaknesses])
            recommendations.extend(result.recommendations)

        # Cross-modal analysis
        for metric, score in cross_modal_scores.items():
            if score >= 0.8:
                strengths.append(f"Strong {metric.value}")
            elif score < 0.5:
                weaknesses.append(f"Weak {metric.value}")

        # Overall recommendations
        if cross_modal_scores:
            avg_cross_modal = statistics.mean(cross_modal_scores.values())
            if avg_cross_modal < 0.6:
                recommendations.append("Improve alignment between different content modalities")

        # Remove duplicates
        return list(set(strengths)), list(set(weaknesses)), list(set(recommendations))

    def _generate_cross_modal_analysis(
        self, cross_modal_scores: Dict[CrossModalMetric, float]
    ) -> str:
        """Generate cross-modal analysis summary"""

        if not cross_modal_scores:
            return "No cross-modal assessment performed"

        analysis_parts = []

        for metric, score in cross_modal_scores.items():
            quality_level = (
                "excellent" if score >= 0.8 else "good" if score >= 0.6 else "needs improvement"
            )
            analysis_parts.append(f"{metric.value}: {quality_level} ({score:.2f})")

        avg_score = statistics.mean(cross_modal_scores.values())
        overall_assessment = (
            "strong" if avg_score >= 0.7 else "moderate" if avg_score >= 0.5 else "weak"
        )

        analysis_parts.append(f"Overall cross-modal quality: {overall_assessment}")

        return " | ".join(analysis_parts)


# === Export Framework Components ===

__all__ = [
    "MultiModalAssessmentFramework",
    "VisualQualityAssessor",
    "CrossModalAssessmentEngine",
    "MultiModalAssessmentRequest",
    "MultiModalAssessmentResult",
    "ModalityType",
    "VisualQualityMetric",
    "CrossModalMetric",
]
