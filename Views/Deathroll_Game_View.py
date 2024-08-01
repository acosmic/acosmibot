from email import message
import discord
from Dao.UserDao import UserDao
from Dao.GamesDao import GamesDao

class DeathrollGameView(discord.ui.View):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.current_player = game.current_player
        self.current_roll = game.current_roll
        self.is_finished = game.is_finished
        self.initiator = game.initiator
        self.target = game.target
        self.bet = game.bet
        self.message_id = game.message_id
        self.id = game.id

    async def send(self, interaction: discord.Interaction):
        self.joined_users.append(interaction.user.display_name)
        embed = self.create_embed()
        await interaction.response.send_message(view=self, embed=embed)
        self.message = await interaction.original_response()
        channel = self.message.channel
        
    def create_embed(self):
        embed = discord.Embed(title="Deathroll", description=f"Bet: {self.bet}\nCurrent Player: {self.current_player.mention}\nCurrent Roll: {self.current_roll}")
        return embed
    
    async def on_timeout(self):
        if self.game.is_finished:
            gamesDao = GamesDao()
            gamesDao.set_game_inprogress(game_name="deathroll", inprogress=0)
            self.disable_all_buttons()
            self.reset_game()
            timeout_message = "The Deathroll match has timed out. <:FeelsBigSad:1199734765230768139>"
            await self.message.edit(content=timeout_message, view=None, embed=None)

    def reset_game(self):
        self.joined_users.clear()
        self.declined_users.clear()
        self.tentative_users.clear()
        self.match_started = False
        self.initiator = None
        self.target = None
        self.players = 0
        self.bet = 0

    async def on_button_click(self, button: discord.ui.Button, interaction: discord.Interaction):
        