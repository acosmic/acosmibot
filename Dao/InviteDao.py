from database import Database
from Entities.Invite import Invite
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

class InviteDao:
    def __init__(self):
        self.db = Database(db_host, db_user, db_password, db_name)

    def create_table(self):
        sql = """
            CREATE TABLE IF NOT EXISTS Invite (
                id INT AUTO_INCREMENT,
                guild_id BIGINT,
                inviter_id BIGINT,
                invitee_id BIGINT,
                code VARCHAR(255),
                timestamp DATETIME,
                PRIMARY KEY (id)
            )
        """
        self.db.mycursor.execute(sql)
    
    def add_new_invite(self, invite):
        sql = """
            INSERT INTO Invite (id, guild_id, inviter_id, invitee_id, code, timestamp) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (
            invite.id,
            invite.guild_id,
            invite.inviter_id,
            invite.invitee_id,
            invite.code,
            invite.timestamp
        )
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()

    def get_invites(self, guild_id):
        sql = """
            SELECT *
            FROM Invite
            WHERE guild_id = %s
        """
        values = (guild_id,)
        self.db.mycursor.execute(sql, values)
        invites = self.db.mycursor.fetchall()
        return [Invite(*invite) for invite in invites]
    
    def get_invite(self, code):
        sql = """
            SELECT *
            FROM Invite
            WHERE code = %s
        """
        values = (code,)
        self.db.mycursor.execute(sql, values)
        invite = self.db.mycursor.fetchone()
        return Invite(*invite) if invite else None
    
    def get_inviter(self, code):
        sql = """
            SELECT inviter_id
            FROM Invite
            WHERE code = %s
        """
        values = (code,)
        self.db.mycursor.execute(sql, values)
        inviter = self.db.mycursor.fetchone()
        return inviter[0] if inviter else None
    
    def get_invitee(self, code):
        sql = """
            SELECT invitee_id
            FROM Invite
            WHERE code = %s
        """
        values = (code,)
        self.db.mycursor.execute(sql, values)
        invitee = self.db.mycursor.fetchone()
        return invitee[0] if invitee else None
    