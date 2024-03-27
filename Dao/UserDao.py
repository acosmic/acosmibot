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
            id,
            discord_username,
            level,
            streak,
            exp,
            exp_gained,
            exp_lost,
            currency,
            messages_sent,
            reactions_sent,
            created,
            last_active,
            daily
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
                discord_username = %s,
                level = %s,
                streak = %s,
                exp = %s,
                exp_gained = %s,
                exp_lost = %s,
                currency = %s,
                messages_sent = %s,
                reactions_sent = %s,
                last_active = %s,
                daily = %s
            WHERE id = %s
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
        

    def reset_daily(self):
        sql = '''
            UPDATE Users
            SET daily = 0;
        '''
        self.db.mycursor.execute(sql)
        self.db.mydb.commit()
        

    def get_user(self, id):
        sql = '''
            SELECT *
            FROM Users
            WHERE id = %s
        '''
        values = (id,)
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
        
    def get_user_rank(self, id):
        rank_query = '''
            SELECT
                id,
                discord_username,
                level,
                streak,
                exp,
                exp_gained,
                exp_lost,
                currency,
                messages_sent,
                reactions_sent,
                created,
                last_active,
                daily,
                (SELECT COUNT(*) + 1 FROM Users u2 WHERE u2.exp > u1.exp) AS user_rank
            FROM Users u1
            WHERE id = %s;
        '''

        self.db.mycursor.execute(rank_query, (id,))
        user_data = self.db.mycursor.fetchone()

        if user_data:
            # User found, return the rank
            return user_data  # Assuming the last column is the user_rank
        else:
            # User not found
            return None
        
    def get_top_users(self, column, limit=5):
        sql = f'''
        SELECT id, discord_username, {column}
        FROM Users
        ORDER BY {column} DESC
        LIMIT {limit}
        '''
        self.db.mycursor.execute(sql)
        top_users = self.db.mycursor.fetchall()
        self.db.close_connection()
        return top_users
    
    # temporary - DO NOT KEEP
    # def update_user_id(self, discord_username, discord_id):
    #     sql = '''
    #         UPDATE Users
    #         SET id = %s
    #         WHERE discord_username = %s
    #     '''
    #     values = (discord_id, discord_username)
    #     self.db.mycursor.execute(sql, values)
    #     self.db.mydb.commit()
        
        