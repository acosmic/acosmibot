#! /usr/bin/python3.10
import discord
import logging
import uuid
from Dao.GuildUserDao import GuildUserDao
from Dao.GamesDao import GamesDao
from Dao.GuildDao import GuildDao
from Entities.BlackjackGame import BlackjackGame

logger = logging.getLogger(__name__)


class Blackjack_View(discord.ui.View):
    """View for managing blackjack game state and user interactions"""

    def __init__(self, player: discord.Member, bet: int, guild_id: int, config: dict, timeout=120):
        super().__init__(timeout=timeout)
        self.player = player
        self.bet = bet
        self.guild_id = guild_id
        self.config = config
        self.game_id = str(uuid.uuid4())  # Unique identifier for concurrent games

        # Initialize game logic
        use_persistent_shoe = config.get("persistent_shoe", False)
        self.game = BlackjackGame(
            num_decks=config.get("num_decks", 6),
            guild_id=guild_id if use_persistent_shoe else None,
            use_persistent_shoe=use_persistent_shoe
        )
        self.game.deal_initial_hands()

        # Message reference
        self.message: discord.Message = None

        # Game state
        self.insurance_phase = False
        self.main_game_started = False

        # Check for immediate dealer blackjack (after insurance)
        self.check_initial_state()

    def check_initial_state(self):
        """Check if insurance is needed or game ends immediately"""
        player_blackjack = self.game.is_blackjack(self.game.player_hand)
        dealer_blackjack = self.game.is_blackjack(self.game.dealer_hand)
        dealer_shows_ace = self.game.can_take_insurance()

        # If dealer shows Ace and player doesn't have blackjack, offer insurance
        if dealer_shows_ace and not player_blackjack:
            self.insurance_phase = True
        elif player_blackjack or dealer_blackjack:
            self.game.game_over = True
            self.main_game_started = True

    async def send(self, interaction: discord.Interaction):
        """Send the initial game message"""
        embed = self.create_game_embed()

        # Insurance phase
        if self.insurance_phase:
            self.add_insurance_buttons()
            await interaction.response.send_message(embed=embed, view=self)
            self.message = await interaction.original_response()
        # Game already over (blackjacks)
        elif self.game.game_over:
            await interaction.response.send_message(embed=embed)
            self.message = await interaction.original_response()
            await self.end_game()
        # Normal game start
        else:
            self.add_game_buttons()
            await interaction.response.send_message(embed=embed, view=self)
            self.message = await interaction.original_response()

    def add_insurance_buttons(self):
        """Add insurance decision buttons"""
        self.clear_items()

        yes_button = discord.ui.Button(
            label=f"Yes ({self.bet // 2:,} credits)",
            style=discord.ButtonStyle.primary,
            custom_id=f"insurance_yes_{self.game_id}",
            emoji="🛡️"
        )
        yes_button.callback = self.insurance_yes_callback
        self.add_item(yes_button)

        no_button = discord.ui.Button(
            label="No, thanks",
            style=discord.ButtonStyle.secondary,
            custom_id=f"insurance_no_{self.game_id}",
            emoji="❌"
        )
        no_button.callback = self.insurance_no_callback
        self.add_item(no_button)

    def add_game_buttons(self):
        """Add interactive buttons for game actions"""
        self.clear_items()

        current_hand = self.game.get_current_hand()
        is_first_action = len(current_hand) == 2 and not self.main_game_started

        # Hit button
        hit_button = discord.ui.Button(
            label="Hit",
            style=discord.ButtonStyle.primary,
            custom_id=f"hit_{self.game_id}",
            emoji="🎴"
        )
        hit_button.callback = self.hit_callback
        self.add_item(hit_button)

        # Stand button
        stand_button = discord.ui.Button(
            label="Stand",
            style=discord.ButtonStyle.success,
            custom_id=f"stand_{self.game_id}",
            emoji="✋"
        )
        stand_button.callback = self.stand_callback
        self.add_item(stand_button)

        # Double Down button (only on first action with enough funds)
        if len(current_hand) == 2:
            guild_user_dao = GuildUserDao()
            player_user = guild_user_dao.get_guild_user(self.player.id, self.guild_id)

            if player_user and player_user.currency >= self.bet:
                double_button = discord.ui.Button(
                    label="Double Down",
                    style=discord.ButtonStyle.danger,
                    custom_id=f"double_{self.game_id}",
                    emoji="💰"
                )
                double_button.callback = self.double_callback
                self.add_item(double_button)

        # Split button (only on first action, if allowed, and enough funds)
        if (is_first_action and
            self.game.can_split() and
            self.config.get("allow_split", True) and
            not self.game.is_split):

            guild_user_dao = GuildUserDao()
            player_user = guild_user_dao.get_guild_user(self.player.id, self.guild_id)

            if player_user and player_user.currency >= self.bet:
                split_button = discord.ui.Button(
                    label="Split",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"split_{self.game_id}",
                    emoji="✂️"
                )
                split_button.callback = self.split_callback
                self.add_item(split_button)

        # Surrender button (only on first action, if allowed)
        if (is_first_action and
            self.game.can_surrender() and
            self.config.get("allow_surrender", True)):

            surrender_button = discord.ui.Button(
                label="Surrender",
                style=discord.ButtonStyle.secondary,
                custom_id=f"surrender_{self.game_id}",
                emoji="🏳️"
            )
            surrender_button.callback = self.surrender_callback
            self.add_item(surrender_button)

    async def insurance_yes_callback(self, interaction: discord.Interaction):
        """Handle insurance acceptance"""
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return

        # Deduct insurance bet
        guild_user_dao = GuildUserDao()
        player_user = guild_user_dao.get_guild_user(self.player.id, self.guild_id)
        insurance_cost = self.bet // 2

        if not player_user or player_user.currency < insurance_cost:
            await interaction.response.send_message("You don't have enough credits for insurance!", ephemeral=True)
            return

        guild_user_dao.update_currency_with_global_sync(self.player.id, self.guild_id, -insurance_cost)
        player_user.currency -= insurance_cost  # Update local object

        self.game.take_insurance(self.bet)
        self.insurance_phase = False
        self.main_game_started = True

        await interaction.response.defer()

        # Check if dealer has blackjack
        if self.game.is_blackjack(self.game.dealer_hand):
            self.game.game_over = True
            await self.end_game()
        else:
            # Continue with normal game
            embed = self.create_game_embed()
            self.add_game_buttons()
            await self.message.edit(embed=embed, view=self)

    async def insurance_no_callback(self, interaction: discord.Interaction):
        """Handle insurance decline"""
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return

        self.insurance_phase = False
        self.main_game_started = True

        await interaction.response.defer()

        # Check if dealer has blackjack
        if self.game.is_blackjack(self.game.dealer_hand):
            self.game.game_over = True
            await self.end_game()
        else:
            # Continue with normal game
            embed = self.create_game_embed()
            self.add_game_buttons()
            await self.message.edit(embed=embed, view=self)

    async def hit_callback(self, interaction: discord.Interaction):
        """Handle Hit button press"""
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return

        self.main_game_started = True
        await interaction.response.defer()

        # Player takes a card
        card, value, busted = self.game.player_hit_current()

        if self.game.game_over:
            # Both hands done or player busted
            self.game.dealer_play()
            await self.end_game()
        else:
            # Update the game view
            embed = self.create_game_embed()
            self.add_game_buttons()
            await self.message.edit(embed=embed, view=self)

    async def stand_callback(self, interaction: discord.Interaction):
        """Handle Stand button press"""
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return

        self.main_game_started = True
        await interaction.response.defer()

        # Player stands
        self.game.player_stand_current()

        if self.game.game_over:
            # All hands done, dealer plays
            self.game.dealer_play()
            await self.end_game()
        else:
            # Move to split hand
            embed = self.create_game_embed()
            self.add_game_buttons()
            await self.message.edit(embed=embed, view=self)

    async def double_callback(self, interaction: discord.Interaction):
        """Handle Double Down button press"""
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return

        # Deduct additional bet first
        guild_user_dao = GuildUserDao()
        player_user = guild_user_dao.get_guild_user(self.player.id, self.guild_id)

        if not player_user or player_user.currency < self.bet:
            await interaction.response.send_message("You don't have enough credits to double down!", ephemeral=True)
            return

        # Deduct the additional bet with global sync
        guild_user_dao.update_currency_with_global_sync(self.player.id, self.guild_id, -self.bet)
        player_user.currency -= self.bet  # Update local object

        self.main_game_started = True
        await interaction.response.defer()

        # Double down: deal one card and stand
        card, value, busted = self.game.player_double_down_current()

        if self.game.game_over:
            # All hands done
            self.game.dealer_play()
            await self.end_game()
        else:
            # Move to split hand
            embed = self.create_game_embed()
            self.add_game_buttons()
            await self.message.edit(embed=embed, view=self)

    async def split_callback(self, interaction: discord.Interaction):
        """Handle Split button press"""
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return

        # Deduct additional bet for split hand
        guild_user_dao = GuildUserDao()
        player_user = guild_user_dao.get_guild_user(self.player.id, self.guild_id)

        if not player_user or player_user.currency < self.bet:
            await interaction.response.send_message("You don't have enough credits to split!", ephemeral=True)
            return

        # Deduct the split bet with global sync
        guild_user_dao.update_currency_with_global_sync(self.player.id, self.guild_id, -self.bet)
        player_user.currency -= self.bet  # Update local object

        self.main_game_started = True
        await interaction.response.defer()

        # Perform split
        success = self.game.player_split()

        if not success:
            await interaction.followup.send("Failed to split!", ephemeral=True)
            return

        # Update view
        embed = self.create_game_embed()
        self.add_game_buttons()
        await self.message.edit(embed=embed, view=self)

    async def surrender_callback(self, interaction: discord.Interaction):
        """Handle Surrender button press"""
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return

        self.main_game_started = True
        await interaction.response.defer()

        # Surrender
        self.game.player_surrender()
        await self.end_game()

    def create_game_embed(self) -> discord.Embed:
        """Create embed showing current game state"""
        player_value = self.game.get_hand_value(self.game.player_hand)
        dealer_value = self.game.get_hand_value(self.game.dealer_hand)

        # Title with current bet
        total_bet = self.bet
        if self.game.doubled_down:
            total_bet += self.bet
        if self.game.is_split:
            total_bet += self.bet
            if self.game.split_hand_doubled:
                total_bet += self.bet
        if self.game.has_insurance:
            total_bet += self.game.insurance_bet

        title = f"♠️ Blackjack - {total_bet:,} Credits at Risk ♥️"

        # Insurance phase
        if self.insurance_phase:
            description = "**Dealer shows an Ace!**\n\n"
            description += "Would you like to take **Insurance**?\n"
            description += f"Cost: {self.bet // 2:,} credits\n"
            description += f"Pays 2:1 if dealer has Blackjack\n\n"

            dealer_hand_str = self.game.format_hand(self.game.dealer_hand, hide_first=False)
            description += f"**Dealer's Hand:**\n{dealer_hand_str}\n\n"

            player_hand_str = self.game.format_hand(self.game.player_hand)
            description += f"**{self.player.display_name}'s Hand ({player_value}):**\n{player_hand_str}"

            embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
            return embed

        # Format hands
        if self.game.game_over:
            # Show all dealer cards
            dealer_hand_str = self.game.format_hand(self.game.dealer_hand)
            dealer_display = f"**Dealer's Hand ({dealer_value}):**\n{dealer_hand_str}"
        else:
            # Hide dealer's first card
            dealer_hand_str = self.game.format_hand(self.game.dealer_hand, hide_first=True)
            visible_value = self.game.get_hand_value([self.game.dealer_hand[1]])
            dealer_display = f"**Dealer's Hand (? + {visible_value}):**\n{dealer_hand_str}"

        # Player hands
        if self.game.is_split:
            # Show both hands
            hand1_str = self.game.format_hand(self.game.player_hand)
            hand1_value = self.game.get_hand_value(self.game.player_hand)
            hand1_indicator = " 👈" if self.game.current_hand_index == 0 else ""

            hand2_str = self.game.format_hand(self.game.split_hand)
            hand2_value = self.game.get_hand_value(self.game.split_hand)
            hand2_indicator = " 👈" if self.game.current_hand_index == 1 else ""

            player_display = f"**{self.player.display_name}'s Hand 1 ({hand1_value}):{hand1_indicator}**\n{hand1_str}\n\n"
            player_display += f"**{self.player.display_name}'s Hand 2 ({hand2_value}):{hand2_indicator}**\n{hand2_str}"
        else:
            player_hand_str = self.game.format_hand(self.game.player_hand)
            player_display = f"**{self.player.display_name}'s Hand ({player_value}):**\n{player_hand_str}"

        # Build description
        description = f"{dealer_display}\n\n{player_display}"

        # Insurance info
        if self.game.has_insurance:
            description += f"\n\n🛡️ **Insurance: {self.game.insurance_bet:,} credits**"

        # Add game status messages
        color = discord.Color.dark_theme()
        if self.game.game_over:
            if self.game.surrendered:
                description += "\n\n🏳️ **Surrendered** - Half bet returned"
                color = discord.Color.orange()
            else:
                # Calculate results for display
                total_won, total_lost, details = self.game.calculate_total_payout(self.bet)

                if total_won > total_lost:
                    description += "\n\n🎉 **You win!** 🎉"
                    color = discord.Color.green()
                elif total_won < total_lost:
                    description += "\n\n😢 **Dealer wins.**"
                    color = discord.Color.red()
                else:
                    description += "\n\n🤝 **Push!**"
                    color = discord.Color.blue()

        # Create embed
        embed = discord.Embed(title=title, description=description, color=color)
        return embed

    async def end_game(self):
        """Handle game end: calculate payout, update database, show results"""
        # Disable all buttons
        for child in self.children:
            child.disabled = True

        # Calculate total payout
        total_won, total_lost, details = self.game.calculate_total_payout(self.bet)

        # Update player currency
        guild_user_dao = GuildUserDao()
        player_user = guild_user_dao.get_guild_user(self.player.id, self.guild_id)

        if player_user:
            guild_user_dao.update_currency_with_global_sync(self.player.id, self.guild_id, total_won)
            player_user.currency += total_won  # Update local object

            # Add to vault (10% of losses)
            if total_lost > 0:
                guild_dao = GuildDao()
                guild_dao.add_vault_currency(self.guild_id, int(total_lost * 0.1))

        # Record game in database
        games_dao = GamesDao()

        # Determine overall result
        if self.game.surrendered:
            game_result = "lose"  # Surrender counts as loss
        elif total_won > total_lost:
            game_result = "win"
        elif total_won < total_lost:
            game_result = "lose"
        else:
            game_result = "draw"

        total_bet = self.bet
        if self.game.doubled_down:
            total_bet += self.bet
        if self.game.is_split:
            total_bet += self.bet
            if self.game.split_hand_doubled:
                total_bet += self.bet
        if self.game.has_insurance:
            total_bet += self.game.insurance_bet

        game_data = self.game.get_game_state()
        game_data["payout_details"] = details

        games_dao.add_game(
            user_id=self.player.id,
            guild_id=self.guild_id,
            game_type="blackjack",
            amount_bet=total_bet,
            amount_won=total_won if game_result != "draw" else 0,
            amount_lost=total_lost,
            result=game_result,
            game_data=game_data
        )

        # Update message with final state
        embed = self.create_game_embed()

        # Add detailed payout breakdown
        if self.game.surrendered:
            embed.add_field(name="Payout", value=f"Returned: {total_won:,} credits\nLost: {total_lost:,} credits", inline=False)
        else:
            payout_text = ""

            # Main hand
            if details["main_hand"]:
                result = details["main_hand"]["result"]
                won = details["main_hand"]["won"]
                lost = details["main_hand"]["lost"]
                if result == "player_blackjack":
                    payout_text += f"**Hand 1:** Blackjack! +{won - self.bet:,} (3:2)\n"
                elif result == "player_win":
                    payout_text += f"**Hand 1:** Win! +{won - self.bet:,}\n"
                elif result == "push":
                    payout_text += f"**Hand 1:** Push (bet returned)\n"
                else:
                    payout_text += f"**Hand 1:** Loss -{lost:,}\n"

            # Split hand
            if self.game.is_split and details["split_hand"]:
                result = details["split_hand"]["result"]
                won = details["split_hand"]["won"]
                lost = details["split_hand"]["lost"]
                if result == "player_win":
                    payout_text += f"**Hand 2:** Win! +{won - self.bet:,}\n"
                elif result == "push":
                    payout_text += f"**Hand 2:** Push (bet returned)\n"
                else:
                    payout_text += f"**Hand 2:** Loss -{lost:,}\n"

            # Insurance
            if self.game.has_insurance:
                if details["insurance"].get("won", 0) > 0:
                    ins_profit = details["insurance"]["won"] - self.game.insurance_bet
                    payout_text += f"**Insurance:** Win! +{ins_profit:,}\n"
                else:
                    payout_text += f"**Insurance:** Loss -{self.game.insurance_bet:,}\n"

            # Net result
            net = total_won - total_lost
            if net > 0:
                payout_text += f"\n**Net Profit:** +{net:,} credits 💰"
            elif net < 0:
                payout_text += f"\n**Net Loss:** {net:,} credits"
            else:
                payout_text += f"\n**Net:** Even"

            embed.add_field(name="Results", value=payout_text, inline=False)

        await self.message.edit(embed=embed, view=self)

        logger.info(f"Blackjack game {self.game_id} completed. Player: {self.player.display_name}, Net: {total_won - total_lost}")

    async def on_timeout(self):
        """Handle timeout"""
        if not self.game.game_over:
            # Disable all buttons
            for child in self.children:
                child.disabled = True

            # Treat timeout as player standing/surrendering
            if not self.main_game_started:
                # Timeout during insurance - treat as no insurance
                self.insurance_phase = False

            # Auto-play remaining actions
            while not self.game.game_over:
                self.game.player_stand_current()

            self.game.dealer_play()
            await self.end_game()

            # Add timeout message
            try:
                await self.message.reply("⏱️ Game timed out. Automatically completed.")
            except:
                pass  # Message might be deleted

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the player can interact with buttons"""
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return False
        return True
