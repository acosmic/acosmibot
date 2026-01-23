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
    level_up_announcements: bool = False  # Default to False to prevent unwanted spam
    announcement_channel_id: Optional[str] = None

    # Custom announcement message templates
    level_up_message: str = "🎉 {mention} GUILD LEVEL UP! You have reached level {level}! Gained {credits} Credits!"
    level_up_message_with_streak: str = "🎉 {mention} GUILD LEVEL UP! You have reached level {level}! Gained {credits} Credits! {base_credits} + {streak_bonus} from {streak}x Streak!"

    exp_multiplier: float = Field(default=1.0, ge=0.1, le=5.0)
    max_level: int = Field(default=100, ge=1, le=1000000)

    # XP formula settings
    exp_formula: ExpFormula = ExpFormula.QUADRATIC
    base_exp: int = Field(default=100, ge=50, le=1000)
    exp_growth_factor: float = Field(default=1.2, ge=1.0, le=3.0)

    # Daily reward settings
    daily_announcements_enabled: bool = False
    daily_announcement_channel_id: Optional[str] = None
    daily_announcement_message: str = "💰 {mention} claimed their daily reward! +{credits} Credits!"
    daily_announcement_message_with_streak: str = "💰 {mention} claimed their daily reward! +{credits} Credits! ({base_credits} + {streak_bonus} from {streak}x streak!)"

    @field_validator('announcement_channel_id', 'daily_announcement_channel_id')
    def validate_channel_id(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError('Channel ID must be a numeric string')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "level_up_announcements": False,
                "level_up_message": "🎉 {mention} GUILD LEVEL UP! You have reached level {level}! Gained {credits} Credits!",
                "announcement_channel_id": "123456789012345678",
                "exp_multiplier": 1.0,
                "max_level": 100,
                "exp_formula": "quadratic",
                "base_exp": 100,
                "exp_growth_factor": 1.2
            }
        }


class RoleMappingEntry(BaseModel):
    """Entry for role mappings with custom announcement message"""
    role_ids: List[str] = Field(default_factory=list)
    announcement_message: str = "🎉 {mention} reached level {level} and earned the {role} role!"


class RoleSystemSettings(BaseModel):
    """Role assignment system configuration"""
    enabled: bool = False
    mode: RoleAssignmentMode = RoleAssignmentMode.PROGRESSIVE

    # Role mappings: level -> RoleMappingEntry (with role_ids and custom message)
    role_mappings: Dict[str, RoleMappingEntry] = Field(default_factory=dict)

    # Role cache for validation and display
    role_cache: Dict[str, RoleCacheEntry] = Field(default_factory=dict)

    # Role management options
    remove_previous_roles: bool = True

    # Announcement settings
    role_announcement: bool = False  # Default to False to prevent unwanted spam
    announcement_channel_id: Optional[str] = None

    @field_validator('role_mappings')
    def validate_role_mappings(cls, v):
        """Ensure all keys are valid integers as strings"""
        for level_str in v.keys():
            try:
                level = int(level_str)
                if level < 0 or level > 1000000:
                    raise ValueError(f"Level {level} must be between 0 and 1000000")
            except ValueError:
                raise ValueError(f"Invalid level key: {level_str}. Must be a number.")
        return v

    def get_roles_for_level(self, level: int) -> List[str]:
        """Get role IDs for a specific level"""
        entry = self.role_mappings.get(str(level))
        return entry.role_ids if entry else []

    def get_message_for_level(self, level: int) -> str:
        """Get announcement message for a specific level"""
        entry = self.role_mappings.get(str(level))
        return entry.announcement_message if entry else "🎉 {mention} reached level {level} and earned the {role} role!"

    def set_roles_for_level(self, level: int, role_ids: List[str], message: Optional[str] = None):
        """Set role IDs and optionally message for a specific level"""
        if not role_ids:
            # Remove empty mappings
            self.role_mappings.pop(str(level), None)
        else:
            entry = RoleMappingEntry(
                role_ids=role_ids,
                announcement_message=message if message else "🎉 {mention} reached level {level} and earned the {role} role!"
            )
            self.role_mappings[str(level)] = entry

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
                    "5": {
                        "role_ids": ["123456789012345678"],
                        "announcement_message": "🎉 {mention} reached level 5!"
                    },
                    "10": {
                        "role_ids": ["234567890123456789"],
                        "announcement_message": "🎉 {mention} reached level 10!"
                    }
                },
                "remove_previous_roles": True,
                "role_announcement": False
            }
        }


class AIChannelMode(str, Enum):
    """AI channel restriction modes"""
    ALL = "all"  # AI works in all channels
    SPECIFIC = "specific"  # AI only works in specified channels
    EXCLUDE = "exclude"  # AI works in all channels except specified


class AISettings(BaseModel):
    """AI configuration for a guild"""
    enabled: bool = False
    instructions: str = ""
    model: str = "gpt-4o-mini"
    channel_mode: AIChannelMode = AIChannelMode.ALL
    allowed_channels: List[str] = Field(default_factory=list)
    excluded_channels: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "enabled": True,
                "instructions": "You are a friendly helper bot.",
                "model": "gpt-4o-mini",
                "channel_mode": "exclude",
                "allowed_channels": [],
                "excluded_channels": ["123456789", "987654321"]
            }
        }


class SlotsConfig(BaseModel):
    """Slots game configuration for a guild"""
    enabled: bool = False
    symbols: List[str] = Field(default_factory=lambda: [
        "🍒", "🍋", "🍊", "🍇", "🍎", "🍌", "⭐", "🔔", "💎", "🎰", "🍀", "❤️"
    ])

    class Config:
        schema_extra = {
            "example": {
                "enabled": True,
                "symbols": ["🍒", "🍋", "🍊", "🍇", "🍎", "🍌", "⭐", "🔔", "💎", "🎰", "🍀", "❤️"]
            }
        }


class GamesSettings(BaseModel):
    """Games configuration for a guild"""
    enabled: bool = False
    slots_config: SlotsConfig = Field(default_factory=SlotsConfig, alias="slots-config")

    class Config:
        populate_by_name = True
        schema_extra = {
            "example": {
                "enabled": True,
                "slots-config": {
                    "enabled": True,
                    "symbols": ["🍒", "🍋", "🍊", "🍇", "🍎", "🍌", "⭐", "🔔", "💎", "🎰", "🍀", "❤️"]
                }
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
                    "level_up_announcements": False,
                    "level_up_message": "🎉 {mention} reached level {level}!"
                },
                "roles": {
                    "enabled": True,
                    "mode": "progressive",
                    "role_mappings": {
                        "5": {
                            "role_ids": ["123456789012345678"],
                            "announcement_message": "Congrats!"
                        }
                    }
                }
            }
        }


class CrossServerPortalSettings(BaseModel):
    """Cross-server portal system configuration"""
    enabled: bool = False
    channel_id: Optional[str] = None
    public_listing: bool = True
    display_name: Optional[str] = None
    portal_cost: int = 1000

    @field_validator('channel_id')
    def validate_channel_id(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError('Channel ID must be a numeric string')
        return v

    class Config:
        schema_extra = {
            "example": {
                "enabled": True,
                "channel_id": "123456789012345678",
                "public_listing": True,
                "display_name": "My Awesome Server",
                "portal_cost": 1000
            }
        }


class InstagramEmbedSettings(BaseModel):
    """Instagram embed configuration for a guild"""
    enabled: bool = True
    show_captions: bool = True
    show_engagement: bool = True
    show_author: bool = True

    class Config:
        schema_extra = {
            "example": {
                "enabled": True,
                "show_captions": True,
                "show_engagement": True,
                "show_author": True
            }
        }


class BetterEmbedsSettings(BaseModel):
    """Better embeds configuration for various link types"""
    enabled: bool = True
    instagram: InstagramEmbedSettings = Field(default_factory=InstagramEmbedSettings)

    class Config:
        schema_extra = {
            "example": {
                "enabled": True,
                "instagram": {
                    "enabled": True,
                    "show_captions": True,
                    "show_engagement": True,
                    "show_author": True
                }
            }
        }


class GuildSettings(BaseModel):
    """Complete guild settings structure"""
    leveling: LevelingSettings = Field(default_factory=LevelingSettings)
    roles: RoleSystemSettings = Field(default_factory=RoleSystemSettings)
    ai: AISettings = Field(default_factory=AISettings)
    games: GamesSettings = Field(default_factory=GamesSettings)
    cross_server_portal: CrossServerPortalSettings = Field(default_factory=CrossServerPortalSettings)
    better_embeds: BetterEmbedsSettings = Field(default_factory=BetterEmbedsSettings)

    class Config:
        extra = "allow"
        use_enum_values = True
        validate_assignment = True