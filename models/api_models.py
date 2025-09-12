from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional
from models.base_models import RoleAssignmentMode, ExpFormula, GuildLevelingRoleSettings
from models.discord_models import DiscordRole, GuildChannelInfo


class UpdateLevelingSettingsRequest(BaseModel):
    """Request model for updating leveling settings"""
    enabled: Optional[bool] = None
    exp_per_message: Optional[int] = Field(None, ge=1, le=100)
    exp_cooldown_seconds: Optional[int] = Field(None, ge=0, le=300)
    level_up_announcements: Optional[bool] = None
    announcement_channel_id: Optional[str] = None
    exp_multiplier: Optional[float] = Field(None, ge=0.1, le=5.0)
    max_level: Optional[int] = Field(None, ge=1, le=1000)
    exp_formula: Optional[ExpFormula] = None
    base_exp: Optional[int] = Field(None, ge=50, le=1000)
    exp_growth_factor: Optional[float] = Field(None, ge=1.0, le=3.0)

    @field_validator('announcement_channel_id')
    @classmethod
    def validate_channel_id(cls, v):
        if v is not None and v != "" and not v.isdigit():
            raise ValueError('Channel ID must be a numeric string')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "exp_per_message": 20,
                "level_up_announcements": True,
                "announcement_channel_id": "123456789012345678"
            }
        }


class UpdateRoleSettingsRequest(BaseModel):
    """Request model for updating role settings"""
    enabled: Optional[bool] = None
    mode: Optional[RoleAssignmentMode] = None
    remove_previous_roles: Optional[bool] = None
    max_level_tracked: Optional[int] = Field(None, ge=1, le=1000)
    role_announcement: Optional[bool] = None
    role_announcement_message: Optional[str] = None

    @field_validator('role_announcement_message')
    @classmethod
    def validate_announcement_message(cls, v):
        if v is not None:
            required_placeholders = ['{user}', '{level}']
            for placeholder in required_placeholders:
                if placeholder not in v:
                    raise ValueError(f"Announcement message must contain {placeholder}")
        return v

    class Config:
        schema_extra = {
            "example": {
                "enabled": True,
                "mode": "progressive",
                "role_announcement": True
            }
        }


class RoleMappingRequest(BaseModel):
    """Request model for updating role mappings"""
    level: int = Field(ge=1, le=1000)
    role_ids: List[str]

    @field_validator('role_ids')
    @classmethod
    def validate_role_ids(cls, v):
        """Ensure all role IDs are valid Discord snowflakes"""
        for role_id in v:
            if not role_id.isdigit():
                raise ValueError(f"Invalid role ID: {role_id}")
        return v

    class Config:
        schema_extra = {
            "example": {
                "level": 5,
                "role_ids": ["123456789012345678", "234567890123456789"]
            }
        }


class RoleMappingResponse(BaseModel):
    """Response model for role mapping information"""
    level: int
    roles: List[DiscordRole]

    class Config:
        schema_extra = {
            "example": {
                "level": 5,
                "roles": [
                    {
                        "id": "123456789012345678",
                        "name": "Active Member",
                        "color": "#5865F2",
                        "position": 5
                    }
                ]
            }
        }


class GuildConfigResponse(BaseModel):
    """Complete guild configuration response"""
    guild_id: str
    guild_name: str
    settings: GuildLevelingRoleSettings
    available_roles: List[DiscordRole]
    available_channels: List[GuildChannelInfo]
    role_mappings: List[RoleMappingResponse]

    class Config:
        schema_extra = {
            "example": {
                "guild_id": "123456789012345678",
                "guild_name": "My Awesome Server",
                "settings": {
                    "leveling": {"enabled": True},
                    "roles": {"enabled": True}
                },
                "available_roles": [],
                "available_channels": [],
                "role_mappings": []
            }
        }


class ValidationError(BaseModel):
    """Validation error response"""
    field: str
    message: str
    code: str

    class Config:
        schema_extra = {
            "example": {
                "field": "exp_per_message",
                "message": "Value must be between 1 and 100",
                "code": "value_error"
            }
        }


class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    message: str
    data: Optional[dict] = None
    errors: Optional[List[ValidationError]] = None

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Settings updated successfully",
                "data": None,
                "errors": None
            }
        }


class APIErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    errors: Optional[List[ValidationError]] = None

    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "message": "Validation failed",
                "error_code": "validation_error",
                "errors": [
                    {
                        "field": "exp_per_message",
                        "message": "Value must be between 1 and 100",
                        "code": "value_error"
                    }
                ]
            }
        }


class BulkRoleMappingRequest(BaseModel):
    """Request model for updating multiple role mappings at once"""
    mappings: Dict[str, List[str]]  # level -> role_ids

    @field_validator('mappings')
    @classmethod
    def validate_mappings(cls, v):
        """Validate all levels and role IDs"""
        for level_str, role_ids in v.items():
            # Validate level
            try:
                level = int(level_str)
                if level < 1 or level > 1000:
                    raise ValueError(f"Level {level} must be between 1 and 1000")
            except ValueError:
                raise ValueError(f"Invalid level key: {level_str}")

            # Validate role IDs
            for role_id in role_ids:
                if not role_id.isdigit():
                    raise ValueError(f"Invalid role ID: {role_id}")

        return v

    class Config:
        schema_extra = {
            "example": {
                "mappings": {
                    "5": ["123456789012345678"],
                    "10": ["234567890123456789"],
                    "20": ["345678901234567890", "456789012345678901"]
                }
            }
        }


class GuildStatsResponse(BaseModel):
    """Guild statistics response"""
    guild_id: str
    total_members: int
    members_with_levels: int
    highest_level: int
    total_exp_distributed: int
    roles_configured: int
    leveling_enabled: bool
    role_system_enabled: bool

    class Config:
        schema_extra = {
            "example": {
                "guild_id": "123456789012345678",
                "total_members": 150,
                "members_with_levels": 89,
                "highest_level": 25,
                "total_exp_distributed": 45670,
                "roles_configured": 5,
                "leveling_enabled": True,
                "role_system_enabled": True
            }
        }


class PreviewRoleAssignmentRequest(BaseModel):
    """Request to preview what roles a user would get at a specific level"""
    level: int = Field(ge=1, le=1000)
    user_id: Optional[str] = None  # Optional user ID to check current roles

    class Config:
        schema_extra = {
            "example": {
                "level": 15,
                "user_id": "987654321098765432"
            }
        }


class PreviewRoleAssignmentResponse(BaseModel):
    """Response showing what roles would be assigned"""
    level: int
    roles_to_add: List[DiscordRole]
    roles_to_remove: List[DiscordRole]
    current_user_roles: Optional[List[DiscordRole]] = None

    class Config:
        schema_extra = {
            "example": {
                "level": 15,
                "roles_to_add": [
                    {
                        "id": "345678901234567890",
                        "name": "Veteran",
                        "color": "#FF5733",
                        "position": 8
                    }
                ],
                "roles_to_remove": [
                    {
                        "id": "123456789012345678",
                        "name": "Active Member",
                        "color": "#5865F2",
                        "position": 5
                    }
                ]
            }
        }