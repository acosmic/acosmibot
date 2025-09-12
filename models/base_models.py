from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class RoleAssignmentMode(str, Enum):
    """Role assignment behavior modes"""
    PROGRESSIVE = "progressive"  # Remove old roles when advancing
    ADDITIVE = "additive"  # Keep all earned roles
    SELECTIVE = "selective"  # Custom logic per level


class ExpFormula(str, Enum):
    """Experience calculation formulas"""
    LINEAR = "linear"
    QUADRATIC = "quadratic"
    EXPONENTIAL = "exponential"


class RoleCacheEntry(BaseModel):
    """Cached information about a Discord role"""
    name: str
    color: str = "#99AAB5"
    position: int = 0
    last_verified: datetime = Field(default_factory=datetime.now)
    exists: bool = True
    managed: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LevelingSettings(BaseModel):
    """Leveling system configuration"""
    enabled: bool = True
    exp_per_message: int = Field(default=15, ge=1, le=100)
    exp_cooldown_seconds: int = Field(default=60, ge=0, le=300)
    level_up_announcements: bool = True
    announcement_channel_id: Optional[str] = None
    exp_multiplier: float = Field(default=1.0, ge=0.1, le=5.0)
    max_level: int = Field(default=100, ge=1, le=1000)

    # XP formula settings
    exp_formula: ExpFormula = ExpFormula.QUADRATIC
    base_exp: int = Field(default=100, ge=50, le=1000)
    exp_growth_factor: float = Field(default=1.2, ge=1.0, le=3.0)

    @field_validator('announcement_channel_id')
    def validate_channel_id(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError('Channel ID must be a numeric string')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "exp_per_message": 15,
                "exp_cooldown_seconds": 60,
                "level_up_announcements": True,
                "announcement_channel_id": "123456789012345678",
                "exp_multiplier": 1.0,
                "max_level": 100,
                "exp_formula": "quadratic",
                "base_exp": 100,
                "exp_growth_factor": 1.2
            }
        }


class RoleSystemSettings(BaseModel):
    """Role assignment system configuration"""
    enabled: bool = False
    mode: RoleAssignmentMode = RoleAssignmentMode.PROGRESSIVE

    # Role mappings: level -> [role_ids]
    role_mappings: Dict[str, List[str]] = Field(default_factory=dict)

    # Role cache for validation and display
    role_cache: Dict[str, RoleCacheEntry] = Field(default_factory=dict)

    # Role management options
    remove_previous_roles: bool = True
    max_level_tracked: int = Field(default=50, ge=1, le=1000)

    # Announcement settings
    role_announcement: bool = True
    role_announcement_message: str = "🎉 {user} reached level {level} and earned the {role} role!"

    @field_validator('role_mappings')
    def validate_role_mappings(cls, v):
        """Ensure all keys are valid integers as strings"""
        for level_str in v.keys():
            try:
                level = int(level_str)
                if level < 1 or level > 1000:
                    raise ValueError(f"Level {level} must be between 1 and 1000")
            except ValueError:
                raise ValueError(f"Invalid level key: {level_str}. Must be a number.")
        return v

    @field_validator('role_announcement_message')
    def validate_announcement_message(cls, v):
        """Ensure announcement message has required placeholders"""
        required_placeholders = ['{user}', '{level}']
        for placeholder in required_placeholders:
            if placeholder not in v:
                raise ValueError(f"Announcement message must contain {placeholder}")
        return v

    def get_roles_for_level(self, level: int) -> List[str]:
        """Get role IDs for a specific level"""
        return self.role_mappings.get(str(level), [])

    def set_roles_for_level(self, level: int, role_ids: List[str]):
        """Set role IDs for a specific level"""
        if not role_ids:
            # Remove empty mappings
            self.role_mappings.pop(str(level), None)
        else:
            self.role_mappings[str(level)] = role_ids

    def get_all_configured_levels(self) -> List[int]:
        """Get all levels that have role mappings configured"""
        return sorted([int(level) for level in self.role_mappings.keys()])

    def get_highest_role_level(self, current_level: int) -> Optional[int]:
        """Get the highest level role that the user qualifies for"""
        qualified_levels = [
            int(level) for level in self.role_mappings.keys()
            if int(level) <= current_level
        ]
        return max(qualified_levels) if qualified_levels else None

    def remove_level(self, level: int):
        """Remove all role mappings for a level"""
        self.role_mappings.pop(str(level), None)

    class Config:
        schema_extra = {
            "example": {
                "enabled": True,
                "mode": "progressive",
                "role_mappings": {
                    "5": ["123456789012345678"],
                    "10": ["234567890123456789"],
                    "20": ["345678901234567890"]
                },
                "remove_previous_roles": True,
                "max_level_tracked": 50,
                "role_announcement": True,
                "role_announcement_message": "🎉 {user} reached level {level} and earned the {role} role!"
            }
        }


class GuildLevelingRoleSettings(BaseModel):
    """Combined leveling and role settings for a guild"""
    leveling: LevelingSettings = Field(default_factory=LevelingSettings)
    roles: RoleSystemSettings = Field(default_factory=RoleSystemSettings)

    class Config:
        extra = "allow"
        use_enum_values = True
        validate_assignment = True
        schema_extra = {
            "example": {
                "leveling": {
                    "enabled": True,
                    "exp_per_message": 15,
                    "level_up_announcements": True
                },
                "roles": {
                    "enabled": True,
                    "mode": "progressive",
                    "role_mappings": {
                        "5": ["123456789012345678"]
                    }
                }
            }
        }