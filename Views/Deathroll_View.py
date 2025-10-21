import discord
import logging
import random
import uuid
from Dao.GuildUserDao import GuildUserDao
from Dao.GamesDao import GamesDao


class Deathroll_View(discord.ui.View):
    """Combined view for both matchmaking and gameplay phases of Deathroll"""

    def __init__(self, timeout=120, is_matchmaking=True):
        super().__init__(timeout=timeout)
        self.is_matchmaking = is_matchmaking
        self.guild_id = None
        self.game_id = str(uuid.uuid4())  # Unique identifier for this game instance

        # Matchmaking phase attributes
        self.initiator = None
        self.target = None
        self.bet = 0
        self.match_started = False

        # Game phase attributes
        self.current_player = None
        self.current_roll = 0
        self.game_complete = False  # Using game_complete instead of is_finished
        self.message = None
        self.message2 = None  # Challenge notification message
        self.message_start = None  # Game start message

    async def send(self, interaction: discord.Interaction):
        """Send the initial matchmaking message"""
        embed = self.create_matchmaking_embed()

        # Add buttons manually to avoid conflicts
        accept_button = discord.ui.Button(
            label="Accept",
            style=discord.ButtonStyle.green,
            custom_id=f"accept_{self.game_id}",
            emoji="✅"
        )
        decline_button = discord.ui.Button(
            label="Decline",
            style=discord.ButtonStyle.red,
            custom_id=f"decline_{self.game_id}",
            emoji="❌"
        )

        accept_button.callback = self.accept_callback
        decline_button.callback = self.decline_callback

        self.add_item(accept_button)
        self.add_item(decline_button)

        await interaction.response.send_message(view=self, embed=embed)
        self.message = await interaction.original_response()

        # Send challenge notification
        channel = self.message.channel
        self.message2 = await channel.send(
            f"{self.target.mention}, {self.initiator.display_name} has challenged you to a game of Deathroll! Do you accept?")

    async def accept_callback(self, interaction: discord.Interaction):
        """Handle accept button click"""
        if interaction.user.id == self.initiator.id:
            await interaction.response.send_message("You cannot accept your own challenge!", ephemeral=True)
            return

        if interaction.user.id != self.target.id:
            await interaction.response.send_message("This challenge is not for you!", ephemeral=True)
            return

        # Verify target still has enough credits
        guild_user_dao = GuildUserDao()
        target_user = guild_user_dao.get_guild_user(self.target.id, self.guild_id)

        if not target_user or target_user.currency < self.bet:
            await interaction.response.send_message("You no longer have enough credits for this bet!", ephemeral=True)
            return

        await self.transition_to_game_phase(interaction)

    async def decline_callback(self, interaction: discord.Interaction):
        """Handle decline button click"""
        if interaction.user.id == self.initiator.id:
            await interaction.response.send_message("You cannot decline your own challenge!", ephemeral=True)
            return

        if interaction.user.id != self.target.id:
            await interaction.response.send_message("This challenge is not for you!", ephemeral=True)
            return

        await interaction.response.edit_message(
            content=f"{self.target.display_name} has declined {self.initiator.display_name}'s match. <:FeelsBadMan:1199734765230768139>",
            view=None,
            embed=None
        )

        if self.message2:
            await self.message2.delete()

    async def roll_callback(self, interaction: discord.Interaction):
        """Handle dice roll"""
        if interaction.user.id != self.current_player.id:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        await interaction.response.defer()

        # Roll the dice
        roll = random.randint(1, self.current_roll)
        self.current_roll = roll

        if roll == 1:
            # Game over - current player loses
            self.game_complete = True
            winner = self.target if self.current_player == self.initiator else self.initiator
            loser = self.current_player

            await self.end_game(winner, loser)
        else:
            # Switch players and continue
            self.current_player = self.target if self.current_player == self.initiator else self.initiator
            await self.update_game_message()

    async def announce_game_start(self):
        """Announce that the game has started"""
        self.match_started = True
        if self.message2:
            await self.message2.delete()
        self.message_start = await self.message.channel.send(
            f"{self.target.mention} has accepted {self.initiator.mention}'s match. The match has started! <:Smirk:1200297264502034533>")

    async def announce_winner(self, winner, loser):
        """Announce the match winner"""
        await self.message.channel.send(
            f"{loser.mention} rolled a 1 and lost {self.bet:,.0f} Credits to {winner.mention}! 💀")

    async def on_timeout(self):
        """Handle timeout for both phases"""
        if self.is_matchmaking and not self.match_started:
            # Disable all buttons
            for child in self.children:
                child.disabled = True

            if self.message2:
                await self.message2.delete()
            timeout_message = "The Deathroll match has timed out because no one accepted. <:UglyCry:1200263947274698892>"
            await self.message.edit(content=timeout_message, view=None, embed=None)

        elif not self.is_matchmaking and not self.game_complete:
            # Game phase timeout
            for child in self.children:
                child.disabled = True
            timeout_message = "The Deathroll match has timed out."
            await self.message.edit(content=timeout_message, embed=None)
            if self.message_start:
                await self.message_start.delete()

    def create_matchmaking_embed(self):
        """Create embed for matchmaking phase"""
        embed = discord.Embed(
            title=f"💀 Deathroll for {self.bet:,.0f} Credits!? 💀 \n {self.initiator.display_name} has challenged {self.target.display_name}",
            description="Two players roll a dice and the first player to roll a 1 loses!",
            color=discord.Color.dark_theme()
        )

        deathroll_image = "https://cdn.discordapp.com/attachments/1207159417980588052/1283617949806100581/ac_deathroll-halloween.png?ex=66fcb25f&is=66fb60df&hm=532af5e01ea12f64d0f2c12eb0d593c9961a8bdd4da2209680fbe14753f71e04&"
        embed.set_image(url=deathroll_image)
        return embed

    def create_game_embed(self):
        """Create embed for game phase"""
        embed = discord.Embed(
            title=f"💀 Deathroll - {self.bet:,.0f} Credits 💀\n{self.initiator.display_name} vs {self.target.display_name}",
            description=f"# {self.current_player.display_name}'s Turn \n\n # Roll: {self.current_roll}",
            color=self.current_player.color if hasattr(self.current_player, 'color') else discord.Color.red()
        )
        return embed

    def create_end_game_embed(self, winner, loser):
        """Create embed for game end"""
        embed = discord.Embed(
            title=f"💀 Deathroll - {self.bet:,.0f} Credits 💀\n{self.initiator.display_name} vs {self.target.display_name}",
            description=f"# Game Over! \n# {loser.display_name} rolled a 1 and lost {self.bet:,.0f} credits!",
            color=loser.color if hasattr(loser, 'color') else discord.Color.red()
        )

        embed.add_field(name=f"{winner.display_name}:", value="🏆 WINNER 🏆", inline=True)
        embed.add_field(name=f"{loser.display_name}:", value="💀 BROKIE 💀", inline=True)

        return embed

    async def transition_to_game_phase(self, interaction):
        """Transition from matchmaking to game phase"""
        # Set up game
        self.is_matchmaking = False
        self.current_player = self.initiator
        self.current_roll = self.bet

        # Clear existing buttons
        self.clear_items()

        # Add roll button
        roll_button = discord.ui.Button(
            label=f"{self.current_player.display_name}: Roll!",
            style=discord.ButtonStyle.danger,
            custom_id=f"roll_{self.game_id}",
            emoji="🎲"
        )
        roll_button.callback = self.roll_callback
        self.add_item(roll_button)

        # Update message with game embed
        embed = self.create_game_embed()
        await interaction.response.edit_message(embed=embed, view=self)

        await self.announce_game_start()

    async def update_game_message(self):
        """Update message during game phase"""
        # Clear existing buttons
        self.clear_items()

        # Add new roll button with updated player
        roll_button = discord.ui.Button(
            label=f"{self.current_player.display_name}: Roll!",
            style=discord.ButtonStyle.danger,
            custom_id=f"roll_{self.game_id}",
            emoji="🎲"
        )
        roll_button.callback = self.roll_callback
        self.add_item(roll_button)

        embed = self.create_game_embed()
        await self.message.edit(embed=embed, view=self)

    async def end_game(self, winner, loser):
        """End the game and handle payouts"""
        # Disable all buttons
        for child in self.children:
            child.disabled = True

        # Handle currency transfer
        await self.winner_payout(winner, loser)

        # Update embed
        embed = self.create_end_game_embed(winner, loser)
        await self.message.edit(embed=embed, view=self)

        # Announce winner
        await self.announce_winner(winner, loser)

        # Clean up
        if self.message_start:
            await self.message_start.delete()

        logging.info(
            f"Deathroll game {self.game_id} completed in guild {self.guild_id}. Winner: {winner.display_name}, Loser: {loser.display_name}")

    async def winner_payout(self, winner, loser):
        """Handle winner payout"""
        guild_user_dao = GuildUserDao()

        winner_user = guild_user_dao.get_guild_user(winner.id, self.guild_id)
        loser_user = guild_user_dao.get_guild_user(loser.id, self.guild_id)

        if winner_user and loser_user:
            guild_user_dao.update_currency_with_global_sync(winner.id, self.guild_id, self.bet)
            guild_user_dao.update_currency_with_global_sync(loser.id, self.guild_id, -self.bet)
            winner_user.currency += self.bet  # Update local objects
            loser_user.currency -= self.bet

            # Record games in database
            games_dao = GamesDao()

            # Log for winner
            games_dao.add_game(
                user_id=winner.id,
                guild_id=self.guild_id,
                game_type="deathroll",
                amount_bet=self.bet,
                amount_won=self.bet,
                amount_lost=0,
                result="win",
                game_data={
                    "opponent_id": loser.id,
                    "opponent_name": loser.display_name,
                    "final_roll": self.current_roll
                }
            )

            # Log for loser
            games_dao.add_game(
                user_id=loser.id,
                guild_id=self.guild_id,
                game_type="deathroll",
                amount_bet=self.bet,
                amount_won=0,
                amount_lost=self.bet,
                result="lose",
                game_data={
                    "opponent_id": winner.id,
                    "opponent_name": winner.display_name,
                    "final_roll": self.current_roll
                }
            )