from database import Database
from Entities.CoinflipEvent import CoinflipEvent
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

class CoinflipDao:
    def __init__(self):
        self.db = Database(db_host, db_user, db_password, db_name)

    def add_new_event(self, coinflip_event):
        sql = """
            INSERT INTO Coinflip (discord_id, guess, result, amount_won, amount_lost, timestamp) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (
            coinflip_event.discord_id,
            coinflip_event.guess,
            coinflip_event.result,
            coinflip_event.amount_won,
            coinflip_event.amount_lost,
            coinflip_event.timestamp
        )
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()

    def get_top_wins(self):
        sql = """
            SELECT discord_id, amount_won, timestamp
            FROM Coinflip
            WHERE amount_lost = 0
            ORDER BY amount_won DESC
            LIMIT 5
        """
        self.db.mycursor.execute(sql)
        top_wins = self.db.mycursor.fetchall()
        return top_wins
    
    def get_top_losses(self):
        sql = """
            SELECT discord_id, amount_lost, timestamp
            FROM Coinflip
            WHERE amount_won = 0
            ORDER BY amount_lost DESC
            LIMIT 5
        """
        self.db.mycursor.execute(sql)
        top_losses = self.db.mycursor.fetchall()
        return top_losses