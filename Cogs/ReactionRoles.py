#! /usr/bin/python3.10
from discord.ext import commands
import discord
from logger import AppLogger
from models.reaction_role_manager import ReactionRoleManager
from Dao.ReactionRoleDao import ReactionRoleDao
from Views.ReactionRoleViews import ReactionRoleButtonView, ReactionRoleDropdownView

logger = AppLogger(__name__).get_logger()


class ReactionRoles(commands.Cog):
    """Cog for handling reaction role functionality"""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.manager = ReactionRoleManager(ReactionRoleDao())

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Handle reaction additions for emoji-based reaction roles
            /stat
        Args:
            payload: Raw reaction event data
        """
        if payload.member and payload.member.bot:
            return  # Skip bot reactions

        try:
            # Check if this message has a reaction role config
            config = self.manager.get_reaction_config(payload.message_id)
            if not config or config.get("interaction_type") != "emoji":
                return

            if not config.get("enabled"):
                logger.debug(f"Reaction role {payload.message_id} is disabled")
                return

            # Get the emoji string
            emoji_str = str(payload.emoji)

            # Get emoji to role mapping
            emoji_mappings = config.get("emoji_role_mappings", {})
            role_ids = emoji_mappings.get(emoji_str, [])

            if not role_ids:
                logger.debug(f"No roles mapped for emoji {emoji_str} on message {payload.message_id}")
                return

            # Get guild and member
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                logger.error(f"Guild {payload.guild_id} not found")
                return

            member = guild.get_member(payload.user_id)
            if not member:
                logger.error(f"Member {payload.user_id} not found in guild {payload.guild_id}")
                return

            # Add roles to member
            added_roles = []
            failed_roles = []

            for role_id in role_ids:
                try:
                    role = guild.get_role(int(role_id))
                    if role:
                        await member.add_roles(role)
                        added_roles.append(role.name)
                        logger.info(f"Added role {role.name} to {member.name} via reaction")
                    else:
                        failed_roles.append(f"Role {role_id}")
                        logger.warning(f"Role {role_id} not found in guild {payload.guild_id}")
                except discord.Forbidden:
                    logger.error(f"No permission to add role {role_id} to {member.name}")
                    failed_roles.append(f"Role {role_id} (no permission)")
                except Exception as e:
                    logger.error(f"Error adding role {role_id} to {member.name}: {e}")
                    failed_roles.append(f"Role {role_id} (error)")

            if added_roles:
                logger.info(f"Successfully added {len(added_roles)} roles to {member.name}")

        except Exception as e:
            logger.error(f"Error in on_raw_reaction_add for reaction roles: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """
        Handle reaction removals for emoji-based reaction roles (role removal)

        Args:
            payload: Raw reaction event data
        """
        if payload.member and payload.member.bot:
            return  # Skip bot reactions

        try:
            # Check if this message has a reaction role config
            config = self.manager.get_reaction_config(payload.message_id)
            if not config or config.get("interaction_type") != "emoji":
                return

            if not config.get("enabled"):
                return

            # Check if removal is allowed
            if not config.get("allow_removal", True):
                logger.debug(f"Role removal is disabled for message {payload.message_id}")
                return

            # Get the emoji string
            emoji_str = str(payload.emoji)

            # Get emoji to role mapping
            emoji_mappings = config.get("emoji_role_mappings", {})
            role_ids = emoji_mappings.get(emoji_str, [])

            if not role_ids:
                return

            # Get guild and member
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                logger.error(f"Guild {payload.guild_id} not found")
                return

            member = guild.get_member(payload.user_id)
            if not member:
                logger.error(f"Member {payload.user_id} not found in guild {payload.guild_id}")
                return

            # Remove roles from member
            removed_roles = []
            failed_roles = []

            for role_id in role_ids:
                try:
                    role = guild.get_role(int(role_id))
                    if role and role in member.roles:
                        await member.remove_roles(role)
                        removed_roles.append(role.name)
                        logger.info(f"Removed role {role.name} from {member.name} via reaction removal")
                    elif role:
                        logger.debug(f"Member {member.name} doesn't have role {role.name}")
                    else:
                        failed_roles.append(f"Role {role_id}")
                except discord.Forbidden:
                    logger.error(f"No permission to remove role {role_id} from {member.name}")
                    failed_roles.append(f"Role {role_id} (no permission)")
                except Exception as e:
                    logger.error(f"Error removing role {role_id} from {member.name}: {e}")
                    failed_roles.append(f"Role {role_id} (error)")

            if removed_roles:
                logger.info(f"Successfully removed {len(removed_roles)} roles from {member.name}")

        except Exception as e:
            logger.error(f"Error in on_raw_reaction_remove for reaction roles: {e}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """
        Handle button and dropdown interactions for reaction roles

        Args:
            interaction: Discord interaction event
        """
        # Only handle components (buttons/dropdowns)
        if interaction.type != discord.InteractionType.component:
            return

        try:
            # Check if this is a reaction role interaction
            if not interaction.data.get("custom_id", "").startswith("reaction_role_"):
                return

            custom_id = interaction.data.get("custom_id", "")
            logger.debug(f"Reaction role interaction: {custom_id}")

            # Handle button interactions
            if custom_id.startswith("reaction_role_button_"):
                await self._handle_button_interaction(interaction)

            # Handle dropdown interactions
            elif custom_id.startswith("reaction_role_dropdown_"):
                await self._handle_dropdown_interaction(interaction)

        except Exception as e:
            logger.error(f"Error handling reaction role interaction: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=True)
                await interaction.followup.send(
                    "An error occurred while processing your request.",
                    ephemeral=True
                )
            except:
                pass

    async def _handle_button_interaction(self, interaction: discord.Interaction):
        """
        Handle button interaction for reaction roles

        Args:
            interaction: Discord interaction
        """
        try:
            # Extract message ID from custom_id
            custom_id_parts = interaction.data.get("custom_id", "").split("_")
            if len(custom_id_parts) < 4:
                logger.error(f"Invalid button custom_id format: {interaction.data.get('custom_id')}")
                return

            message_id = int(custom_id_parts[3])
            button_index = int(custom_id_parts[4]) if len(custom_id_parts) > 4 else 0

            # Get reaction role config
            config = self.manager.get_reaction_config(message_id)
            if not config or config.get("interaction_type") != "button":
                logger.warning(f"No button reaction role config found for message {message_id}")
                return

            if not config.get("enabled"):
                await interaction.response.defer(ephemeral=True)
                await interaction.followup.send("This reaction role is disabled.", ephemeral=True)
                return

            # Get button config
            button_configs = config.get("button_configs", [])
            if button_index >= len(button_configs):
                logger.error(f"Button index {button_index} out of range for message {message_id}")
                return

            button_config = button_configs[button_index]
            role_ids = button_config.get("role_ids", [])

            if not role_ids:
                await interaction.response.defer(ephemeral=True)
                await interaction.followup.send("No roles are assigned to this button.", ephemeral=True)
                return

            # Add roles to member
            await interaction.response.defer(ephemeral=True)
            await self._add_roles_to_member(
                interaction,
                role_ids,
                interaction.guild,
                interaction.user
            )

        except Exception as e:
            logger.error(f"Error handling button interaction: {e}")
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            await interaction.followup.send(
                "An error occurred while processing your request.",
                ephemeral=True
            )

    async def _handle_dropdown_interaction(self, interaction: discord.Interaction):
        """
        Handle dropdown interaction for reaction roles

        Args:
            interaction: Discord interaction
        """
        try:
            # Extract message ID from custom_id
            custom_id_parts = interaction.data.get("custom_id", "").split("_")
            if len(custom_id_parts) < 4:
                logger.error(f"Invalid dropdown custom_id format: {interaction.data.get('custom_id')}")
                return

            message_id = int(custom_id_parts[3])

            # Get reaction role config
            config = self.manager.get_reaction_config(message_id)
            if not config or config.get("interaction_type") != "dropdown":
                logger.warning(f"No dropdown reaction role config found for message {message_id}")
                return

            if not config.get("enabled"):
                await interaction.response.defer(ephemeral=True)
                await interaction.followup.send("This reaction role is disabled.", ephemeral=True)
                return

            # Get selected values
            selected_values = interaction.data.get("values", [])
            if not selected_values:
                await interaction.response.defer(ephemeral=True)
                await interaction.followup.send("No option was selected.", ephemeral=True)
                return

            # Get dropdown config
            dropdown_config = config.get("dropdown_config", {})
            options = dropdown_config.get("options", [])

            # Collect all roles from selected options
            all_role_ids = []
            selected_labels = []

            for selected_value in selected_values:
                # Find matching option
                matching_option = next(
                    (opt for opt in options if str(opt.get("value", opt.get("label"))) == selected_value),
                    None
                )

                if matching_option:
                    role_ids = matching_option.get("role_ids", [])
                    all_role_ids.extend(role_ids)
                    selected_labels.append(matching_option.get("label", selected_value))

            if not all_role_ids:
                await interaction.response.defer(ephemeral=True)
                await interaction.followup.send(
                    f"No roles assigned to selected option(s): {', '.join(selected_labels)}",
                    ephemeral=True
                )
                return

            # Add roles to member
            await interaction.response.defer(ephemeral=True)
            await self._add_roles_to_member(
                interaction,
                all_role_ids,
                interaction.guild,
                interaction.user
            )

        except Exception as e:
            logger.error(f"Error handling dropdown interaction: {e}")
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            await interaction.followup.send(
                "An error occurred while processing your request.",
                ephemeral=True
            )

    async def _add_roles_to_member(
            self,
            interaction: discord.Interaction,
            role_ids: list,
            guild: discord.Guild,
            user: discord.User
    ):
        """
        Helper method to add roles to a member

        Args:
            interaction: Discord interaction (for followup response)
            role_ids: List of role IDs to add
            guild: Discord guild
            user: Discord user
        """
        try:
            member = guild.get_member(user.id)
            if not member:
                await interaction.followup.send(
                    "Could not find your member data in this server.",
                    ephemeral=True
                )
                return

            added_roles = []
            failed_roles = []

            for role_id in role_ids:
                try:
                    role = guild.get_role(int(role_id))
                    if role:
                        if role not in member.roles:
                            await member.add_roles(role)
                            added_roles.append(role.name)
                        else:
                            added_roles.append(f"{role.name} (already had)")
                    else:
                        failed_roles.append(f"Role {role_id}")
                        logger.warning(f"Role {role_id} not found in guild {guild.id}")
                except discord.Forbidden:
                    logger.error(f"No permission to add role {role_id} to {member.name}")
                    failed_roles.append(f"Role (no permission)")
                except Exception as e:
                    logger.error(f"Error adding role {role_id} to {member.name}: {e}")
                    failed_roles.append(f"Role (error)")

            # Send response
            if added_roles:
                msg = f"✅ Added roles: {', '.join(added_roles)}"
                if failed_roles:
                    msg += f"\n❌ Failed: {', '.join(failed_roles)}"
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.followup.send(
                    f"❌ Failed to add roles: {', '.join(failed_roles)}",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in _add_roles_to_member: {e}")
            await interaction.followup.send(
                "An error occurred while adding roles.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(ReactionRoles(bot))
