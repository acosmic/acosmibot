from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum


class ChannelType(str, Enum):
    """Discord channel types"""
    TEXT = "text"
    VOICE = "voice"
    CATEGORY = "category"
    NEWS = "news"
    STAGE = "stage"
    FORUM = "forum"
    THREAD = "thread"


class DiscordRole(BaseModel):
    """Represents a Discord role for API responses"""
    id: str
    name: str
    color: str = "#99AAB5"  # Default Discord role color
    position: int
    permissions: Optional[str] = None
    managed: bool = False
    mentionable: bool = True
    hoist: bool = False  # Whether role is displayed separately in member list

    @field_validator('id')
    @classmethod
    def validate_role_id(cls, v):
        if not v.isdigit():
            raise ValueError('Role ID must be a numeric string')
        return v

    @field_validator('color')
    @classmethod
    def validate_color(cls, v):
        # Accept hex colors with or without #
        if v.startswith('#'):
            v = v[1:]
        if len(v) != 6 or not all(c in '0123456789ABCDEFabcdef' for c in v):
            raise ValueError('Color must be a valid hex color')
        return f"#{v.upper()}"

    def can_be_assigned_by_bot(self, bot_highest_role_position: int) -> bool:
        """Check if this role can be assigned by the bot"""
        return not self.managed and self.position < bot_highest_role_position

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123456789012345678",
                "name": "Active Member",
                "color": "#5865F2",
                "position": 5,
                "managed": False,
                "mentionable": True,
                "hoist": False
            }
        }


class GuildChannelInfo(BaseModel):
    """Guild channel information for dropdowns"""
    id: str
    name: str
    type: ChannelType
    position: int = 0
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    nsfw: bool = False

    @field_validator('id')
    @classmethod
    def validate_channel_id(cls, v):
        if not v.isdigit():
            raise ValueError('Channel ID must be a numeric string')
        return v

    def is_text_based(self) -> bool:
        """Check if this is a text-based channel that can receive announcements"""
        return self.type in [ChannelType.TEXT, ChannelType.NEWS, ChannelType.FORUM]

    class Config:
        schema_extra = {
            "example": {
                "id": "123456789012345678",
                "name": "general",
                "type": "text",
                "position": 0,
                "category_name": "Text Channels",
                "nsfw": False
            }
        }


class GuildInfo(BaseModel):
    """Basic guild information"""
    id: str
    name: str
    icon: Optional[str] = None
    owner_id: str
    member_count: int
    premium_tier: int = 0
    features: List[str] = Field(default_factory=list)

    @field_validator('id', 'owner_id')
    @classmethod
    def validate_snowflake(cls, v):
        if not v.isdigit():
            raise ValueError('ID must be a numeric string')
        return v

    def get_icon_url(self, size: int = 256) -> Optional[str]:
        """Get the guild icon URL"""
        if self.icon:
            return f"https://cdn.discordapp.com/icons/{self.id}/{self.icon}.png?size={size}"
        return None

    class Config:
        schema_extra = {
            "example": {
                "id": "123456789012345678",
                "name": "My Awesome Server",
                "icon": "a1b2c3d4e5f6g7h8i9j0",
                "owner_id": "987654321098765432",
                "member_count": 150,
                "premium_tier": 2,
                "features": ["COMMUNITY", "NEWS"]
            }
        }


class DiscordUser(BaseModel):
    """Discord user information"""
    id: str
    username: str
    discriminator: str = "0"  # New username system uses "0"
    global_name: Optional[str] = None
    avatar: Optional[str] = None
    bot: bool = False

    @field_validator('id')
    @classmethod
    def validate_user_id(cls, v):
        if not v.isdigit():
            raise ValueError('User ID must be a numeric string')
        return v

    def get_display_name(self) -> str:
        """Get the display name (global_name if available, otherwise username)"""
        return self.global_name or self.username

    def get_avatar_url(self, size: int = 256) -> str:
        """Get the user's avatar URL"""
        if self.avatar:
            return f"https://cdn.discordapp.com/avatars/{self.id}/{self.avatar}.png?size={size}"
        else:
            # Default avatar based on discriminator or user ID
            if self.discriminator != "0":
                default_avatar = int(self.discriminator) % 5
            else:
                default_avatar = (int(self.id) >> 22) % 6
            return f"https://cdn.discordapp.com/embed/avatars/{default_avatar}.png"

    class Config:
        schema_extra = {
            "example": {
                "id": "987654321098765432",
                "username": "cooluser",
                "discriminator": "0",
                "global_name": "Cool User",
                "avatar": "a1b2c3d4e5f6g7h8i9j0",
                "bot": False
            }
        }


class GuildMember(BaseModel):
    """Discord guild member information"""
    user: DiscordUser
    nick: Optional[str] = None
    roles: List[str] = Field(default_factory=list)  # List of role IDs
    joined_at: Optional[str] = None
    premium_since: Optional[str] = None

    def get_display_name(self) -> str:
        """Get the member's display name (nickname > global_name > username)"""
        return self.nick or self.user.get_display_name()

    def has_role(self, role_id: str) -> bool:
        """Check if member has a specific role"""
        return role_id in self.roles

    class Config:
        schema_extra = {
            "example": {
                "user": {
                    "id": "987654321098765432",
                    "username": "cooluser",
                    "global_name": "Cool User"
                },
                "nick": "Super Cool User",
                "roles": ["123456789012345678", "234567890123456789"],
                "joined_at": "2023-01-15T10:30:00.000Z"
            }
        }


class BotPermissions(BaseModel):
    """Bot's permissions in a guild"""
    guild_id: str
    can_manage_roles: bool
    can_send_messages: bool
    can_embed_links: bool
    can_use_external_emojis: bool
    can_add_reactions: bool
    highest_role_position: int
    assignable_roles: List[DiscordRole] = Field(default_factory=list)

    def can_assign_role(self, role: DiscordRole) -> bool:
        """Check if bot can assign a specific role"""
        return (
                self.can_manage_roles and
                not role.managed and
                role.position < self.highest_role_position
        )

    class Config:
        schema_extra = {
            "example": {
                "guild_id": "123456789012345678",
                "can_manage_roles": True,
                "can_send_messages": True,
                "can_embed_links": True,
                "can_use_external_emojis": True,
                "can_add_reactions": True,
                "highest_role_position": 10,
                "assignable_roles": []
            }
        }


class RoleHierarchy(BaseModel):
    """Role hierarchy information for a guild"""
    roles: List[DiscordRole]
    bot_highest_position: int
    assignable_roles: List[DiscordRole]
    managed_roles: List[DiscordRole]

    def get_roles_above_bot(self) -> List[DiscordRole]:
        """Get roles that are above the bot's highest role"""
        return [role for role in self.roles if role.position >= self.bot_highest_position]

    def get_roles_below_bot(self) -> List[DiscordRole]:
        """Get roles that are below the bot's highest role"""
        return [role for role in self.roles if role.position < self.bot_highest_position and not role.managed]

    class Config:
        schema_extra = {
            "example": {
                "roles": [],
                "bot_highest_position": 10,
                "assignable_roles": [],
                "managed_roles": []
            }
        }