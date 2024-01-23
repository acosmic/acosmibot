import mysql.connector
from Entities.User import User

class Database:
    def __init__(self, db_host, db_user, db_password, db_name):
        self.mydb = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name
        )
        self.mycursor = self.mydb.cursor()

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
                MESSAGES_SENT,
                REACTIONS_SENT,
                CREATED,
                LAST_ACTIVE,
                (SELECT COUNT(*) + 1 FROM Users u2 WHERE u2.EXP > u1.EXP) AS user_rank
            FROM Users u1
            WHERE DISCORD_USERNAME = %s;
        '''

        self.mycursor.execute(rank_query, (discord_username,))
        user_data = self.mycursor.fetchone()

        if user_data:
            # User found, return the rank
            return user_data  # Assuming the last column is the user_rank
        else:
            # User not found
            return None
    
    def add_new_user(self, new_user):
        sql = '''
        INSERT INTO Users (
            ID,
            DISCORD_USERNAME,
            LEVEL,
            STREAK,
            EXP,
            EXP_GAINED,
            EXP_LOST,
            MESSAGES_SENT,
            REACTIONS_SENT,
            CREATED,
            LAST_ACTIVE
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
        values = (
            new_user.id,
            new_user.discord_username,
            new_user.level,
            new_user.streak,
            new_user.exp,
            new_user.exp_gained,
            new_user.exp_lost,
            new_user.messages_sent,
            new_user.reactions_sent,
            new_user.created,
            new_user.last_active
        )

        self.mycursor.execute(sql, values)
        self.mydb.commit()
        self.close_connection()

    def modify_user(self, updated_user):
        sql = '''
            UPDATE Users
            SET
                DISCORD_USERNAME = %s,
                LEVEL = %s,
                STREAK = %s,
                EXP = %s,
                EXP_GAINED = %s,
                EXP_LOST = %s,
                MESSAGES_SENT = %s,
                REACTIONS_SENT = %s,
                LAST_ACTIVE = %s
            WHERE ID = %s
        '''
        values = (
            updated_user.discord_username,
            updated_user.level,
            updated_user.streak,
            updated_user.exp,
            updated_user.exp_gained,
            updated_user.exp_lost,
            updated_user.messages_sent,
            updated_user.reactions_sent,
            updated_user.last_active,
            updated_user.id
        )

        self.mycursor.execute(sql, values)
        self.mydb.commit()
        self.close_connection()

    def get_user(self, discord_username):
        sql = '''
            SELECT *
            FROM Users
            WHERE DISCORD_USERNAME = %s
        '''

        values = (discord_username,)

        self.mycursor.execute(sql, values)
        user_data = self.mycursor.fetchone()

        if user_data:
            # Assuming you have a User class, create an instance and populate its attributes
            user = User(
                id=user_data[0],
                discord_username=user_data[1],
                level=user_data[2],
                streak=user_data[3],
                exp=user_data[4],
                exp_gained=user_data[5],
                exp_lost=user_data[6],
                messages_sent=user_data[7],
                reactions_sent=user_data[8],
                created=user_data[9],
                last_active=user_data[10]
            )
            return user
        else:
            return None

    
    def close_connection(self):
        if self.mydb.is_connected():
            self.mycursor.close()
            self.mydb.close()
            print("Database connection closed.")




    




  # sql ='''CREATE TABLE IF NOT EXISTS USER(
  #    ID INT NOT NULL AUTO_INCREMENT,
  #    DISCORD_USERNAME VARCHAR(255) NOT NULL,
  #    LEVEL INT,
  #    STREAK INT,
  #    EXP INT,
  #    EXP_GAINED INT,
  #    EXP_LOST INT,
  #    CREATED DATETIME,
  #    LAST_ACTIVE DATETIME,
  #    PRIMARY KEY (ID)
  # )'''


  