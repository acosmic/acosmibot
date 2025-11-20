import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildUserDao import GuildUserDao
from Dao.GuildDao import GuildDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class Polymorph(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="polymorph",
                          description="Change your target's display name for 10,000 Credits... please be nice")
    async def polymorph_command(self, interaction: discord.Interaction, target: discord.Member, rename: str):

        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        # Validate nickname length (Discord limit is 32 characters)
        if len(rename) > 32:
            await interaction.response.send_message("Nickname cannot be longer than 32 characters.", ephemeral=True)
            return



        # Check if target is the server owner
        if target.id == interaction.guild.owner_id:
            await interaction.response.send_message("You cannot polymorph the server owner! 👑", ephemeral=True)
            return

        # # Check if target has higher permissions
        # if target.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        #     await interaction.response.send_message("You cannot polymorph someone with equal or higher permissions!",
        #                                             ephemeral=True)
        #     return

        guild_user_dao = GuildUserDao()
        guild_dao = GuildDao()
        cost = 10000

        # Check if user is trying to rename themselves
        if target.id == interaction.user.id:
            cost = 1000

        # Get guild user (currency is guild-specific)
        user = guild_user_dao.get_or_create_guild_user_from_discord(interaction.user, interaction.guild.id)

        if not user:
            await interaction.response.send_message("Failed to get your user data.", ephemeral=True)
            return

        target_original_name = target.display_name  # Get current display name

        if user.currency >= cost:
            try:
                # Store original name for the message
                await target.edit(nick=rename, reason=f"Polymorphed by {interaction.user.name}")

                # Deduct cost from user's guild currency
                user.currency -= cost
                guild_user_dao.update_guild_user(user)

                # Add credits to guild vault (optional - you can adjust this percentage)
                vault_gain = int(cost * 0.1)  # 10% goes to vault
                guild_dao.add_vault_currency(interaction.guild.id, vault_gain)

                embed=discord.Embed(
                    title=f"Polymorph :sheep:",
                    color=target.color,
                    description=f"### {target.mention} is your new nickname.\n\n"
                                f"-# Polymorphed by {interaction.user.name}\n\n"
                )

                embed.set_author(
                    name=f"{target_original_name} ",
                    icon_url=target.avatar.url,
                )
                embed.set_footer(text="/polymorph [@target] - costs 10,000 Credits")

                await interaction.response.send_message(embed=embed, ephemeral=False)

                # await interaction.response.send_message(
                #     f"# 🐑 {interaction.user.name} polymorphed **{target_original_name}** into {target.mention} for {cost:,.0f} Credits! 🐑\n"
                #     f"*{vault_gain:,.0f} Credits added to guild bank.*"
                # )
                logger.info(f'{interaction.user.name} used /polymorph on {target.name} in {interaction.guild.name}')

            except discord.Forbidden:
                await interaction.response.send_message(
                    "I don't have permission to change that user's nickname. They might have higher permissions than me!",
                    ephemeral=True
                )
                logger.warning(f'{interaction.user.name} tried to polymorph {target.name} but bot lacks permissions')

            except discord.HTTPException as e:
                await interaction.response.send_message(
                    f"Failed to change nickname: {str(e)}",
                    ephemeral=True
                )
                logger.error(f'{interaction.user.name} tried to polymorph {target.name} - HTTPException: {e}')

            except Exception as e:
                await interaction.response.send_message(
                    "An unexpected error occurred while changing the nickname.",
                    ephemeral=True
                )
                logger.error(f'{interaction.user.name} tried to polymorph {target.name} - {e}')

        else:
            needed = cost - user.currency
            await interaction.response.send_message(
                f"You need {needed:,.0f} more credits to polymorph someone! "
                f"(You have {user.currency:,.0f}, need {cost:,.0f}) "
                f"<:PepePathetic:1200268253021360128>"
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Polymorph(bot))