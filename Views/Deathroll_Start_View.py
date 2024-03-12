from email import message
import discord
from Dao.UserDao import UserDao
from Dao.GamesDao import GamesDao
# from Views.Deathroll_Game_View import Deathroll_Game_View


# copiloted - need to clean this up 
class Deathroll_Start_View(discord.ui.View):
    joined_users = []

    target: discord.User = None
    target: discord.User = None
    
    players: int = 0
    bet: int = 0
    match_started = bool = False

    async def send(self, interaction: discord.Interaction):
        self.joined_users.append(interaction.user.display_name)
        embed = self.create_embed()
        await interaction.response.send_message(view=self, embed=embed)
        self.message = await interaction.original_response()
        channel = self.message.channel
        self.message2 = await channel.send(f"{self.target.mention}, {self.initiator.display_name} has challenged you to a game of Deathroll! Do you accept?")

    async def announce_game_start(self):
        self.match_started = True
        await self.message.channel.send(f"{self.target.mention} has accepted {self.initiator.mention}'s match. The match has started! <:Smirk:1200297264502034533>")
        # Start the Deathroll_Game_View here
        # deathroll_game_view = Deathroll_Game_View()
        # await deathroll_game_view.send(self.message.channel)

    async def on_timeout(self):
        if not self.match_started:
            gamesDao = GamesDao()
            # Disable all buttons
            for child in self.children:
                child.disabled = True
            
            gamesDao.set_game_inprogress(game_name="deathroll", inprogress=0)
            self.disable_all_buttons()
        
            message = self.message
            self.reset_game()
            timeout_message = "The Deathroll match has timed out because no one joined. <:FeelsBigSad:1199734765230768139>"
            await message.edit(content=timeout_message, view=None, embed=None)
        

    def reset_game(self):
        self.joined_users.clear()
        self.declined_users.clear()
        self.tentative_users.clear()
        self.match_started = False
        self.initiator = None
        self.target = None
        self.players = 0
        self.bet = 0
        
    def convert_user_list_to_str(self, user_list, default_str="No one"):
        if len(user_list):
            return ", ".join(user_list)
        else:
            return default_str

    def create_embed(self):
        user_dao = UserDao()
        initiator = self.initiator
        target = self.target
        initiator_balance = user_dao.get_user(initiator.id).currency
        target_balance = user_dao.get_user(target.id).currency
        embed = discord.Embed(title="Deathroll - TESTING", description="Two players roll a dice and the first player to roll a 1 loses!", color=0x00ff00)
        embed.add_field
        embed.add_field(name="Initiator", value=f"{initiator.display_name} - {initiator_balance} Credits", inline=False)
        embed.add_field(name="Target", value=f"{target.display_name} - {target_balance} Credits", inline=False)
        embed.add_field(name="Bet", value=f"{self.bet} Credits", inline=False)
        embed.add_field(name="Joined Users", value=self.convert_user_list_to_str(self.joined_users), inline=False)
        return embed
    
    def disable_all_buttons(self):
        for child in self.children:
            child.disabled = True
        self.stop()

    async def update_message(self):
        
        
        embed = self.create_embed()
        await self.message.edit(embed=embed, view=self)


    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.initiator.id:
            await interaction.response.send_message("You cannot join your own match!", ephemeral=True)
            
        if interaction.user.id == self.target.id:
            await interaction.response.send_message(f"{self.target.display_name} has already joined the match!", ephemeral=True)
            
       
        self.joined_users.append(interaction.user.display_name)
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        if len(self.joined_users) == 2:
            await self.announce_game_start()
            self.disable_all_buttons()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.initiator.id:
            await interaction.response.send_message("You cannot decline your own match!", ephemeral=True)
            return
        if interaction.user.id == self.target.id:
            gamesDao = GamesDao()
            gamesDao.set_game_inprogress(game_name="deathroll", inprogress=0)
            await self.message.edit(content=f"{self.target.display_name} has declined {self.initiator.display_name}'s match. <:FeelsBadMan:1199734765230768139>", view=None, embed=None)
            await self.message2.delete()
            self.reset_game()
        
        