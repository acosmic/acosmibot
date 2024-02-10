from database import Database
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

class VaultDao:
    def __init__(self):
        self.db = Database(db_host, db_user, db_password, db_name)

    def get_currency(self):
        sql = 'SELECT currency FROM Vault WHERE name = %s'
        name = 'Vault'  # Replace 'Vault' with the actual name if needed
        
        self.db.mycursor.execute(sql, (name,))
        result = self.db.mycursor.fetchone()
        return result[0]
    
    def update_currency(self, new_currency):
        sql = 'UPDATE Vault SET currency = %s WHERE name = %s'
        name = 'Vault'  # Replace 'Vault' with the actual name if needed
        
        self.db.mycursor.execute(sql, (new_currency, name))
        self.db.mydb.commit()
        self.db.close_connection()