from database import Database
from Entities.LotteryEvent import LotteryEvent
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

class LotteryEventDao:
    def __init__(self):
        self.db = Database(db_host, db_user, db_password, db_name)

    def add_new_event(self, lottery_event):
        sql = """
            INSERT INTO LotteryEvents (id, message_id, start_time, end_time, credits, winner_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (
            lottery_event.id,
            lottery_event.message_id,
            lottery_event.start_time,
            lottery_event.end_time,
            lottery_event.credits,
            lottery_event.winner_id
        )
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()

    def get_current_event(self):
        sql = """
            SELECT id, message_id, start_time, end_time, credits, winner_id
            FROM LotteryEvents
            WHERE end_time > NOW()
            ORDER BY start_time DESC
            LIMIT 1
        """
        self.db.mycursor.execute(sql)
        current_event = self.db.mycursor.fetchone()
        if current_event:
            return LotteryEvent(current_event[0], current_event[1], current_event[2], current_event[3], current_event[4], current_event[5])
        else:
            return None
        
    def get_past_events(self):
        sql = """
            SELECT id, message_id, start_time, end_time, credits, winner_id
            FROM LotteryEvents
            WHERE end_time < NOW()
            ORDER BY start_time DESC
            LIMIT 5
        """
        self.db.mycursor.execute(sql)
        past_events = self.db.mycursor.fetchall()
        return [LotteryEvent(event[0], event[1], event[2], event[3], event[4], event[5]) for event in past_events]
    
    def get_all_events(self):
        sql = """
            SELECT id, message_id, start_time, end_time, credits, winner_id
            FROM LotteryEvents
            ORDER BY start_time DESC
        """
        self.db.mycursor.execute(sql)
        all_events = self.db.mycursor.fetchall()
        return [LotteryEvent(event[0], event[1], event[2], event[3], event[4], event[5]) for event in all_events]
    
    def get_event_by_id(self, id):
        sql = """
            SELECT id, message_id, start_time, end_time, credits, winner_id
            FROM LotteryEvents
            WHERE id = %s
        """
        values = (id,)
        self.db.mycursor.execute(sql, values)
        event = self.db.mycursor.fetchone()
        if event:
            return LotteryEvent(event[0], event[1], event[2], event[3], event[4], event[5])
        else:
            return None
        
    def update_event(self, lottery_event):
        sql = """
            UPDATE LotteryEvents
            SET message_id = %s, start_time = %s, end_time = %s, credits = %s, winner_id = %s
            WHERE id = %s
        """
        values = (
            lottery_event.message_id,
            lottery_event.start_time,
            lottery_event.end_time,
            lottery_event.credits,
            lottery_event.winner_id,
            lottery_event.id
        )
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()

    def delete_event(self, id):
        sql = """
            DELETE FROM LotteryEvents
            WHERE id = %s
        """
        values = (id,)
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()

    def get_total_credits(self):
        sql = """
            SELECT SUM(credits) AS total_credits
            FROM LotteryEvents
        """
        self.db.mycursor.execute(sql)
        total_credits = self.db.mycursor.fetchone()
        return total_credits[0]
    
    def close_connection(self):
        self.db.close_connection()

