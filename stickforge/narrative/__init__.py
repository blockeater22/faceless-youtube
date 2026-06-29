"""The cognitive layer — StickForge's story brain.

Understanding is separated into **contracts** (versioned data: StoryAnalysis,
CharacterModel, IntentGraph, SceneSpec), a **pipeline** (segment → analyze →
intent graph → plan → validate), and a pluggable **inference provider** (an
``Analyzer``). The shipped provider is deterministic and heuristic; an LLM
provider can register later and emit the *same* structures, so no downstream
engine (renderer, World, Camera, Director) ever parses English — they consume
the Scene Graph this layer produces.

Every inference carries a confidence score: that is the seam a future LLM
improves without changing a single consumer.

Public API: ``understand_story``, ``plan``, plus the granular services
(``segment_story``, ``extract_characters``, ``build_intent_graph``,
``plan_scene``, ``validate_scene_graph``, ``infer_environment``,
``infer_camera_focus``, ``infer_emotion_curve``, ``summarize_story``, …).
"""
from .schema import (Inf, StoryAnalysis, CharacterModel, IntentGraph,
                     IntentNode, SceneSpec, StorySegmentation, SCHEMA_VERSION)
from .analyzer import Analyzer, HeuristicAnalyzer, ANALYZERS, get_analyzer
from .segmentation import segment_story
from .characters import extract_characters, extract_relationships
from .intent import build_intent_graph, extract_intent
from .planner import (plan_scene, infer_environment, infer_camera_focus,
                      infer_emotion_curve, recommend_scene_structure)
from .validate import validate_scene_graph, validate_intent_graph
from .engine import understand_story, plan, summarize_story, StoryUnderstanding

__all__ = [
    "Inf", "StoryAnalysis", "CharacterModel", "IntentGraph", "IntentNode",
    "SceneSpec", "StorySegmentation", "SCHEMA_VERSION",
    "Analyzer", "HeuristicAnalyzer", "ANALYZERS", "get_analyzer",
    "segment_story", "extract_characters", "extract_relationships",
    "build_intent_graph", "extract_intent", "plan_scene", "infer_environment",
    "infer_camera_focus", "infer_emotion_curve", "recommend_scene_structure",
    "validate_scene_graph", "validate_intent_graph",
    "understand_story", "plan", "summarize_story", "StoryUnderstanding",
]
