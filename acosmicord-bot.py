#! /usr/bin/python3.8
from ast import alias
from code import interact
from curses.ascii import US
import random
from urllib import response
from click import option
import discord
from discord.ext import commands
from discord import Message, app_commands
from numpy import True_
from Dao.UserDao import UserDao
from database import Database
from Entities.User import User
from datetime import datetime
import logging
from dotenv import load_dotenv
import os


load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

client_id = os.getenv('client_id')
client_secret =  os.getenv('client_secret')
TOKEN = os.getenv('TOKEN')
MY_GUILD = discord.Object(id=int(os.getenv('MY_GUILD')))

# Configure the logging settings
logging.basicConfig(filename='/root/dev/acosmicord-bot/logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


role_level_1 = "Level One"
role_level_2 = "Level Two"
role_level_3 = "Level Three"
role_level_4 = "Level Four"
role_level_5 = "Level Five"
role_level_6 = "Level Six"
role_level_7 = "Level Seven"
role_level_8 = "Level Eight"
role_level_9 = "Level Nine"
role_level_10 = "Level Ten"


intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents = intents)

@bot.event
async def on_ready():
    logging.info(f'Logged on as {bot.user}!')
    await bot.tree.sync(guild=MY_GUILD)

@bot.event 
async def on_message(message):
    
    if not message.author.bot:
        logging.info(f'Message from {message.author}: {message.content}')
        role1 = discord.utils.get(message.guild.roles, name=role_level_1)
        role2 = discord.utils.get(message.guild.roles, name=role_level_2)
        role3 = discord.utils.get(message.guild.roles, name=role_level_3)
        role4 = discord.utils.get(message.guild.roles, name=role_level_4)
        role5 = discord.utils.get(message.guild.roles, name=role_level_5)
        role6 = discord.utils.get(message.guild.roles, name=role_level_6)
        role7 = discord.utils.get(message.guild.roles, name=role_level_7)
        role8 = discord.utils.get(message.guild.roles, name=role_level_8)
        role9 = discord.utils.get(message.guild.roles, name=role_level_9)
        role10 = discord.utils.get(message.guild.roles, name=role_level_10)

        dao = UserDao()

        current_user = dao.get_user(str(message.author))
        logging.info(f'{str(message.author)} grabbed from get_user() in on_message()')
        if current_user is not None:
            current_user.exp += 2
            current_user.exp_gained += 2
            current_user.messages_sent += 1
            current_user.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_level = current_user.level

            if current_user.exp < 100:
                role = role1
                current_user.level = 1
            elif current_user.exp >= 100 and current_user.exp < 200:
                role = role2
                current_user.level = 2
            elif current_user.exp >= 200 and current_user.exp < 300:
                role = role3
                current_user.level = 3
            elif current_user.exp >= 300 and current_user.exp < 400:
                role = role4
                current_user.level = 4
            elif current_user.exp >= 400 and current_user.exp < 500:
                role = role5
                current_user.level = 5
            elif current_user.exp >= 500 and current_user.exp < 600:
                role = role6
                current_user.level = 6
            elif current_user.exp >= 600 and current_user.exp < 700:
                role = role7
                current_user.level = 7
            elif current_user.exp >= 700 and current_user.exp < 800:
                role = role8
                current_user.level = 8
            elif current_user.exp >= 800 and current_user.exp < 900:
                role = role9
                current_user.level = 9
            elif current_user.exp >= 900:
                role = role10
                current_user.level = 10
            

            if current_user.level > current_level:
                await message.reply(f'GG! You have been promoted up to {str(role)}!')
                
            try:
                dao.update_user(current_user)
                logging.info(f'{str(message.author)} updated in database in on_message()')
            except Exception as e: 
                logging.error(f'Error updating {message.author} to the database: {e}')
            await message.author.add_roles(role)
        else:
            join_date = message.author.joined_at

            # Convert join_date to a format suitable for database insertion (e.g., as a string)
            formatted_join_date = join_date.strftime("%Y-%m-%d %H:%M:%S")

            new_user_data = {
            'id': 0,
            'discord_username': str(message.author),
            'level': 1,
            'streak': 0,
            'exp': 0,
            'exp_gained': 0,
            'exp_lost': 0,
            'currency': 0,
            'messages_sent': 1,
            'reactions_sent': 0,
            'created': formatted_join_date,
            'last_active': formatted_join_date
            }
            new_user = User(**new_user_data)
            try:
                dao.add_user(new_user)
                logging.info(f'{message.author} added to the database.')
            except Exception as e:
                logging.error(f'on_message() - Error adding user to the database: {e}')


@bot.event 
async def on_raw_reaction_add(payload):
    channel = bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = await bot.fetch_user(payload.user_id)
    emoji = payload.emoji
    dao = UserDao()

    discord_username = user.name
    current_user=dao.get_user(discord_username)

    # Increment user total reactions 
    current_user.reactions_sent += 1

    try:
        dao.update_user(current_user)
        logging.info(f"{discord_username} added {emoji} to {message.author}'s message .")
        logging.info(f"incremented and updated db reactions_sent for {discord_username}")
    except Exception as e:
        logging.error(f'on_raw_reaction_add() - Error updating user to the database: {e}')
    

# This function adds new users to the database if they don't already exist and assigns the lvl1 role
@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name=role_level_1)
    join_date = member.joined_at
    dao = UserDao()

    # Convert join_date to a format suitable for database insertion (e.g., as a string)
    formatted_join_date = join_date.strftime("%Y-%m-%d %H:%M:%S")

    member_data = {
    'id': 0,
    'discord_username': member.name,
    'level': 1,
    'streak': 0,
    'exp': 0,
    'exp_gained': 0,
    'exp_lost': 0,
    'currency': 0,
    'messages_sent': 0,
    'reactions_sent': 0,
    'created': formatted_join_date,
    'last_active': formatted_join_date
    }
    new_user = User(**member_data)
    existing_user = dao.get_user(new_user.discord_username)

    if existing_user is None:
        await member.add_roles(role)
        logging.info(f'Auto assigned {role} role to {member}')

        # add new user to database
        try:
            dao.add_user(new_user)
            logging.info(f'{new_user.discord_username} added to the database.')
        except Exception as e:
            logging.error(f'on_member_join() - Error adding user to the database: {e}')
    else:
        logging.info(f'{new_user.discord_username} already exists, so was not added again.')

@bot.tree.command(name = "rank", description = "returns your rank based on current EXP.", guild=MY_GUILD) 
async def rank_command(interaction: discord.Interaction):
    dao = UserDao()
    user_rank = dao.get_user_rank(interaction.user.name)
    
    current_user = dao.get_user(interaction.user.name)

    if user_rank is not None:
        embed = discord.Embed(
        title=f"{interaction.user.name}'s Stats",
        description=(
        f"Ranked #{user_rank[-1]}\n"
        f"Current Level: {current_user.level}\n"
        f"Current EXP: {current_user.exp}\n"
        f"Total Messages: {current_user.messages_sent}\n"
        f"Total Reactions: {current_user.reactions_sent}\n"
        ),
        color=interaction.user.color)
        embed.set_thumbnail(url=interaction.user.avatar)

        await interaction.response.send_message(embed=embed)

    else:
        logging.info(f"The user with Discord username {interaction.user.name} was not found in the database.")
        
        role = discord.utils.get(interaction.user.guild.roles, name=role_level_1)
        await interaction.user.add_roles(role)
        join_date = interaction.user.joined_at

        # Convert join_date to a format suitable for database insertion (e.g., as a string)
        formatted_join_date = join_date.strftime("%Y-%m-%d %H:%M:%S")

        user_data = {
        'id': 0,
        'discord_username': str(interaction.user.name),
        'level': 1,
        'streak': 0,
        'exp': 0,
        'exp_gained': 0,
        'exp_lost': 0,
        'currency': 0,
        'messages_sent': 1,
        'reactions_sent': 0,
        'created': formatted_join_date,
        'last_active': formatted_join_date 
        }

        new_user = User(**user_data)
        dao.add_user(new_user)
        logging.info(f'{new_user.discord_username} added to the database.')
        await interaction.response.send_message(f'{interaction.user.name} was not found in the database. {new_user.discord_username} added to the database.')
    # await interaction.response.send_message("Hello!") 
    logging.info(f"{interaction.user.name} used /rank command")
    
@bot.tree.command(name = "give", description = "give currency", guild=MY_GUILD) 
async def give_command(interaction: discord.Interaction, target: discord.Member, amount: int):
    role = discord.utils.get(interaction.guild.roles, name="Acosmic")
    dao = UserDao()
    if role in interaction.user.roles:
        target_user = dao.get_user(target.name)
        target_user.currency += amount
        try:
            dao.update_user(target_user)
            await interaction.response.send_message(f'{interaction.user.name} has given {target.mention} {amount} credits! <a:pepesith:1165101386921418792>')
        except Exception as e:
            logging.info(f'/give command - target = {target.name} - {e}.')
    else:
        await interaction.response.send_message(f'only {role} can run this command. <:FeelsNaughty:1199732493792858214>')
        
@bot.tree.command(name = "balance", description = "check your Credit balance.", guild=MY_GUILD) 
async def give_command(interaction: discord.Interaction):
    dao = UserDao()
    user = dao.get_user(interaction.user.name)

    await interaction.response.send_message(f'Your balance: {user.currency} Credits. <:PepeRich:1200265584877772840> {interaction.user.mention}')


@bot.tree.command(name = "8ball", description = "Ask the magic 8ball your yes/no questions for 10 Credits", guild=MY_GUILD) 
async def give_command(interaction: discord.Interaction, question: str):
    # List of 8-ball responses
    responses = [
        "It is certain.",
        "It is decidedly so.",
        "Without a doubt.",
        "Yes - definitely.",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Yes.",
        "Signs point to yes.",
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful."
    ]
    dao = UserDao()
    cost = 10
    user = dao.get_user(interaction.user.name)

    if user.currency >= cost:
        
        eightball = random.choice(responses) 
        await interaction.response.send_message(f"{interaction.user.name} asks: {question}\n\n <:PepeWizard:1200288529138327662> {eightball} 🎱  \n\n*{cost} Credits have been withdrawn from your balance*")
        user.currency -= cost
        dao.update_user(user)
    else:
        await interaction.response.send_message(f"You're too broke to use the magic 8ball. <:OhGodMan:1200262332392157184>")

@bot.tree.command(name = "polymorph", description = "Change your target's display name for 1000 Credits... please be nice", guild=MY_GUILD) 
async def give_command(interaction: discord.Interaction,target: discord.Member, nick: str):
    dao = UserDao()
    cost = 1000
    user = dao.get_user(interaction.user.name)

    if user.currency >= cost:
        try:
            await target.edit(nick=nick)
            await interaction.response.send_message(f"🐏 {interaction.user.name} poly'd {target.name} into {nick} for 1000 Credits. 🐏")
            user.currency -= cost
            dao.update_user(user)
            logging.info(f'{user.name} used /polymorph on {target.name}')
        except Exception as e:
            logging.error(f'{user.name} tried to use /polymorph on {target.name} - {e}')
    else:
        await interaction.response.send_message(f"You're much too broke to polymorph anyone. <:PepePathetic:1200268253021360128>")




if __name__ == "__main__":
    bot.run(TOKEN)