from database import Database
from Entities.LotteryParticipant import LotteryParticipant
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

class LotteryParticipantDao:
    def __init__(self):
        self.db = Database(db_host, db_user, db_password, db_name)

    def add_new_participant(self, lottery_participant):
        sql = """
            INSERT INTO LotteryParticipants (event_id, participant_id)
            VALUES (%s, %s)
        """
        values = (
            lottery_participant.event_id,
            lottery_participant.participant_id
        )
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()
        
    def get_participants(self, event_id):
        sql = """
            SELECT event_id, participant_id
            FROM LotteryParticipants
            WHERE event_id = %s
        """
        values = (event_id,)
        self.db.mycursor.execute(sql, values)
        participants = self.db.mycursor.fetchall()
        return [LotteryParticipant(participant[0], participant[1]) for participant in participants]
    
    def get_all_participants(self):
        sql = """
            SELECT event_id, participant_id
            FROM LotteryParticipants
        """
        self.db.mycursor.execute(sql)
        participants = self.db.mycursor.fetchall()
        return [LotteryParticipant(participant[0], participant[1]) for participant in participants]
    
    def get_participant(self, event_id, participant_id):
        sql = """
            SELECT event_id, participant_id
            FROM LotteryParticipants
            WHERE event_id = %s AND participant_id = %s
        """
        values = (event_id, participant_id)
        self.db.mycursor.execute(sql, values)
        participant = self.db.mycursor.fetchone()
        if participant:
            return LotteryParticipant(participant[0], participant[1])
        else:
            return None
        
    def remove_participant(self, event_id, participant_id):
        sql = """
            DELETE FROM LotteryParticipants
            WHERE event_id = %s AND participant_id = %s
        """
        values = (event_id, participant_id)
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()

    def remove_all_participants(self, event_id):
        sql = """
            DELETE FROM LotteryParticipants
            WHERE event_id = %s
        """
        values = (event_id,)
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()

    def remove_all_participants_by_participant_id(self, participant_id):
        sql = """
            DELETE FROM LotteryParticipants
            WHERE participant_id = %s
        """
        values = (participant_id,)
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()

    def remove_all_participants_by_event_id(self, event_id):
        sql = """
            DELETE FROM LotteryParticipants
            WHERE event_id = %s
        """
        values = (event_id,)
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()


    def close_connection(self):
        self.db.close_connection()
