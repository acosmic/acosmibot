#! /usr/bin/python3.10
import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Dao.GuildUserDao import GuildUserDao
from Dao.BankTransactionDao import BankTransactionDao
from Dao.GuildDao import GuildDao
from Dao.GlobalSettingsDao import GlobalSettingsDao
from logger import AppLogger
import typing
from datetime import datetime

logger = AppLogger(__name__).get_logger()


class Bank(commands.Cog):
    """
    Bank system cog for cross-server currency management.
    Allows users to deposit/withdraw currency between guild wallets and global bank.
    """

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    def _get_bank_config(self, guild_id: int) -> dict:
        """Get bank configuration from global settings + guild overrides."""
        import json

        # Fallback defaults (if GlobalSettings table is empty)
        fallback_config = {
            'enabled': True,
            'deposit_fee_percent': 2.0,
            'withdraw_fee_percent': 2.0,
            'daily_transfer_limit': 500000,
            'min_deposit': 100,
            'min_withdraw': 100,
            'interest_enabled': False,
            'interest_rate': 0.02,  # 2%
            'interest_interval': 'daily'
        }

        try:
            with GlobalSettingsDao() as global_settings_dao, GuildDao() as guild_dao:
                # Fetch economy settings from GlobalSettings table
                economy_settings = {
                    'economy.deposit_fee_percent': 'deposit_fee_percent',
                    'economy.withdraw_fee_percent': 'withdraw_fee_percent',
                    'economy.min_transaction': 'min_deposit',  # Use same min for both
                    'economy.max_transaction': 'max_transaction',
                    'economy.daily_transfer_limit': 'daily_transfer_limit',
                    'economy.interest_enabled': 'interest_enabled',
                    'economy.interest_rate_percent': 'interest_rate',
                    'economy.interest_interval': 'interest_interval'
                }

                # Build config from global settings
                config = {}
                for setting_key, field_name in economy_settings.items():
                    value = global_settings_dao.get_setting_value(setting_key)
                    if value is not None:
                        # Convert string booleans to actual booleans
                        if value in ('true', 'false'):
                            value = value == 'true'
                        # Convert numeric strings to float/int
                        elif isinstance(value, str):
                            try:
                                # Try float first
                                float_val = float(value)
                                # If it's a whole number, make it int
                                value = int(float_val) if float_val.is_integer() else float_val
                            except ValueError:
                                # Keep as string (like "weekly", "daily")
                                pass

                        # Handle special mappings
                        if field_name == 'min_deposit':
                            config['min_deposit'] = value
                            config['min_withdraw'] = value  # Use same minimum for both
                        elif field_name == 'interest_rate':
                            # Convert percentage to decimal (0.5% -> 0.005)
                            config['interest_rate'] = value / 100 if isinstance(value, (int, float)) else 0.005
                        else:
                            config[field_name] = value
                    else:
                        # Use fallback if setting not found
                        if field_name == 'min_deposit':
                            config['min_deposit'] = fallback_config['min_deposit']
                            config['min_withdraw'] = fallback_config['min_withdraw']
                        elif field_name == 'interest_rate':
                            config['interest_rate'] = fallback_config['interest_rate']
                        elif field_name in fallback_config:
                            config[field_name] = fallback_config[field_name]

                # Check if guild has any override for 'enabled' status
                guild = guild_dao.get_guild(guild_id)

            if guild and guild.settings:
                # Parse settings JSON
                settings = json.loads(guild.settings) if isinstance(guild.settings, str) else guild.settings

                # Check if guild has economy/bank enabled override
                economy_settings_guild = settings.get("economy", {})
                if 'enabled' in economy_settings_guild:
                    config['enabled'] = economy_settings_guild['enabled']
                else:
                    # Default to enabled if not specified
                    config['enabled'] = True
            else:
                config['enabled'] = True

            return config

        except Exception as e:
            logger.error(f"Error getting bank config: {e}")
            return fallback_config

    def _calculate_fee(self, amount: int, fee_percent: float) -> int:
        """Calculate fee based on amount and percentage."""
        return int(amount * fee_percent / 100)

    @app_commands.command(name="deposit", description="Deposit credits from your server wallet to your global bank")
    @app_commands.describe(amount="Amount to deposit (or 'all' to deposit everything)")
    async def deposit(self, interaction: discord.Interaction, amount: str):
        """Deposit currency from guild wallet to global bank."""

        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        try:
            # Get bank config
            config = self._get_bank_config(interaction.guild.id)

            if not config['enabled']:
                await interaction.followup.send("❌ The bank system is not enabled in this server.", ephemeral=True)
                return

            # Get user data using context managers
            with UserDao() as user_dao, GuildUserDao() as guild_user_dao:
                user = user_dao.get_user(interaction.user.id)
                guild_user = guild_user_dao.get_guild_user(interaction.user.id, interaction.guild.id)

                if not user or not guild_user:
                    await interaction.followup.send("❌ User data not found.", ephemeral=True)
                    return

                # Parse amount
                if amount.lower() == 'all':
                    deposit_amount = guild_user.currency
                else:
                    try:
                        deposit_amount = int(amount.replace(',', ''))
                    except ValueError:
                        await interaction.followup.send("❌ Invalid amount. Please enter a number or 'all'.", ephemeral=True)
                        return

                # Validate amount
                if deposit_amount <= 0:
                    await interaction.followup.send("❌ Amount must be positive.", ephemeral=True)
                    return

                if deposit_amount < config['min_deposit']:
                    await interaction.followup.send(
                        f"❌ Minimum deposit is {config['min_deposit']:,} credits.",
                        ephemeral=True
                    )
                    return

                if guild_user.currency < deposit_amount:
                    await interaction.followup.send(
                        f"❌ Insufficient funds. You have {guild_user.currency:,} credits in this server.",
                        ephemeral=True
                    )
                    return

                # Check daily limit
                if config['daily_transfer_limit'] > 0:
                    # Reset daily limit if needed
                    user_dao.reset_daily_transfer_if_needed(interaction.user.id)

                    # Get current user to check limit
                    user = user_dao.get_user(interaction.user.id)
                    new_daily_total = user.daily_transfer_amount + deposit_amount

                    if new_daily_total > config['daily_transfer_limit']:
                        remaining = config['daily_transfer_limit'] - user.daily_transfer_amount
                        await interaction.followup.send(
                            f"❌ Daily transfer limit exceeded.\n"
                            f"Limit: {config['daily_transfer_limit']:,} credits/day\n"
                            f"Used today: {user.daily_transfer_amount:,}\n"
                            f"Remaining: {remaining:,}",
                            ephemeral=True
                        )
                        return

                # Calculate fee
                fee = self._calculate_fee(deposit_amount, config['deposit_fee_percent'])
                net_deposit = deposit_amount - fee

                # Execute transfer
                result = guild_user_dao.transfer_to_bank(
                    user_id=interaction.user.id,
                    guild_id=interaction.guild.id,
                    amount=deposit_amount,
                    fee=fee
                )

                if not result['success']:
                    await interaction.followup.send(f"❌ {result['message']}", ephemeral=True)
                    return

                # Update daily transfer tracking
                if config['daily_transfer_limit'] > 0:
                    user_dao.increment_daily_transfer(interaction.user.id, deposit_amount)

                # Create success embed
                embed = discord.Embed(
                    title="💰 Bank Deposit Successful",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Amount Deposited", value=f"{deposit_amount:,} credits", inline=True)
                if fee > 0:
                    embed.add_field(name="Fee", value=f"{fee:,} credits ({config['deposit_fee_percent']}%)", inline=True)
                    embed.add_field(name="Net Deposit", value=f"{net_deposit:,} credits", inline=True)
                    embed.add_field(name="Previous Balance", value=f"{result['balance_before']:,} credits", inline=True)
                    embed.add_field(name="New Balance", value=f"{result['balance_after']:,} credits", inline=True)

                embed.set_footer(text=f"Use /bank to view your balance • Server: {interaction.guild.name}")

                await interaction.followup.send(embed=embed, ephemeral=False)
                logger.info(f"User {interaction.user.id} deposited {deposit_amount:,} credits to bank")

        except Exception as e:
            logger.error(f"Error in deposit command: {e}")
            await interaction.followup.send("❌ An error occurred while processing your deposit.", ephemeral=True)

    @app_commands.command(name="withdraw", description="Withdraw credits from your global bank to your server wallet")
    @app_commands.describe(amount="Amount to withdraw (or 'all' to withdraw everything)")
    async def withdraw(self, interaction: discord.Interaction, amount: str):
        """Withdraw currency from global bank to guild wallet."""

        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        try:
            # Get bank config
            config = self._get_bank_config(interaction.guild.id)

            if not config['enabled']:
                await interaction.followup.send("❌ The bank system is not enabled in this server.", ephemeral=True)
                return

            # Get user data using context managers
            with UserDao() as user_dao, GuildUserDao() as guild_user_dao:
                user = user_dao.get_user(interaction.user.id)
                guild_user = guild_user_dao.get_guild_user(interaction.user.id, interaction.guild.id)

                if not user or not guild_user:
                    await interaction.followup.send("❌ User data not found.", ephemeral=True)
                    return

                # Parse amount
                if amount.lower() == 'all':
                    # Calculate max we can withdraw (need to account for fee)
                    fee_percent = config['withdraw_fee_percent']
                    if fee_percent > 0:
                        # If fee is X%, then amount + fee = bank_balance
                        # amount * (1 + X/100) = bank_balance
                        # amount = bank_balance / (1 + X/100)
                        withdraw_amount = int(user.bank_balance / (1 + fee_percent / 100))
                    else:
                        withdraw_amount = user.bank_balance
                else:
                    try:
                        withdraw_amount = int(amount.replace(',', ''))
                    except ValueError:
                        await interaction.followup.send("❌ Invalid amount. Please enter a number or 'all'.", ephemeral=True)
                        return

                # Validate amount
                if withdraw_amount <= 0:
                    await interaction.followup.send("❌ Amount must be positive.", ephemeral=True)
                    return

                if withdraw_amount < config['min_withdraw']:
                    await interaction.followup.send(
                        f"❌ Minimum withdrawal is {config['min_withdraw']:,} credits.",
                        ephemeral=True
                    )
                    return

                # Calculate fee
                fee = self._calculate_fee(withdraw_amount, config['withdraw_fee_percent'])
                total_needed = withdraw_amount + fee

                if user.bank_balance < total_needed:
                    await interaction.followup.send(
                        f"❌ Insufficient bank balance.\n"
                        f"Withdrawal amount: {withdraw_amount:,}\n"
                        f"Fee: {fee:,} ({config['withdraw_fee_percent']}%)\n"
                        f"Total needed: {total_needed:,}\n"
                        f"Your balance: {user.bank_balance:,}",
                        ephemeral=True
                    )
                    return

                # Check daily limit
                if config['daily_transfer_limit'] > 0:
                    # Reset daily limit if needed
                    user_dao.reset_daily_transfer_if_needed(interaction.user.id)

                    # Get current user to check limit
                    user = user_dao.get_user(interaction.user.id)
                    new_daily_total = user.daily_transfer_amount + withdraw_amount

                    if new_daily_total > config['daily_transfer_limit']:
                        remaining = config['daily_transfer_limit'] - user.daily_transfer_amount
                        await interaction.followup.send(
                            f"❌ Daily transfer limit exceeded.\n"
                            f"Limit: {config['daily_transfer_limit']:,} credits/day\n"
                            f"Used today: {user.daily_transfer_amount:,}\n"
                            f"Remaining: {remaining:,}",
                            ephemeral=True
                        )
                        return

                # Execute transfer
                result = guild_user_dao.transfer_from_bank(
                    user_id=interaction.user.id,
                    guild_id=interaction.guild.id,
                    amount=withdraw_amount,
                    fee=fee
                )

                if not result['success']:
                    await interaction.followup.send(f"❌ {result['message']}", ephemeral=True)
                    return

                # Update daily transfer tracking
                if config['daily_transfer_limit'] > 0:
                    user_dao.increment_daily_transfer(interaction.user.id, withdraw_amount)

                # Create success embed
                embed = discord.Embed(
                    title="💸 Bank Withdrawal Successful",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Amount Withdrawn", value=f"{withdraw_amount:,} credits", inline=True)
                if fee > 0:
                    embed.add_field(name="Fee", value=f"{fee:,} credits ({config['withdraw_fee_percent']}%)", inline=True)
                    embed.add_field(name="Total Deducted", value=f"{total_needed:,} credits", inline=True)
                embed.add_field(name="Previous Balance", value=f"{result['balance_before']:,} credits", inline=True)
                embed.add_field(name="New Balance", value=f"{result['balance_after']:,} credits", inline=True)

                embed.set_footer(text=f"Use /bank to view your balance • Server: {interaction.guild.name}")

                await interaction.followup.send(embed=embed, ephemeral=False)
                logger.info(f"User {interaction.user.id} withdrew {withdraw_amount:,} credits from bank")

        except Exception as e:
            logger.error(f"Error in withdraw command: {e}")
            await interaction.followup.send("❌ An error occurred while processing your withdrawal.", ephemeral=True)

    @app_commands.command(name="bank", description="View your global bank balance and statistics")
    @app_commands.describe(user="View another user's bank info (optional)")
    async def bank(self, interaction: discord.Interaction, user: typing.Optional[discord.Member] = None):
        """View bank balance and statistics."""

        # Use interaction user if no user specified
        target_user = user or interaction.user

        await interaction.response.defer(ephemeral=False)

        try:
            # Get user data using context managers
            with UserDao() as user_dao, BankTransactionDao() as bank_dao:
                db_user = user_dao.get_user(target_user.id)

                if not db_user:
                    await interaction.followup.send(
                        f"❌ {target_user.display_name} has no bank account yet.",
                        ephemeral=True
                    )
                    return

                # Get transaction stats
                stats = bank_dao.get_transaction_stats(target_user.id)

                # Get bank config if in guild
                config = None
                if interaction.guild:
                    config = self._get_bank_config(interaction.guild.id)

                # Create embed
                embed = discord.Embed(
                    title=f"🏦 Bank Account - {target_user.display_name}",
                    color=discord.Color.gold(),
                    timestamp=datetime.utcnow()
                )

                # Set thumbnail
                if target_user.avatar:
                    embed.set_thumbnail(url=target_user.avatar.url)

                # Bank balance
                embed.add_field(
                    name="💰 Current Balance",
                    value=f"**{db_user.bank_balance:,}** credits",
                    inline=False
                )

                # Transaction statistics
                if stats:
                    total_deposited = stats.get('total_deposits', 0) or 0
                    total_withdrawn = stats.get('total_withdrawals', 0) or 0
                    total_fees = stats.get('total_fees_paid', 0) or 0
                    total_interest = stats.get('total_interest', 0) or 0

                    embed.add_field(name="📥 Total Deposited", value=f"{total_deposited:,} credits", inline=True)
                    embed.add_field(name="📤 Total Withdrawn", value=f"{total_withdrawn:,} credits", inline=True)
                    embed.add_field(name="💸 Total Fees Paid", value=f"{total_fees:,} credits", inline=True)

                    if total_interest > 0:
                        embed.add_field(name="📈 Total Interest Earned", value=f"{total_interest:,} credits", inline=True)

                # Daily limit info (only show for self)
                if target_user.id == interaction.user.id and config and config['daily_transfer_limit'] > 0:
                    # Reset if needed
                    user_dao.reset_daily_transfer_if_needed(target_user.id)
                    # Get fresh data
                    db_user = user_dao.get_user(target_user.id)

                    remaining = config['daily_transfer_limit'] - db_user.daily_transfer_amount
                    embed.add_field(
                        name="📊 Daily Transfer Limit",
                        value=f"Used: {db_user.daily_transfer_amount:,} / {config['daily_transfer_limit']:,}\n"
                              f"Remaining: {remaining:,} credits",
                        inline=False
                    )

                # Show interest info if enabled
                if config and config['interest_enabled']:
                    embed.add_field(
                        name="📈 Interest Rate",
                        value=f"{config['interest_rate'] * 100:.2f}% {config['interest_interval']}",
                        inline=True
                    )

                # Show fees if any
                if config:
                    fee_info = []
                    if config['deposit_fee_percent'] > 0:
                        fee_info.append(f"Deposit: {config['deposit_fee_percent']}%")
                    if config['withdraw_fee_percent'] > 0:
                        fee_info.append(f"Withdraw: {config['withdraw_fee_percent']}%")

                    if fee_info:
                        embed.add_field(
                            name="💳 Transaction Fees",
                            value=" • ".join(fee_info),
                            inline=True
                        )

                embed.set_footer(text="Use /deposit or /withdraw to manage your balance • /bank-history for transactions")

                await interaction.followup.send(embed=embed, ephemeral=False)

        except Exception as e:
            logger.error(f"Error in bank command: {e}")
            await interaction.followup.send("❌ An error occurred while fetching bank information.", ephemeral=True)

    @app_commands.command(name="bank-history", description="View your recent bank transactions")
    @app_commands.describe(limit="Number of transactions to show (default: 10, max: 25)")
    async def bank_history(self, interaction: discord.Interaction, limit: typing.Optional[int] = 10):
        """View transaction history."""

        await interaction.response.defer(ephemeral=True)

        try:
            # Validate limit
            if limit < 1 or limit > 25:
                await interaction.followup.send("❌ Limit must be between 1 and 25.", ephemeral=True)
                return

            # Get transactions using context manager
            with BankTransactionDao() as bank_dao:
                transactions = bank_dao.get_user_transactions(interaction.user.id, limit)

                if not transactions:
                    await interaction.followup.send(
                        "📋 You have no bank transactions yet.\nUse `/deposit` to make your first deposit!",
                        ephemeral=True
                    )
                    return

            # Create embed
            embed = discord.Embed(
                title=f"🏦 Transaction History - {interaction.user.display_name}",
                description=f"Showing last {len(transactions)} transaction(s)",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            # Add transactions
            for txn in transactions:
                # Format transaction type
                if txn.transaction_type == 'deposit':
                    icon = "📥"
                    type_str = "Deposit"
                elif txn.transaction_type == 'withdraw':
                    icon = "📤"
                    type_str = "Withdrawal"
                else:  # interest
                    icon = "📈"
                    type_str = "Interest"

                # Get guild name
                guild_name = "Unknown Server"
                try:
                    guild = self.bot.get_guild(txn.guild_id)
                    if guild:
                        guild_name = guild.name
                except Exception:
                    pass

                # Format transaction details
                details = []
                details.append(f"**Amount:** {txn.amount:,} credits")
                if txn.fee > 0:
                    details.append(f"**Fee:** {txn.fee:,} credits")
                details.append(f"**Balance:** {txn.balance_before:,} → {txn.balance_after:,}")
                details.append(f"**Server:** {guild_name}")

                # Format timestamp
                try:
                    if isinstance(txn.timestamp, str):
                        txn_time = datetime.strptime(txn.timestamp, "%Y-%m-%d %H:%M:%S")
                    else:
                        txn_time = txn.timestamp
                    time_str = txn_time.strftime("%b %d, %Y at %I:%M %p")
                except Exception:
                    time_str = str(txn.timestamp)

                embed.add_field(
                    name=f"{icon} {type_str} - {time_str}",
                    value="\n".join(details),
                    inline=False
                )

            embed.set_footer(text=f"Transaction ID range: {transactions[-1].id} - {transactions[0].id}")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in bank-history command: {e}")
            await interaction.followup.send("❌ An error occurred while fetching transaction history.", ephemeral=True)


async def setup(bot: commands.Bot):
    """Required setup function for cog loading."""
    await bot.add_cog(Bank(bot))
