#! /usr/bin/python3.10
"""
AIImage Entity

Represents AI-generated or analyzed images in the system.
Tracks image generation (DALL-E) and image analysis (GPT-4 Vision) usage.
"""

from Entities.BaseEntity import BaseEntity
from typing import Optional
from datetime import datetime


class AIImage(BaseEntity):
    """Entity representing an AI image operation (generation or analysis)"""

    def __init__(
        self,
        id: Optional[int] = None,
        guild_id: Optional[str] = None,
        user_id: Optional[str] = None,
        type: str = 'generation',  # 'generation' or 'analysis'
        prompt: Optional[str] = None,
        image_url: Optional[str] = None,
        revised_prompt: Optional[str] = None,
        analysis_result: Optional[str] = None,
        model: Optional[str] = None,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.guild_id = guild_id
        self.user_id = user_id
        self.type = type
        self.prompt = prompt
        self.image_url = image_url
        self.revised_prompt = revised_prompt
        self.analysis_result = analysis_result
        self.model = model
        self.size = size
        self.quality = quality
        self.created_at = created_at or datetime.now()

    def is_generation(self) -> bool:
        """Check if this is an image generation operation"""
        return self.type == 'generation'

    def is_analysis(self) -> bool:
        """Check if this is an image analysis operation"""
        return self.type == 'analysis'

    def __repr__(self):
        return f"<AIImage id={self.id} type={self.type} guild_id={self.guild_id} user_id={self.user_id}>"
