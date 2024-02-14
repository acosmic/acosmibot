from tabnanny import check
import discord
from Dao.GamesDao import GamesDao
from Views.View_Rock_Paper_Scissors import View_Rock_Paper_Scissors
from Dao.UserDao import UserDao

class View_Start_RPS(discord.ui.View):

    joined_users = []
    declined_users = []
    tentative_users = []

    initiator: discord.User = None
    acceptor: discord.User = None
    players: int = 0
    bet: int = 0
    match_started = bool = False
    
    async def send(self, interaction: discord.Interaction):
        self.joined_users.append(interaction.user.display_name)
        embed = self.create_embed()
        await interaction.response.send_message(view=self, embed=embed)
        self.message = await interaction.original_response()

    async def announce_game_start(self):
        self.match_started = True
        await self.message.channel.send(f"{self.acceptor.mention} has accepted {self.initiator.mention}'s match. The match has started! <:Smirk:1200297264502034533>")



    async def on_timeout(self):
        if not self.match_started:
            gamesDao = GamesDao()
            # Disable all buttons
            for child in self.children:
                child.disabled = True
            
            gamesDao.set_game_inprogress(game_name="rps", inprogress=0)
            self.disable_all_buttons()
        
            message = self.message
            self.reset_game()
            timeout_message = "The Rock, Paper, Scissors match has timed out because no one joined. <:FeelsBigSad:1199734765230768139>"
            await message.edit(content=timeout_message, view=None, embed=None)
        

        

    def reset_game(self):
        self.joined_users.clear()
        self.declined_users.clear()
        self.tentative_users.clear()
        self.match_started = False
        self.initiator = None
        self.acceptor = None
        self.players = 0
        self.bet = 0
        

    def convert_user_list_to_str(self, user_list, defualt_str="No one"):
        if len(user_list):
            return "\n".join(user_list)
        return defualt_str

    def create_embed(self):
        desc = f"{self.initiator.display_name} is looking for a match. Bet = {self.bet} Credits!"
        embed = discord.Embed(title="Accept Rock, Paper, Scissors Match!?", description=desc)
        rps_image = "https://cdn.discordapp.com/attachments/1207159417980588052/1207160371798872165/acosmic_rock-paper-scissors.png?ex=65dea2b4&is=65cc2db4&hm=10f27e83933362fdd34dd986d958aa19dd27ac90d54be09e876a2b7e82afba25&"
        embed.add_field(inline=True, name="✅ Joined", value=self.convert_user_list_to_str(self.joined_users))
        embed.add_field(inline=True, name="🔄 Joined - 0 Bet", value=self.convert_user_list_to_str(self.tentative_users))
        embed.add_field(inline=True, name="❌ Declined", value=self.convert_user_list_to_str(self.declined_users))
        embed.set_image(url=rps_image)

        return embed
    
    def check_players_full_bet(self):
        if len(self.joined_users) >= self.players:
            return True
        return False
    
    def check_players_no_bet(self):
        if len(self.tentative_users) >= self.players:
            return True
        return False
    
    def disable_all_buttons(self):
        self.join_button.disabled = True
        self.decline_button.disabled = True
        self.no_bet_button.disabled = True

    async def update_message(self):
        if self.check_players_full_bet():
            self.disable_all_buttons()
            # THIS IS THE START OF THE GAME SEND TO NEW VIEW
            await self.announce_game_start()
            game_view = View_Rock_Paper_Scissors(timeout=120)
            game_view.player_one = self.initiator
            game_view.player_two = self.acceptor
            game_view.players = self.players
            game_view.message = self.message
            game_view.bet = self.bet
            # game_view.undecided_users.append(game_view.player_one.display_name)
            # game_view.undecided_users.append(game_view.player_two.display_name)
            await self.message.edit(view=game_view, embed=game_view.create_embed())
            self.joined_users.clear()
            self.declined_users.clear()
            self.tentative_users.clear()
        elif self.check_players_no_bet():
            self.disable_all_buttons()
            await self.announce_game_start()
            game_view = View_Rock_Paper_Scissors(timeout=120)
            game_view.player_one = self.initiator
            game_view.player_two = self.acceptor
            game_view.players = self.players
            game_view.message = self.message
            game_view.bet = 0
            await self.message.edit(view=game_view, embed=game_view.create_embed())
            self.joined_users.clear()
            self.declined_users.clear()
            self.tentative_users.clear()
        else:
            embed = self.create_embed()
            await self.message.edit(view=self, embed=embed)
    
    @discord.ui.button(label="Join", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button = discord.ui.Button):
        
        userDao = UserDao()
        current_user = userDao.get_user(interaction.user.id)
        current_user_credit = current_user.currency
        if current_user_credit >= self.bet:
            await interaction.response.defer()
            if interaction.user.display_name not in self.joined_users:
                self.joined_users.append(interaction.user.display_name)
                self.acceptor = interaction.user
            if interaction.user.display_name in self.tentative_users:
                self.tentative_users.remove(interaction.user.display_name)
            if interaction.user.display_name in self.declined_users:
                self.declined_users.remove(interaction.user.display_name)
        else:
            await interaction.response.send_message("You don't have enough Credits to accept this match.", ephemeral=True)

        await self.update_message()

    @discord.ui.button(label="Join - 0 Bet", style=discord.ButtonStyle.blurple)
    async def no_bet_button(self, interaction: discord.Interaction, button = discord.ui.Button):
        await interaction.response.defer()
        if interaction.user.display_name not in self.tentative_users:
            self.tentative_users.append(interaction.user.display_name)
            if interaction.user != self.initiator:
                self.acceptor = interaction.user
        if interaction.user.display_name in self.joined_users:
            self.joined_users.remove(interaction.user.display_name)
        if interaction.user.display_name in self.declined_users:
            self.declined_users.remove(interaction.user.display_name)
        await self.update_message()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline_button(self, interaction: discord.Interaction, button = discord.ui.Button):
        await interaction.response.defer()

        if interaction.user.display_name not in self.declined_users:
            self.declined_users.append(interaction.user.display_name)
        if interaction.user.display_name in self.tentative_users:
            self.tentative_users.remove(interaction.user.display_name)
        if interaction.user.display_name in self.joined_users:
            self.joined_users.remove(interaction.user.display_name)

        await self.update_message()

