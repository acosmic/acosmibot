from database import Database
from Entities.User import User
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

class UserDao:
    def __init__(self):
        self.db = Database(db_host, db_user, db_password, db_name)
    
    def add_user(self, new_user):
        sql = '''
        INSERT INTO Users (
            ID,
            DISCORD_USERNAME,
            LEVEL,
            STREAK,
            EXP,
            EXP_GAINED,
            EXP_LOST,
            CURRENCY,
            MESSAGES_SENT,
            REACTIONS_SENT,
            CREATED,
            LAST_ACTIVE,
            DAILY
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
        values = (
            new_user.id,
            new_user.discord_username,
            new_user.level,
            new_user.streak,
            new_user.exp,
            new_user.exp_gained,
            new_user.exp_lost,
            new_user.currency,
            new_user.messages_sent,
            new_user.reactions_sent,
            new_user.created,
            new_user.last_active,
            new_user.daily
        )

        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()
        self.db.close_connection()

    def update_user(self, updated_user):
        sql = '''
            UPDATE Users
            SET
                DISCORD_USERNAME = %s,
                LEVEL = %s,
                STREAK = %s,
                EXP = %s,
                EXP_GAINED = %s,
                EXP_LOST = %s,
                CURRENCY = %s,
                MESSAGES_SENT = %s,
                REACTIONS_SENT = %s,
                LAST_ACTIVE = %s,
                DAILY = %s
            WHERE ID = %s
        '''
        values = (
            updated_user.discord_username,
            updated_user.level,
            updated_user.streak,
            updated_user.exp,
            updated_user.exp_gained,
            updated_user.exp_lost,
            updated_user.currency,
            updated_user.messages_sent,
            updated_user.reactions_sent,
            updated_user.last_active,
            updated_user.daily,
            updated_user.id,
        )
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()
        self.db.close_connection()

    def get_user(self, discord_username):
        sql = '''
            SELECT *
            FROM Users
            WHERE DISCORD_USERNAME = %s
        '''
        values = (discord_username,)
        self.db.mycursor.execute(sql, values)
        user_data = self.db.mycursor.fetchone()
        if user_data:
            user = User(
                id=user_data[0],
                discord_username=user_data[1],
                level=user_data[2],
                streak=user_data[3],
                exp=user_data[4],
                exp_gained=user_data[5],
                exp_lost=user_data[6],
                currency=user_data[7],
                messages_sent=user_data[8],
                reactions_sent=user_data[9],
                created=user_data[10],
                last_active=user_data[11],
                daily=user_data[12]
            )
            return user
        else:
            return None
        
    def get_user_rank(self, discord_username):
        rank_query = '''
            SELECT
                ID,
                DISCORD_USERNAME,
                LEVEL,
                STREAK,
                EXP,
                EXP_GAINED,
                EXP_LOST,
                CURRENCY,
                MESSAGES_SENT,
                REACTIONS_SENT,
                CREATED,
                LAST_ACTIVE,
                DAILY,
                (SELECT COUNT(*) + 1 FROM Users u2 WHERE u2.EXP > u1.EXP) AS user_rank
            FROM Users u1
            WHERE DISCORD_USERNAME = %s;
        '''

        self.db.mycursor.execute(rank_query, (discord_username,))
        user_data = self.db.mycursor.fetchone()

        if user_data:
            # User found, return the rank
            return user_data  # Assuming the last column is the user_rank
        else:
            # User not found
            return None
        
    def get_top_users(self, column, limit=5):
        sql = f'''
        SELECT ID, DISCORD_USERNAME, {column}
        FROM Users
        ORDER BY {column} DESC
        LIMIT {limit}
        '''
        self.db.mycursor.execute(sql)
        top_users = self.db.mycursor.fetchall()
        self.db.close_connection()
        return top_users
        
        