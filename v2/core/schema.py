"""Core data models for Soap2Soap V2 pipeline."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class Dialogue:
    speaker_id: str
    text: str
    start_time: float = 0.0
    end_time: float = 0.0

@dataclass
class Character:
    id: str
    name: str
    description: str
    image_path: Optional[str] = None

@dataclass
class Shot:
    index: int
    scene_id: str
    time_range: str
    start_time: float
    end_time: float
    duration: float
    setting_description: str = ""
    environment_description: str = ""
    lighting_setup: str = ""
    color_grading: str = ""
    shot_size: str = ""
    camera_angle: str = ""
    camera_movement: str = ""
    focal_length: str = ""
    depth_of_field: str = ""
    mood_atmosphere: str = ""
    composition: str = ""
    subject_movement: str = ""
    characters: List[str] = field(default_factory=list)
    dialogue: List[Dialogue] = field(default_factory=list)
    t2i_prompt: str = ""
    i2v_prompt: str = ""
    keyframe_path: Optional[str] = None
    video_path: Optional[str] = None
    status: str = "pending"

    @property
    def shot_id(self) -> int:
        return self.index + 1

@dataclass
class PipelineState:
    video_path: str
    style: str
    aspect_ratio: str = "16:9"
    max_shots: int = 10
    dev_mode: bool = True
    generation_mode: str = "consistency"
    keyframe_model: str = "gemini"
    video_model: str = "seeddance"
    dialogue_lang: str = "auto"
    source_frame_grid: bool = False
    finishing_strength: str = "balanced"  # faithful | balanced | strong; used by cinefilter
    characters: List[Character] = field(default_factory=list)
    shots: List[Shot] = field(default_factory=list)
    design_sheet_path: Optional[str] = None
    camera_groups: List[Dict[str, Any]] = field(default_factory=list)
    output_dir: str = "."

    def get_character(self, char_id: str) -> Optional[Character]:
        for c in self.characters:
            if c.id == char_id:
                return c
        return None

    def to_summary(self) -> Dict[str, Any]:
        return {
            "video": self.video_path,
            "style": self.style,
            "finishing_strength": self.finishing_strength if self.style == "cinefilter" else "n/a",
            "characters": len(self.characters),
            "shots": len(self.shots),
            "done": sum(1 for s in self.shots if s.status == "done"),
            "failed": sum(1 for s in self.shots if s.status == "failed"),
        }
