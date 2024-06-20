from database import Database
from Entities.SlotEvent import SlotEvent
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

class SlotsDao:
    def __init__(self):
        self.db = Database(db_host, db_user, db_password, db_name)

    def add_new_event(self, slot_event):
        sql = """
            INSERT INTO Slots (discord_id, slot1, slot2, slot3, bet_amount, amount_won, amount_lost, timestamp) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            slot_event.discord_id,
            slot_event.slot1,
            slot_event.slot2,
            slot_event.slot3,
            slot_event.bet_amount,
            slot_event.amount_won,
            slot_event.amount_lost,
            slot_event.timestamp
        )
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()

    def get_slot_wins(self, discord_id):
        sql = """
            SELECT COUNT(*)
            FROM Slots
            WHERE discord_id = %s AND amount_won > 0
        """
        values = (discord_id,)
        self.db.mycursor.execute(sql, values)
        wins = self.db.mycursor.fetchone()
        return wins[0]
    
    def get_slot_losses(self, discord_id):
        sql = """
            SELECT COUNT(*)
            FROM Slots
            WHERE discord_id = %s AND amount_lost > 0
        """
        values = (discord_id,)
        self.db.mycursor.execute(sql, values)
        losses = self.db.mycursor.fetchone()
        return losses[0]
    
    def get_total_slots(self, discord_id):
        sql = """
            SELECT COUNT(*)
            FROM Slots
            WHERE discord_id = %s
        """
        values = (discord_id,)
        self.db.mycursor.execute(sql, values)
        total_slots = self.db.mycursor.fetchone()
        return total_slots[0]
    
    def get_total_won(self, discord_id):
        sql = """
            SELECT SUM(amount_won)
            FROM Slots
            WHERE discord_id = %s
        """
        values = (discord_id,)
        self.db.mycursor.execute(sql, values)
        total_won = self.db.mycursor.fetchone()
        return total_won[0]
    
    def get_total_lost(self, discord_id):
        sql = """
            SELECT SUM(amount_lost)
            FROM Slots
            WHERE discord_id = %s
        """
        values = (discord_id,)
        self.db.mycursor.execute(sql, values)
        total_lost = self.db.mycursor.fetchone()
        return total_lost[0]

    def get_top_wins(self):
        sql = """
            SELECT u.discord_username,
                s.amount_won AS largest_single_win,
                s.timestamp AS win_timestamp
            FROM Slots s
            JOIN Users u ON s.discord_id = u.id
            WHERE (u.id, s.amount_won) IN (
                SELECT u.id,
                    MAX(s1.amount_won) AS max_win
                FROM Slots s1
                JOIN Users u ON s1.discord_id = u.id
                GROUP BY u.id
            )
            ORDER BY largest_single_win DESC
            LIMIT 5;
            """
        self.db.mycursor.execute(sql)
        top_wins = self.db.mycursor.fetchall()
        return top_wins
    
    def get_top_losses(self):
        sql = """
            SELECT u.discord_username,
                s.amount_lost AS largest_single_loss,
                s.timestamp AS loss_timestamp
            FROM Slots s
            JOIN Users u ON s.discord_id = u.id
            WHERE (u.id, s.amount_lost) IN (
                SELECT u.id,
                    MAX(s1.amount_lost) AS max_loss
                FROM Slots s1
                JOIN Users u ON s1.discord_id = u.id
                GROUP BY u.id
            )
            ORDER BY largest_single_loss DESC
            LIMIT 5;
            """
        self.db.mycursor.execute(sql)
        top_losses = self.db.mycursor.fetchall()
        return top_losses

    def get_total_spins(self):
        sql = """
            SELECT COUNT(*)
            FROM Slots
        """
        self.db.mycursor.execute(sql)
        total_spins = self.db.mycursor.fetchone()
        return total_spins[0]