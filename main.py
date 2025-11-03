#! /usr/bin/python3.10
import os
from dotenv import load_dotenv
from bot import Bot

load_dotenv()
bot = Bot()

if __name__ == "__main__":
    bot.run(os.getenv('TOKEN'))
