#! /usr/bin/python3.10
import discord
import logging
import json
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class ReactionRoleButtonView(discord.ui.View):
    """View for handling button-based reaction roles"""

    def __init__(self, config: Dict[str, Any], timeout: int = 180):
        """
        Initialize button view for reaction roles

        Args:
            config: Reaction role configuration from database
            timeout: Button interaction timeout in seconds (default 180)
        """
        super().__init__(timeout=timeout)
        self.config = config
        self.message: Optional[discord.Message] = None

        # Parse button configs
        button_configs = config.get("button_configs", [])

        # Add buttons dynamically
        for idx, button_config in enumerate(button_configs):
            btn = discord.ui.Button(
                label=button_config.get("label", f"Button {idx + 1}"),
                style=self._get_button_style(button_config.get("style", "primary")),
                custom_id=f"reaction_role_button_{config['message_id']}_{idx}",
                emoji=button_config.get("emoji") if button_config.get("emoji") else discord.utils.MISSING
            )
            btn.callback = self._create_button_callback(button_config, idx)
            self.add_item(btn)

    def _get_button_style(self, style_str: str) -> discord.ButtonStyle:
        """
        Convert style string to discord.ButtonStyle

        Args:
            style_str: Style string (primary, secondary, success, danger)

        Returns:
            discord.ButtonStyle enum value
        """
        styles = {
            "primary": discord.ButtonStyle.primary,
            "secondary": discord.ButtonStyle.secondary,
            "success": discord.ButtonStyle.success,
            "danger": discord.ButtonStyle.danger,
        }
        return styles.get(style_str.lower(), discord.ButtonStyle.primary)

    def _create_button_callback(self, button_config: Dict[str, Any], index: int):
        """
        Create callback function for a button

        Args:
            button_config: Button configuration
            index: Button index

        Returns:
            Callback function
        """
        async def callback(interaction: discord.Interaction):
            try:
                # Defer response
                await interaction.response.defer(ephemeral=True)

                # Get role IDs from button config
                role_ids = button_config.get("role_ids", [])

                if not role_ids:
                    await interaction.followup.send(
                        "No roles are assigned to this button.",
                        ephemeral=True
                    )
                    return

                # Get member
                member = interaction.user
                if not isinstance(member, discord.Member):
                    member = interaction.guild.get_member(interaction.user.id)
                    if not member:
                        await interaction.followup.send(
                            "Could not find your member data.",
                            ephemeral=True
                        )
                        return

                # Add roles to member
                added_roles = []
                failed_roles = []

                for role_id in role_ids:
                    try:
                        role = interaction.guild.get_role(int(role_id))
                        if role:
                            await member.add_roles(role)
                            added_roles.append(role.name)
                        else:
                            failed_roles.append(f"Role ID {role_id}")
                    except discord.Forbidden:
                        failed_roles.append(f"{role.name if role else f'Role {role_id}'} (no permission)")
                    except Exception as e:
                        logger.error(f"Error adding role {role_id} to {member.id}: {e}")
                        failed_roles.append(f"Role {role_id} (error)")

                # Send response
                if added_roles:
                    msg = f"Added roles: {', '.join(added_roles)}"
                    if failed_roles:
                        msg += f"\n\nFailed to add: {', '.join(failed_roles)}"
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.followup.send(
                        f"Failed to add roles: {', '.join(failed_roles)}",
                        ephemeral=True
                    )

            except Exception as e:
                logger.error(f"Error in button callback: {e}")
                try:
                    await interaction.followup.send(
                        "An error occurred while processing your request.",
                        ephemeral=True
                    )
                except:
                    pass

        return callback


class ReactionRoleDropdownView(discord.ui.View):
    """View for handling dropdown-based reaction roles"""

    def __init__(self, config: Dict[str, Any], timeout: int = 180):
        """
        Initialize dropdown view for reaction roles

        Args:
            config: Reaction role configuration from database
            timeout: Dropdown interaction timeout in seconds (default 180)
        """
        super().__init__(timeout=timeout)
        self.config = config
        self.message: Optional[discord.Message] = None

        # Parse dropdown config
        dropdown_config = config.get("dropdown_config", {})
        options = dropdown_config.get("options", [])

        if not options:
            logger.warning(f"No options in dropdown config for message {config['message_id']}")
            return

        # Convert options to Discord Select options
        select_options = []
        for opt in options:
            select_options.append(
                discord.SelectOption(
                    label=opt.get("label", ""),
                    value=str(opt.get("value", opt.get("label", ""))),
                    emoji=opt.get("emoji") if opt.get("emoji") else discord.utils.MISSING,
                    description=opt.get("description")
                )
            )

        # Create select menu
        select = discord.ui.Select(
            placeholder=dropdown_config.get("placeholder", "Select an option..."),
            min_values=dropdown_config.get("min_values", 1),
            max_values=dropdown_config.get("max_values", 1),
            options=select_options,
            custom_id=f"reaction_role_dropdown_{config['message_id']}"
        )

        select.callback = self._create_dropdown_callback(options)
        self.add_item(select)

    def _create_dropdown_callback(self, options: List[Dict[str, Any]]):
        """
        Create callback function for dropdown

        Args:
            options: List of option configurations

        Returns:
            Callback function
        """
        async def callback(interaction: discord.Interaction):
            try:
                # Defer response
                await interaction.response.defer(ephemeral=True)

                # Get selected values
                selected_values = interaction.data.get("values", [])

                if not selected_values:
                    await interaction.followup.send(
                        "No option was selected.",
                        ephemeral=True
                    )
                    return

                # Get member
                member = interaction.user
                if not isinstance(member, discord.Member):
                    member = interaction.guild.get_member(interaction.user.id)
                    if not member:
                        await interaction.followup.send(
                            "Could not find your member data.",
                            ephemeral=True
                        )
                        return

                # Process each selected value
                added_roles = []
                failed_roles = []

                for selected_value in selected_values:
                    # Find matching option
                    matching_option = next(
                        (opt for opt in options if str(opt.get("value", opt.get("label"))) == selected_value),
                        None
                    )

                    if not matching_option:
                        failed_roles.append(f"Unknown option: {selected_value}")
                        continue

                    role_ids = matching_option.get("role_ids", [])

                    for role_id in role_ids:
                        try:
                            role = interaction.guild.get_role(int(role_id))
                            if role:
                                await member.add_roles(role)
                                added_roles.append(role.name)
                            else:
                                failed_roles.append(f"Role ID {role_id}")
                        except discord.Forbidden:
                            role_name = role.name if role else f"Role {role_id}"
                            failed_roles.append(f"{role_name} (no permission)")
                        except Exception as e:
                            logger.error(f"Error adding role {role_id} to {member.id}: {e}")
                            failed_roles.append(f"Role {role_id} (error)")

                # Send response
                if added_roles:
                    msg = f"Added roles: {', '.join(added_roles)}"
                    if failed_roles:
                        msg += f"\n\nFailed to add: {', '.join(failed_roles)}"
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.followup.send(
                        f"Failed to add roles: {', '.join(failed_roles)}",
                        ephemeral=True
                    )

            except Exception as e:
                logger.error(f"Error in dropdown callback: {e}")
                try:
                    await interaction.followup.send(
                        "An error occurred while processing your request.",
                        ephemeral=True
                    )
                except:
                    pass

        return callback
