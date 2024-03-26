from cmath import log
from hmac import new
import logging
from math import e
from os import access
import random
import discord
from discord import ButtonStyle
from Dao.UserDao import UserDao
from Dao.GamesDao import GamesDao
from Dao.DeathrollDao import DeathrollDao
from Entities.DeathrollEvent import DeathrollEvent



# copiloted - need to clean this up 
class Deathroll_View(discord.ui.View):
    joined_users = []

    initiator: discord.User = None
    target: discord.User = None
    
    players: int = 0
    bet: int = 0
    match_started: bool = False

    new_event: DeathrollEvent = None


    async def send(self, interaction: discord.Interaction):
        # self.joined_users.append(interaction.user.display_name)
        embed = self.create_embed()
        accept_button = AcceptButton()
        decline_button = DeclineButton()
        self.add_item(accept_button)
        self.add_item(decline_button)
        await interaction.response.send_message(view=self, embed=embed)
        self.message = await interaction.original_response()

        self.new_event = DeathrollEvent(0, self.initiator, self.target, self.bet, self.message.id, self.bet, self.target, 0)
        drDao = DeathrollDao()
        self.current_event = DeathrollEvent(0, self.initiator.id, self.target.id, self.bet, self.message.id, self.bet, self.target.id, 0)
        drDao.add_new_event(self.current_event)
        
        logging.info(f"new_event: {self.new_event}")
        
        channel = self.message.channel
        self.message2 = await channel.send(f"{self.target.mention}, {self.initiator.display_name} has challenged you to a game of Deathroll! Do you accept?")
        
    async def announce_game_start(self):
        self.match_started = True
        await self.message2.delete()
        self.message_start = await self.message.channel.send(f"{self.target.mention} has accepted {self.initiator.mention}'s match. The match has started! <:Smirk:1200297264502034533>")

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
        # self.joined_users.clear()
        # self.declined_users.clear()
        # self.tentative_users.clear()
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
        embed.add_field(name="Initiator", value=f"{initiator.display_name} - {initiator_balance} Credits", inline=False)
        embed.add_field(name="Target", value=f"{target.display_name} - {target_balance} Credits", inline=False)
        embed.add_field(name="Bet", value=f"{self.bet} Credits", inline=False)
        embed.add_field(name="Joined Users", value=self.convert_user_list_to_str(self.joined_users), inline=False)
        return embed
    
    def game_embed(self):
        for child in self.children:
            if isinstance(child, (AcceptButton, DeclineButton, GameButton)):
                self.remove_item(child)

        embed = discord.Embed(title=f"💀 Deathroll - {self.bet} Credits 💀\n{self.initiator.display_name} vs {self.target.display_name}", 
                              description=f"# {self.new_event.current_player.name}'s Turn \n\n # Roll: {self.new_event.current_roll}")

        

        turn_roll = f"{self.new_event.current_player.name}: Roll 1 - {self.new_event.current_roll}!"
        game_button = GameButton(turn_roll)
        self.add_item(game_button)
        return embed
    
    def end_game_embed(self):
        for child in self.children:
            if isinstance(child, (AcceptButton, DeclineButton, GameButton)):
                self.remove_item(child)

        embed = discord.Embed(title=f"💀 Deathroll - {self.bet} Credits 💀\n{self.initiator.display_name} vs {self.target.display_name}",
                                description=f"# Game Over! {self.new_event.current_player.name} rolled a 1 and lost {self.bet} credits!")
        if self.new_event.current_player == self.initiator:
            embed.add_field(name="Winner", value=f"{self.target.display_name}", inline=False)
        if self.new_event.current_player == self.target:
            embed.add_field(name="Winner", value=f"{self.initiator.display_name}", inline=False)
        return embed
    
    
    
    def disable_all_buttons(self):
        for child in self.children:
            child.disabled = True
        self.stop()



    async def update_message(self):
        try:
            embed = self.game_embed()
            await self.message.edit(embed=embed, view=self)
        except Exception as e:
            logging.error(f"update_message: {e}")

    async def end_game(self):
        try:
            embed = self.end_game_embed()
            await self.message.edit(embed=embed, view=self)
            self.disable_all_buttons()
            self.reset_game()
            self.stop()
            await self.message_start.delete()
            drDao = DeathrollDao()
            drDao.update_event(self.current_event)
        except Exception as e:
            logging.error(f"end_game: {e}")
            await self.message.channel.send(f"An error occurred. {e}")
            
    async def roll_dice(self, interaction: discord.Interaction):
        try:
            if interaction.user.id == self.new_event.current_player.id:
                roll = random.randint(1, self.new_event.current_roll)
                self.new_event.current_roll = roll
                if roll == 1:
                    
                    self.new_event.is_finished = 1
                    self.current_event.is_finished = 1
                    logging.info(f"Deathroll - Game finished - Loser: {self.new_event.current_player.name}")
                    await self.end_game()
                    
                else:
                    if self.new_event.current_player == self.new_event.initiator:
                        self.new_event.current_player = self.new_event.acceptor
                    else:
                        self.new_event.current_player = self.new_event.initiator
                await self.update_message()
        except Exception as e:
            logging.error(f"roll_dice: {e}")
            await interaction.response.send_message(f"An error occurred. {e}", ephemeral=True)
        

### BUTTONS
class GameButton(discord.ui.Button):
    def __init__(self, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        
    async def callback(self, interaction: discord.Interaction):
        logging.info("GameButton pressed")
        if interaction.user.id == self.view.new_event.current_player.id:
            try:
                view = self.view
                await view.roll_dice(interaction)

            except Exception as e:
                logging.error(f"GameButton: {e}")
                await interaction.response.send_message(f"An error occurred. {e}", ephemeral=True) 
        else:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)

class AcceptButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Accept", style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        view = self.view  # Access the view this button is part of
        if interaction.user.id == view.initiator.id:
            await interaction.response.send_message("You cannot join your own match!", ephemeral=True)
        elif interaction.user.id == view.target.id:
                embed = view.game_embed()
                await interaction.response.edit_message(embed=embed, view=view)
                await view.announce_game_start()
                logging.info("Deathroll - Game started")

class DeclineButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Decline", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        view = self.view  # Access the view this button is part of
        
        if interaction.user.id == view.initiator.id:
            await interaction.response.send_message("You cannot decline your own match!", ephemeral=True)
            return
        if interaction.user.id == view.target.id:
            
            await view.message.edit(content=f"{view.target.display_name} has declined {view.initiator.display_name}'s match. <:FeelsBadMan:1199734765230768139>", view=None, embed=None)
            await view.message2.delete()
            view.reset_game()
            drDao = DeathrollDao()
            drDao.delete_event(view.new_event.message_id)




        