import discord
from discord.ext import commands
import time

from Dao.GuildDao import GuildDao

class ModerationLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_dao = GuildDao()

    def _get_moderation_settings(self, guild_id):
        """Fetches the moderation settings for a given guild."""
        if guild_id is None:
            return None
        settings = self.guild_dao.get_guild_settings(guild_id)
        if settings is None:
            return None
        return settings.get("moderation")

    async def _get_log_channel(self, channel_id):
        """Fetches a channel object from an ID."""
        if not channel_id:
            return None
        channel = self.bot.get_channel(int(channel_id))
        return channel

    def _get_event_channel_id(self, mod_settings, event_name, fallback_key):
        """
        Get the channel ID for a specific event, falling back to global channel if not set.

        Args:
            mod_settings: The moderation settings dict
            event_name: The event name (e.g., 'on_message_edit')
            fallback_key: The fallback channel key (e.g., 'mod_log_channel_id')

        Returns:
            Channel ID string or None
        """
        # Try to get event-specific channel first
        event_settings = mod_settings.get("events", {}).get(event_name, {})
        event_channel_id = event_settings.get("channel_id")

        if event_channel_id:
            return event_channel_id

        # Fall back to global channel
        return mod_settings.get(fallback_key)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        mod_settings = self._get_moderation_settings(member.guild.id)
        if not mod_settings or not mod_settings.get("enabled") or not mod_settings.get("events", {}).get("on_member_join", {}).get("enabled"):
            return

        event_settings = mod_settings["events"]["on_member_join"]
        # Use event-specific channel or fall back to member_activity_channel_id
        channel_id = self._get_event_channel_id(mod_settings, "on_member_join", "member_activity_channel_id")
        log_channel = await self._get_log_channel(channel_id)

        if log_channel:
            message = event_settings.get("message", "{user.mention} has joined the server.").format(user=member)
            color = int(event_settings.get("color", "#00ff00").replace("#", "0x"), 16)

            embed = discord.Embed(
                title="Member Joined",
                description=message,
                color=color
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>")
            embed.add_field(name="Time", value=f"<t:{int(discord.utils.utcnow().timestamp())}:F> (<t:{int(discord.utils.utcnow().timestamp())}:R>)")
            embed.set_footer(text=f"ID: {member.id}")
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        mod_settings = self._get_moderation_settings(member.guild.id)
        if not mod_settings or not mod_settings.get("enabled") or not mod_settings.get("events", {}).get("on_member_remove", {}).get("enabled"):
            return

        # Check if user was kicked or banned - if so, skip the "left" message
        # since those actions have their own log entries
        try:
            async for entry in member.guild.audit_logs(limit=5):
                # Only check recent entries (within last 5 seconds)
                if (discord.utils.utcnow() - entry.created_at).total_seconds() > 5:
                    break
                # If this member was kicked or banned, don't post "left" message
                if entry.target and entry.target.id == member.id:
                    if entry.action in (discord.AuditLogAction.kick, discord.AuditLogAction.ban):
                        return  # Skip - the kick/ban handler will log this
        except discord.Forbidden:
            pass  # Bot doesn't have audit log permission, continue normally

        event_settings = mod_settings["events"]["on_member_remove"]
        # Use event-specific channel or fall back to member_activity_channel_id
        channel_id = self._get_event_channel_id(mod_settings, "on_member_remove", "member_activity_channel_id")
        log_channel = await self._get_log_channel(channel_id)

        if log_channel:
            message = event_settings.get("message", "{user.name} has left the server.").format(user=member)
            color = int(event_settings.get("color", "#ff0000").replace("#", "0x"), 16)

            embed = discord.Embed(
                title="Member Left",
                description=message,
                color=color
            )
            embed.add_field(name="Time", value=f"<t:{int(discord.utils.utcnow().timestamp())}:F> (<t:{int(discord.utils.utcnow().timestamp())}:R>)")
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"ID: {member.id}")
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        mod_settings = self._get_moderation_settings(message.guild.id)
        if not mod_settings or not mod_settings.get("enabled") or not mod_settings.get("events", {}).get("on_message_delete", {}).get("enabled"):
            return

        # Use event-specific channel or fall back to mod_log_channel_id
        channel_id = self._get_event_channel_id(mod_settings, "on_message_delete", "mod_log_channel_id")
        log_channel = await self._get_log_channel(channel_id)

        if log_channel:
            embed = discord.Embed(
                title="Message Deleted",
                description=f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}",
                color=discord.Color.orange()
            )
            if message.content:
                embed.add_field(name="Content", value=message.content[:1024], inline=False)
            embed.add_field(name="Time", value=f"<t:{int(discord.utils.utcnow().timestamp())}:F> (<t:{int(discord.utils.utcnow().timestamp())}:R>)")
            embed.set_footer(text=f"Author ID: {message.author.id} | Message ID: {message.id}")
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content:
            return

        mod_settings = self._get_moderation_settings(before.guild.id)
        if not mod_settings or not mod_settings.get("enabled") or not mod_settings.get("events", {}).get("on_message_edit", {}).get("enabled"):
            return

        # Use event-specific channel or fall back to mod_log_channel_id
        channel_id = self._get_event_channel_id(mod_settings, "on_message_edit", "mod_log_channel_id")
        log_channel = await self._get_log_channel(channel_id)

        if log_channel:
            embed = discord.Embed(
                title="Message Edited",
                description=f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n[Jump to Message]({after.jump_url})",
                color=discord.Color.blue()
            )
            embed.add_field(name="Before", value=before.content[:1024], inline=False)
            embed.add_field(name="After", value=after.content[:1024], inline=False)
            embed.add_field(name="Time", value=f"<t:{int(discord.utils.utcnow().timestamp())}:F> (<t:{int(discord.utils.utcnow().timestamp())}:R>)")
            embed.set_footer(text=f"Author ID: {before.author.id} | Message ID: {after.id}")
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        mod_settings = self._get_moderation_settings(before.guild.id)
        if not mod_settings or not mod_settings.get("enabled"):
            return

        # Nickname changes
        if before.nick != after.nick and mod_settings.get("events", {}).get("on_member_update", {}).get("nickname_change", {}).get("enabled"):
            # Use event-specific channel for nickname_change sub-event, or fall back to mod_log_channel_id
            nickname_settings = mod_settings.get("events", {}).get("on_member_update", {}).get("nickname_change", {})
            channel_id = nickname_settings.get("channel_id") or mod_settings.get("mod_log_channel_id")
            log_channel = await self._get_log_channel(channel_id)

            if log_channel:
                embed = discord.Embed(
                    title="Nickname Changed",
                    description=f"**Member:** {before.mention}",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Before", value=before.nick or before.name, inline=False)
                embed.add_field(name="After", value=after.nick or after.name, inline=False)
                embed.add_field(name="Time", value=f"<t:{int(discord.utils.utcnow().timestamp())}:F> (<t:{int(discord.utils.utcnow().timestamp())}:R>)")
                embed.set_footer(text=f"ID: {before.id}")
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry):
        mod_settings = self._get_moderation_settings(entry.guild.id)
        if not mod_settings or not mod_settings.get("enabled"):
            return

        audit_events = mod_settings.get("events", {}).get("on_audit_log_entry", {})

        # Member Banned
        if entry.action == discord.AuditLogAction.ban and audit_events.get("ban", {}).get("enabled"):
            ban_settings = audit_events.get("ban", {})
            channel_id = ban_settings.get("channel_id") or mod_settings.get("mod_log_channel_id")
            log_channel = await self._get_log_channel(channel_id)
            if log_channel:
                # entry.target may be Object (just ID) if user not in cache
                target_mention = getattr(entry.target, 'mention', f'<@{entry.target.id}>')
                embed = discord.Embed(
                    title="Member Banned",
                    description=f"**Target:** {target_mention}\n**Moderator:** {entry.user.mention}\n**Reason:** {entry.reason or 'No reason provided.'}",
                    color=discord.Color.red()
                )
                embed.add_field(name="Time", value=f"<t:{int(entry.created_at.timestamp())}:F> (<t:{int(entry.created_at.timestamp())}:R>)")
                embed.set_footer(text=f"Target ID: {entry.target.id}")
                await log_channel.send(embed=embed)

        # Member Unbanned
        elif entry.action == discord.AuditLogAction.unban and audit_events.get("unban", {}).get("enabled"):
            unban_settings = audit_events.get("unban", {})
            channel_id = unban_settings.get("channel_id") or mod_settings.get("mod_log_channel_id")
            log_channel = await self._get_log_channel(channel_id)
            if log_channel:
                # entry.target may be Object (just ID) for unbanned users not in cache
                target_mention = getattr(entry.target, 'mention', f'<@{entry.target.id}>')
                embed = discord.Embed(
                    title="Member Unbanned",
                    description=f"**Target:** {target_mention}\n**Moderator:** {entry.user.mention}\n**Reason:** {entry.reason or 'No reason provided.'}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Time", value=f"<t:{int(entry.created_at.timestamp())}:F> (<t:{int(entry.created_at.timestamp())}:R>)")
                embed.set_footer(text=f"Target ID: {entry.target.id}")
                await log_channel.send(embed=embed)

        # Member Kicked
        elif entry.action == discord.AuditLogAction.kick and audit_events.get("kick", {}).get("enabled"):
            kick_settings = audit_events.get("kick", {})
            channel_id = kick_settings.get("channel_id") or mod_settings.get("mod_log_channel_id")
            log_channel = await self._get_log_channel(channel_id)
            if log_channel:
                target_mention = getattr(entry.target, 'mention', f'<@{entry.target.id}>')
                embed = discord.Embed(
                    title="Member Kicked",
                    description=f"**Target:** {target_mention}\n**Moderator:** {entry.user.mention}\n**Reason:** {entry.reason or 'No reason provided.'}",
                    color=discord.Color.red()
                )
                embed.add_field(name="Time", value=f"<t:{int(entry.created_at.timestamp())}:F> (<t:{int(entry.created_at.timestamp())}:R>)")
                embed.set_footer(text=f"Target ID: {entry.target.id}")
                await log_channel.send(embed=embed)

        # Member Muted (Timeout)
        elif entry.action == discord.AuditLogAction.member_update and entry.after.timed_out_until and audit_events.get("mute", {}).get("enabled"):
            mute_settings = audit_events.get("mute", {})
            channel_id = mute_settings.get("channel_id") or mod_settings.get("mod_log_channel_id")
            log_channel = await self._get_log_channel(channel_id)
            if log_channel:
                target_mention = getattr(entry.target, 'mention', f'<@{entry.target.id}>')
                embed = discord.Embed(
                    title="Member Muted (Timeout)",
                    description=f"**Target:** {target_mention}\n**Moderator:** {entry.user.mention}\n**Reason:** {entry.reason or 'No reason provided.'}\n**Until:** <t:{int(entry.after.timed_out_until.timestamp())}:R>",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Time", value=f"<t:{int(entry.created_at.timestamp())}:F> (<t:{int(entry.created_at.timestamp())}:R>)")
                embed.set_footer(text=f"Target ID: {entry.target.id}")
                await log_channel.send(embed=embed)

        # Member Unmuted (Timeout Removed)
        elif entry.action == discord.AuditLogAction.member_update and entry.before.timed_out_until and not entry.after.timed_out_until and audit_events.get("mute", {}).get("enabled"):
            mute_settings = audit_events.get("mute", {})
            channel_id = mute_settings.get("channel_id") or mod_settings.get("mod_log_channel_id")
            log_channel = await self._get_log_channel(channel_id)
            if log_channel:
                target_mention = getattr(entry.target, 'mention', f'<@{entry.target.id}>')
                embed = discord.Embed(
                    title="Member Unmuted (Timeout Removed)",
                    description=f"**Target:** {target_mention}\n**Moderator:** {entry.user.mention}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Time", value=f"<t:{int(entry.created_at.timestamp())}:F> (<t:{int(entry.created_at.timestamp())}:R>)")
                embed.set_footer(text=f"Target ID: {entry.target.id}")
                await log_channel.send(embed=embed)

        # Role Changes
        elif entry.action == discord.AuditLogAction.member_role_update and audit_events.get("role_change", {}).get("enabled"):
            role_change_settings = audit_events.get("role_change", {})
            channel_id = role_change_settings.get("channel_id") or mod_settings.get("mod_log_channel_id")
            log_channel = await self._get_log_channel(channel_id)

            if log_channel:
                added_roles = [r for r in entry.after.roles if r not in entry.before.roles]
                removed_roles = [r for r in entry.before.roles if r not in entry.after.roles]

                if not added_roles and not removed_roles:
                    return

                target_mention = getattr(entry.target, 'mention', f'<@{entry.target.id}>')
                embed = discord.Embed(
                    title="Member Roles Updated",
                    description=f"**Member:** {target_mention}\n**Moderator:** {entry.user.mention}",
                    color=discord.Color.blue()
                )
                if added_roles:
                    embed.add_field(name="Added Roles", value=", ".join([r.mention for r in added_roles]), inline=False)
                if removed_roles:
                    embed.add_field(name="Removed Roles", value=", ".join([r.mention for r in removed_roles]), inline=False)

                embed.add_field(name="Time", value=f"<t:{int(entry.created_at.timestamp())}:F> (<t:{int(entry.created_at.timestamp())}:R>)")
                embed.set_footer(text=f"ID: {entry.target.id}")
                await log_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ModerationLog(bot))
