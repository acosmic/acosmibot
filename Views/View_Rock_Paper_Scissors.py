import discord
import logging
from datetime import datetime
from Dao.GamesDao import GamesDao
from Dao.GuildUserDao import GuildUserDao
import uuid


class View_Rock_Paper_Scissors(discord.ui.View):
    """Combined view for both matchmaking and gameplay phases of RPS"""

    def __init__(self, timeout=120, is_matchmaking=True, session_manager=None):
        super().__init__(timeout=timeout)
        self.is_matchmaking = is_matchmaking
        self.session_manager = session_manager  # Pass SessionManager instance
        self.guild_id = None
        self.game_id = str(uuid.uuid4())  # Unique identifier for this game instance

        # Matchmaking phase attributes
        self.joined_users = []
        self.declined_users = []
        self.tentative_users = []
        self.initiator = None
        self.acceptor = None
        self.bet = 0
        self.match_started = False

        # Game phase attributes
        self.decided_users = []
        self.round_results = []
        self.player_one = None
        self.player_two = None
        self.round_number = 1
        self.player_one_choice = ""
        self.player_two_choice = ""
        self.player_one_decision = "Choosing..."
        self.player_two_decision = "Choosing..."
        self.player_one_wins = 0
        self.player_two_wins = 0
        self.draws = 0
        self.match_winner = ""
        self.match_loser = ""
        self.match_complete = False
        self.message = None

        # Update buttons based on phase
        self.clear_items()
        if self.is_matchmaking:
            self.add_matchmaking_buttons()
        else:
            self.add_game_buttons()

    def add_matchmaking_buttons(self):
        """Add buttons for the matchmaking phase"""
        self.add_item(discord.ui.Button(
            label="Join", style=discord.ButtonStyle.green,
            custom_id=f"join_button_{self.game_id}", emoji="✅"
        ))
        self.add_item(discord.ui.Button(
            label="Join - 0 Bet", style=discord.ButtonStyle.blurple,
            custom_id=f"no_bet_button_{self.game_id}", emoji="🔄"
        ))
        self.add_item(discord.ui.Button(
            label="Decline", style=discord.ButtonStyle.red,
            custom_id=f"decline_button_{self.game_id}", emoji="❌"
        ))

    def add_game_buttons(self):
        """Add buttons for the game phase"""
        self.add_item(discord.ui.Button(
            label="🪨", style=discord.ButtonStyle.gray,
            custom_id=f"rock_button_{self.game_id}"
        ))
        self.add_item(discord.ui.Button(
            label="📄", style=discord.ButtonStyle.grey,
            custom_id=f"paper_button_{self.game_id}"
        ))
        self.add_item(discord.ui.Button(
            label="✂️", style=discord.ButtonStyle.grey,
            custom_id=f"scissors_button_{self.game_id}"
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Handle button interactions for both phases"""
        custom_id = interaction.data.get('custom_id')

        # Verify this interaction belongs to this game instance
        if not custom_id.endswith(self.game_id):
            return False

        if self.is_matchmaking:
            return await self.handle_matchmaking_interaction(interaction)
        else:
            return await self.handle_game_interaction(interaction)

    async def handle_matchmaking_interaction(self, interaction: discord.Interaction):
        """Handle matchmaking phase button clicks"""
        custom_id = interaction.data.get('custom_id')

        if custom_id.startswith("join_button"):
            await self.join_button_click(interaction)
        elif custom_id.startswith("no_bet_button"):
            await self.no_bet_button_click(interaction)
        elif custom_id.startswith("decline_button"):
            await self.decline_button_click(interaction)

        return True

    async def handle_game_interaction(self, interaction: discord.Interaction):
        """Handle game phase button clicks"""
        custom_id = interaction.data.get('custom_id')

        if interaction.user.id != self.player_one.id and interaction.user.id != self.player_two.id:
            await interaction.response.send_message("You're not a player in this match!", ephemeral=True)
            return False

        choice = ""
        if custom_id.startswith("rock_button"):
            choice = "🪨"
        elif custom_id.startswith("paper_button"):
            choice = "📄"
        elif custom_id.startswith("scissors_button"):
            choice = "✂️"

        await self.make_choice(interaction, choice)
        return True

    async def send(self, interaction: discord.Interaction):
        """Send the initial matchmaking message"""
        self.joined_users.append(interaction.user.display_name)
        embed = self.create_matchmaking_embed()
        await interaction.response.send_message(view=self, embed=embed)
        self.message = await interaction.original_response()

    async def announce_game_start(self):
        """Announce that the game has started"""
        self.match_started = True
        await self.message.channel.send(
            f"{self.acceptor.mention} has accepted {self.initiator.mention}'s match. The match has started! <:Smirk:1200297264502034533>")

    async def announce_winner(self):
        """Announce the match winner"""
        await self.message.channel.send(
            f"{self.match_winner.mention} has defeated {self.match_loser.mention} in a match of 🪨📄✂️ and won {self.bet} Credits! <a:LeoHYPE:1203568518302400512>")

    async def on_timeout(self):
        """Handle timeout for both phases"""
        if self.is_matchmaking and not self.match_started:
            # Disable all buttons
            for child in self.children:
                child.disabled = True

            timeout_message = "The Rock, Paper, Scissors match has timed out because no one joined. <:UglyCry:1200263947274698892>"
            await self.message.edit(content=timeout_message, view=None, embed=None)

        elif not self.is_matchmaking and not self.match_complete:
            # Game phase timeout
            for child in self.children:
                child.disabled = True
            timeout_message = "The Rock, Paper, Scissors match has timed out."
            await self.message.edit(content=timeout_message, embed=None)

    def create_matchmaking_embed(self):
        """Create embed for matchmaking phase"""
        desc = f"{self.initiator.display_name} is looking for a match. Bet = {self.bet} Credits!"
        embed = discord.Embed(title="Accept Rock, Paper, Scissors Match!?", description=desc)


        embed.set_image(url="https://cdn.discordapp.com/attachments/1207159417980588052/1283269805520195634/ac_rock-paper-scissors-halloween.png?ex=68e53363&is=68e3e1e3&hm=3a0bb30607b2abfb7b65c5376a371c0c8d344f4cc56bd341106d9828964af141&")

        embed.add_field(inline=True, name="✅ Joined", value=self.convert_user_list_to_str(self.joined_users))
        embed.add_field(inline=True, name="🔄 Joined - 0 Bet", value=self.convert_user_list_to_str(self.tentative_users))
        embed.add_field(inline=True, name="❌ Declined", value=self.convert_user_list_to_str(self.declined_users))
        return embed

    def create_game_embed(self):
        """Create embed for game phase"""
        title = f"Round {self.round_number}: {self.player_one.display_name} vs. {self.player_two.display_name}"
        desc = f"Rock, Paper, Scissors, Shoot!"

        if self.check_if_winner():
            title = f"{self.match_winner.display_name} won in {self.round_number - 1} rounds!"
            desc = f"{self.player_one.display_name} vs. {self.player_two.display_name}"

        embed = discord.Embed(title=title, description=desc)

        if self.player_one_choice != "":
            self.player_one_decision = "Locked in!"
        if self.player_two_choice != "":
            self.player_two_decision = "Locked in!"

        # Show last 5 round results
        for round_result in self.round_results[-5:]:
            player_one_name = round_result["player_one"]["user"]
            player_two_name = round_result["player_two"]["user"]
            player_one_choice = round_result["player_one"]["choice"]
            player_two_choice = round_result["player_two"]["choice"]
            winner = round_result["winner"]

            embed.add_field(name=f"{player_one_name}", value=player_one_choice, inline=True)
            embed.add_field(name=f"{player_two_name}", value=player_two_choice, inline=True)
            embed.add_field(name="Winner", value=winner, inline=True)

        # Add spacing and current round info
        embed.add_field(inline=False, name="\u200b", value="\u200b")
        embed.add_field(inline=True, name=self.player_one.display_name, value=self.player_one_decision)
        embed.add_field(inline=True, name=self.player_two.display_name, value=self.player_two_decision)

        return embed

    def convert_user_list_to_str(self, user_list, default_str="No one"):
        """Convert user list to string for display"""
        if len(user_list):
            return "\n".join(user_list)
        return default_str

    def check_players_full_bet(self):
        """Check if enough players joined with full bet"""
        return len(self.joined_users) >= 2

    def check_players_no_bet(self):
        """Check if enough players joined with no bet"""
        return len(self.tentative_users) >= 2

    def check_players_decided(self):
        """Check if both players have made their choice"""
        return len(self.decided_users) >= 2

    def check_if_winner(self):
        """Check if there's a match winner"""
        if self.player_one_wins >= 3:
            self.match_winner = self.player_one
            self.match_loser = self.player_two
            self.player_one_decision = "🏆 WINNER! 🏆"
            self.player_two_decision = "<:UglyCry:1200263947274698892>"
            self.match_complete = True
            return True
        elif self.player_two_wins >= 3:
            self.match_winner = self.player_two
            self.match_loser = self.player_one
            self.player_one_decision = "<:UglyCry:1200263947274698892>"
            self.player_two_decision = "🏆 WINNER! 🏆"
            self.match_complete = True
            return True
        return False

    async def join_button_click(self, interaction: discord.Interaction):
        """Handle join button click"""
        guild_user_dao = GuildUserDao()
        current_user = guild_user_dao.get_guild_user(interaction.user.id, self.guild_id)

        if not current_user or current_user.currency < self.bet:
            await interaction.response.send_message("You don't have enough Credits to accept this match.",
                                                    ephemeral=True)
            return

        await interaction.response.defer()

        if interaction.user.display_name not in self.joined_users:
            self.joined_users.append(interaction.user.display_name)
            self.acceptor = interaction.user

        if interaction.user.display_name in self.tentative_users:
            self.tentative_users.remove(interaction.user.display_name)
        if interaction.user.display_name in self.declined_users:
            self.declined_users.remove(interaction.user.display_name)

        await self.update_matchmaking_message()

    async def no_bet_button_click(self, interaction: discord.Interaction):
        """Handle no bet button click"""
        await interaction.response.defer()

        if interaction.user.display_name not in self.tentative_users:
            self.tentative_users.append(interaction.user.display_name)
            if interaction.user != self.initiator:
                self.acceptor = interaction.user

        if interaction.user.display_name in self.joined_users:
            self.joined_users.remove(interaction.user.display_name)
        if interaction.user.display_name in self.declined_users:
            self.declined_users.remove(interaction.user.display_name)

        await self.update_matchmaking_message()

    async def decline_button_click(self, interaction: discord.Interaction):
        """Handle decline button click"""
        await interaction.response.defer()

        if interaction.user.display_name not in self.declined_users:
            self.declined_users.append(interaction.user.display_name)
        if interaction.user.display_name in self.tentative_users:
            self.tentative_users.remove(interaction.user.display_name)
        if interaction.user.display_name in self.joined_users:
            self.joined_users.remove(interaction.user.display_name)

        await self.update_matchmaking_message()

    async def make_choice(self, interaction: discord.Interaction, choice: str):
        """Handle player choice during game"""
        await interaction.response.defer()

        if interaction.user == self.player_one:
            if self.player_one.display_name not in self.decided_users:
                self.player_one_choice = choice
                self.decided_users.append(self.player_one.display_name)
        elif interaction.user == self.player_two:
            if self.player_two.display_name not in self.decided_users:
                self.player_two_choice = choice
                self.decided_users.append(self.player_two.display_name)

        await self.update_game_message()

    async def update_matchmaking_message(self):
        """Update message during matchmaking phase"""
        if self.check_players_full_bet():
            await self.start_game_with_bet()
        elif self.check_players_no_bet():
            await self.start_game_no_bet()
        else:
            embed = self.create_matchmaking_embed()
            await self.message.edit(view=self, embed=embed)

    async def start_game_with_bet(self):
        """Start the game with betting"""
        await self.transition_to_game_phase()

    async def start_game_no_bet(self):
        """Start the game without betting"""
        self.bet = 0
        await self.transition_to_game_phase()

    async def transition_to_game_phase(self):
        """Transition from matchmaking to game phase"""
        # Disable matchmaking buttons
        for child in self.children:
            child.disabled = True

        await self.announce_game_start()

        # Set up game
        self.is_matchmaking = False
        self.player_one = self.initiator
        self.player_two = self.acceptor

        # Clear items and add game buttons
        self.clear_items()
        self.add_game_buttons()

        # Clear lists
        self.joined_users.clear()
        self.declined_users.clear()
        self.tentative_users.clear()

        # Update message with game embed
        embed = self.create_game_embed()
        await self.message.edit(view=self, embed=embed)

    async def update_game_message(self):
        """Update message during game phase"""
        if self.check_players_decided():
            self.player_one_decision = "Choosing..."
            self.player_two_decision = "Choosing..."
            self.process_round_results()
            embed = self.create_game_embed()
            await self.message.edit(view=self, embed=embed)

            if self.check_if_winner():
                await self.complete_game()
        else:
            embed = self.create_game_embed()
            await self.message.edit(view=self, embed=embed)

    def process_round_results(self):
        """Process the results of a round"""
        # Determine winner of the round
        if (self.player_one_choice == "🪨" and self.player_two_choice == "✂️") or \
                (self.player_one_choice == "📄" and self.player_two_choice == "🪨") or \
                (self.player_one_choice == "✂️" and self.player_two_choice == "📄"):
            winner = self.player_one.display_name
            self.player_one_wins += 1
        elif (self.player_two_choice == "🪨" and self.player_one_choice == "✂️") or \
                (self.player_two_choice == "📄" and self.player_one_choice == "🪨") or \
                (self.player_two_choice == "✂️" and self.player_one_choice == "📄"):
            winner = self.player_two.display_name
            self.player_two_wins += 1
        else:
            winner = "Draw"
            self.draws += 1

        round_result = {
            "player_one": {"user": self.player_one.display_name, "choice": self.player_one_choice},
            "player_two": {"user": self.player_two.display_name, "choice": self.player_two_choice},
            "winner": winner
        }

        self.round_results.append(round_result)
        logging.info(f"Round {self.round_number} result: {round_result}")

        # Clear choices for the next round
        self.player_one_choice = ""
        self.player_two_choice = ""
        self.decided_users.clear()
        self.round_number += 1

    async def winner_payout(self):
        """Handle winner payout"""
        if self.bet <= 0:
            return

        guild_user_dao = GuildUserDao()
        games_dao = GamesDao()

        winner_id = None
        loser_id = None
        winner_player = None
        loser_player = None

        if self.player_one_wins >= 3:
            winner_id = self.player_one.id
            loser_id = self.player_two.id
            winner_player = self.player_one
            loser_player = self.player_two
        elif self.player_two_wins >= 3:
            winner_id = self.player_two.id
            loser_id = self.player_one.id
            winner_player = self.player_two
            loser_player = self.player_one

        if winner_id and loser_id:
            # Generate game_instance_id to link the two game entries
            game_instance_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Try to queue games and update currency in sessions
            if self.session_manager:
                # Update currency for winner
                winner_updated = await self.session_manager.update_currency(
                    guild_id=self.guild_id,
                    user_id=winner_id,
                    amount=self.bet
                )
                # Update currency for loser
                loser_updated = await self.session_manager.update_currency(
                    guild_id=self.guild_id,
                    user_id=loser_id,
                    amount=-self.bet
                )

                # Fallback to immediate DB writes if session updates failed
                if not winner_updated:
                    guild_user_dao.update_currency_with_global_sync(winner_id, self.guild_id, self.bet)
                if not loser_updated:
                    guild_user_dao.update_currency_with_global_sync(loser_id, self.guild_id, -self.bet)

                # Queue game for winner
                winner_queued = await self.session_manager.queue_game(
                    guild_id=self.guild_id,
                    user_id=winner_id,
                    game_type="rockpaperscissors",
                    amount_bet=self.bet,
                    amount_won=self.bet,
                    amount_lost=0,
                    result="win",
                    game_data={
                        "opponent_id": loser_id,
                        "opponent_name": loser_player.display_name,
                        "rounds": self.round_number - 1,
                        "player_wins": self.player_one_wins if winner_id == self.player_one.id else self.player_two_wins,
                        "opponent_wins": self.player_two_wins if winner_id == self.player_one.id else self.player_one_wins,
                        "draws": self.draws,
                        "game_instance_id": game_instance_id
                    },
                    timestamp=timestamp
                )

                # Queue game for loser
                loser_queued = await self.session_manager.queue_game(
                    guild_id=self.guild_id,
                    user_id=loser_id,
                    game_type="rockpaperscissors",
                    amount_bet=self.bet,
                    amount_won=0,
                    amount_lost=self.bet,
                    result="lose",
                    game_data={
                        "opponent_id": winner_id,
                        "opponent_name": winner_player.display_name,
                        "rounds": self.round_number - 1,
                        "player_wins": self.player_two_wins if loser_id == self.player_two.id else self.player_one_wins,
                        "opponent_wins": self.player_one_wins if loser_id == self.player_two.id else self.player_two_wins,
                        "draws": self.draws,
                        "game_instance_id": game_instance_id
                    },
                    timestamp=timestamp
                )

                # Fallback to immediate DB writes if queuing failed
                if not winner_queued or not loser_queued:
                    if not winner_queued:
                        games_dao.add_game(
                            user_id=winner_id,
                            guild_id=self.guild_id,
                            game_type="rockpaperscissors",
                            amount_bet=self.bet,
                            amount_won=self.bet,
                            amount_lost=0,
                            result="win",
                            game_data={
                                "opponent_id": loser_id,
                                "opponent_name": loser_player.display_name,
                                "rounds": self.round_number - 1,
                                "player_wins": self.player_one_wins if winner_id == self.player_one.id else self.player_two_wins,
                                "opponent_wins": self.player_two_wins if winner_id == self.player_one.id else self.player_one_wins,
                                "draws": self.draws,
                                "game_instance_id": game_instance_id
                            }
                        )

                    if not loser_queued:
                        games_dao.add_game(
                            user_id=loser_id,
                            guild_id=self.guild_id,
                            game_type="rockpaperscissors",
                            amount_bet=self.bet,
                            amount_won=0,
                            amount_lost=self.bet,
                            result="lose",
                            game_data={
                                "opponent_id": winner_id,
                                "opponent_name": winner_player.display_name,
                                "rounds": self.round_number - 1,
                                "player_wins": self.player_two_wins if loser_id == self.player_two.id else self.player_one_wins,
                                "opponent_wins": self.player_one_wins if loser_id == self.player_two.id else self.player_two_wins,
                                "draws": self.draws,
                                "game_instance_id": game_instance_id
                            }
                        )
            else:
                # No session manager - immediate DB writes
                guild_user_dao.update_currency_with_global_sync(winner_id, self.guild_id, self.bet)
                guild_user_dao.update_currency_with_global_sync(loser_id, self.guild_id, -self.bet)

                # Record game for winner
                games_dao.add_game(
                    user_id=winner_id,
                    guild_id=self.guild_id,
                    game_type="rockpaperscissors",
                    amount_bet=self.bet,
                    amount_won=self.bet,
                    amount_lost=0,
                    result="win",
                    game_data={
                        "opponent_id": loser_id,
                        "opponent_name": loser_player.display_name,
                        "rounds": self.round_number - 1,
                        "player_wins": self.player_one_wins if winner_id == self.player_one.id else self.player_two_wins,
                        "opponent_wins": self.player_two_wins if winner_id == self.player_one.id else self.player_one_wins,
                        "draws": self.draws,
                        "game_instance_id": game_instance_id
                    }
                )

                # Record game for loser
                games_dao.add_game(
                    user_id=loser_id,
                    guild_id=self.guild_id,
                    game_type="rockpaperscissors",
                    amount_bet=self.bet,
                    amount_won=0,
                    amount_lost=self.bet,
                    result="lose",
                    game_data={
                        "opponent_id": winner_id,
                        "opponent_name": winner_player.display_name,
                        "rounds": self.round_number - 1,
                        "player_wins": self.player_two_wins if loser_id == self.player_two.id else self.player_one_wins,
                        "opponent_wins": self.player_one_wins if loser_id == self.player_two.id else self.player_two_wins,
                        "draws": self.draws,
                        "game_instance_id": game_instance_id
                    }
                )

    async def complete_game(self):
        """Complete the game"""
        if not self.match_complete:
            return 
            
        if self.bet > 0:
            await self.announce_winner()
            await self.winner_payout()

        # Disable all buttons
        for child in self.children:
            child.disabled = True

        logging.info(f"RPS game {self.game_id} completed in guild {self.guild_id}")
        await self.message.edit(view=self)