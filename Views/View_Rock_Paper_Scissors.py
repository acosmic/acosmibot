import discord
import logging
from Dao.GamesDao import GamesDao
from Dao.UserDao import UserDao

class View_Rock_Paper_Scissors(discord.ui.View):

    decided_users = []
    round_results = []
    winner_list = []
    players = 0

    player_one = discord.User = None
    player_two = discord.User = None
    round_number = 1
    player_one_choice = ""
    player_two_choice = ""
    player_one_decision = "Choosing..."
    player_two_decision = "Choosing..."
    player_one_wins = 0
    player_two_wins = 0
    draws = 0
    match_winner = ""
    match_loser = ""
    bet = int = 0
    match_complete = bool = False



    message = interaction = None
    

    async def send(self, interaction: discord.Interaction):
        return
        
    
    async def announce_winner(self):
        await self.message.channel.send(f"{self.match_winner.mention} has defeated {self.match_loser.mention} in a match of 🪨📄✂️ and won {self.bet} Credits! <a:LeoHYPE:1203568518302400512>")

    def create_embed(self):
        title = f" Round {self.round_number}: {self.player_one.display_name} vs. {self.player_two.display_name}"
        desc = f"Rock, Paper, Scissors, Shoot!"
        if self.check_if_winner():
            title = f"{self.match_winner.display_name} won in {self.round_number - 1} rounds!"
            desc = f"{self.player_one.display_name} vs. {self.player_two.display_name}"
            

        embed = discord.Embed(title=title, description=desc)
        if self.player_one_choice != "":
            self.player_one_decision = "Locked in!"
            
        if self.player_two_choice != "":
            self.player_two_decision = "Locked in!"


        for round_result in self.round_results[-5:]:
            player_one_name = round_result["player_one"]["user"]
            player_two_name = round_result["player_two"]["user"]
            player_one_choice = round_result["player_one"]["choice"]
            player_two_choice = round_result["player_two"]["choice"]
            winner = round_result["winner"]

            embed.add_field(name=f"{player_one_name}", value=player_one_choice, inline=True)
            embed.add_field(name=f"{player_two_name}", value=player_two_choice, inline=True)
            embed.add_field(name="Winner", value=winner, inline=True)



        # Add extra spacing for the current round
        # Adding empty field for spacing
        embed.add_field(inline=False, name="\u200b", value="\u200b")  # Adding another empty field for more spacing

        embed.add_field(inline=True, name=self.player_one.display_name, value=self.player_one_decision)
        embed.add_field(inline=True, name=self.player_two.display_name, value=self.player_two_decision)



        

        # logging.info(f"undecided list = {self.undecided_users}")
        logging.info(f"DECIDED list = {self.decided_users}")
        logging.info(f"player one = {self.player_one.display_name}")
        logging.info(f"player two= {self.player_two.display_name}")

        return embed
    
    async def on_timeout(self):
        if not self.match_complete:
            gamesDao = GamesDao()
            # Disable all buttons
            for child in self.children:
                child.disabled = True
            gamesDao.set_game_inprogress(game_name="rps", inprogress=0)
            message = self.message
            timeout_message = "The Rock, Paper, Scissors match has timed out. - View_Rock_Paper_Scissors"
            self.disable_all_buttons()
            await self.reset_game()
            await message.edit(content=timeout_message, embed=None)
        
    
    def check_players_decided(self):
        if len(self.decided_users) >= 2:
            return True
        return False
    
    def winner_payout(self):
        if self.player_one_wins >= 3:
            self.match_winner = self.player_one
            self.match_loser = self.player_two
            userDao_one = UserDao()
            userDao_two = UserDao()
            user_one = userDao_one.get_user(self.player_one.id)
            user_two = userDao_two.get_user(self.player_two.id)
            user_one.currency += self.bet
            user_two.currency -= self.bet
            userDao_one.update_user(user_one)
            userDao_two.update_user(user_two)
            
        elif self.player_two_wins >= 3:
            self.match_winner = self.player_two
            self.match_loser = self.player_one
            userDao_one = UserDao()
            userDao_two = UserDao()
            user_one = userDao_one.get_user(self.player_one.id)
            user_two = userDao_two.get_user(self.player_two.id)
            user_one.currency -= self.bet
            user_two.currency += self.bet
            userDao_one.update_user(user_one)
            userDao_two.update_user(user_two)
            

    def check_if_winner(self):
        if self.player_one_wins >= 3:
            self.match_winner = self.player_one
            self.match_loser = self.player_two
            self.player_one_decision = "🏆 WINNER! 🏆"
            self.player_two_decision = "<:FeelsBigSad:1199734765230768139>"
            self.match_complete = True

            
            return True 
        elif self.player_two_wins >= 3:
            self.match_winner = self.player_two
            self.match_loser = self.player_one
            self.player_one_decision = "<:FeelsBigSad:1199734765230768139>"
            self.player_two_decision = "🏆 WINNER! 🏆"
            self.match_complete = True
            
            return True
        return False



    async def reset_game(self):
        gamesDao = GamesDao()
        # Reset all attributes to initial states
        self.decided_users.clear()
        self.round_results.clear()
        self.winner_list.clear()
        self.players = 0
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
        self.message = None
        self.interaction = None
        self.match_complete = False
        gamesDao.set_game_inprogress(game_name="rps", inprogress=0)
        logging.info(f"GAME TIMEOUT RESET \n\n")

    async def complete_game(self):
        gamesDao = GamesDao()
        await self.announce_winner()
        self.winner_payout()
        # Reset all attributes to initial states
        self.decided_users.clear()
        self.round_results.clear()
        self.winner_list.clear()
        self.players = 0
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
        self.message = None
        self.interaction = None
        gamesDao.set_game_inprogress(game_name="rps", inprogress=0)
        logging.info(f"GAME COMPLETED \n\n")
    
    def disable_all_buttons(self):
        self.rock_button.disabled = True
        self.paper_button.disabled = True
        self.scissors_button.disabled = True

    def process_round_results(self):
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
            logging.info(f"WINNER of ROUND {self.round_number} = {winner} \n\n")

        round_result = {
            "player_one": {"user": self.player_one.display_name, "choice": self.player_one_choice},
            "player_two": {"user": self.player_two.display_name, "choice": self.player_two_choice},
            "winner": winner
        }

        self.round_results.append(round_result)
        self.winner_list.append(winner)
        logging.info(f"{round_result} \n\n")
        if winner != "Draw":
            # await self.message.channel.send(f"{winner.display_name} wins Round {self.round_number}!")
            # Clear choices for the next round
            self.player_one_choice = ""
            self.player_two_choice = ""
            self.decided_users.clear()
            self.round_number += 1
            # Check if there's a winner of the game
            if self.check_if_winner():
                # await self.message.channel.send(f"{winner.display_name} wins the game!")
                self.disable_all_buttons()
        else:
            self.player_one_choice = ""
            self.player_two_choice = ""
            self.decided_users.clear()
            self.round_number += 1
        

    async def update_message(self):
        if self.check_players_decided():
            self.player_one_decision = "Choosing..."
            self.player_two_decision = "Choosing..."
            self.process_round_results()
            embed = self.create_embed()
            await self.message.edit(view=self, embed=embed)

            if self.check_if_winner():
            # If there's a winner, reset the game
                await self.complete_game()
        
        else:
            embed = self.create_embed()
            await self.message.edit(view=self, embed=embed)

    @discord.ui.button(label="🪨", style=discord.ButtonStyle.gray)
    async def rock_button(self, interaction: discord.Interaction, button = discord.ui.Button):
        await interaction.response.defer()
        if interaction.user.id != self.player_one.id and interaction.user.id != self.player_two.id:
            logging.info(f"{interaction.user.display_name} pressed the Rock button but not a player")  

        else:
            if interaction.user == self.player_one:
                
                if self.player_one.display_name not in self.decided_users:
                    self.player_one_choice = "🪨"
                    self.decided_users.append(self.player_one.display_name)
                    # self.undecided_users.remove(self.player_one.display_name)  
            elif interaction.user == self.player_two:
                
                if self.player_two.display_name not in self.decided_users:
                    self.player_two_choice = "🪨"
                    self.decided_users.append(self.player_two.display_name)
                    # self.undecided_users.remove(self.player_two.display_name) 
                    

            await self.update_message()

    @discord.ui.button(label="📄", style=discord.ButtonStyle.grey)
    async def paper_button(self, interaction: discord.Interaction, button = discord.ui.Button):
        await interaction.response.defer()
        if interaction.user.id != self.player_one.id and interaction.user.id != self.player_two.id:            
            logging.info(f"{interaction.user.display_name} pressed the Paper button but not a player") 

        else:
            if interaction.user == self.player_one:
                
                if self.player_one.display_name not in self.decided_users:
                    self.player_one_choice = "📄"
                    self.decided_users.append(self.player_one.display_name)
                    # self.undecided_users.remove(self.player_one.display_name)  
            elif interaction.user == self.player_two:
                
                if self.player_two.display_name not in self.decided_users:
                    self.player_two_choice = "📄"
                    self.decided_users.append(self.player_two.display_name)
                    # self.undecided_users.remove(self.player_two.display_name) 
            
            await self.update_message()

    @discord.ui.button(label="✂️", style=discord.ButtonStyle.grey)
    async def scissors_button(self, interaction: discord.Interaction, button = discord.ui.Button):
        await interaction.response.defer()
        if interaction.user.id != self.player_one.id and interaction.user.id != self.player_two.id:
            logging.info(f"{interaction.user.display_name} pressed the Scissors button but not a player") 

        else:
            if interaction.user == self.player_one:
                
                if self.player_one.display_name not in self.decided_users:
                    self.player_one_choice = "✂️"
                    self.decided_users.append(self.player_one.display_name)
                    # self.undecided_users.remove(self.player_one.display_name)  
            elif interaction.user == self.player_two:
                
                if self.player_two.display_name not in self.decided_users:
                    self.player_two_choice = "✂️"
                    self.decided_users.append(self.player_two.display_name)
                    # self.undecided_users.remove(self.player_two.display_name) 

            await self.update_message()

    
     


    
        