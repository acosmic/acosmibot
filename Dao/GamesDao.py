from database import Database
from Entities.User import User
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

class GamesDao:
    def __init__(self):
        self.db = Database(db_host, db_user, db_password, db_name)
    
    def check_game_inprogress(self, game_name):
        query = "SELECT inprogress FROM Games WHERE name = %s;"
        values = (game_name,)
        self.db.mycursor.execute(query, values)
        result = self.db.mycursor.fetchone()
        if result and result[0] == 1:  # Check if result is not None before accessing the value
            return True
        else:
            return False
        
    def set_game_inprogress(self, game_name, int):
        query = "UPDATE Games SET inprogress = %s WHERE name = %s"
        values = (int, game_name)
        self.db.mycursor.execute(query, values)
        self.db.mydb.commit()
        self.db.close_connection()
