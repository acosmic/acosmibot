import os
import mysql.connector


class Database:
    def __init__(self, db_host=None, db_user=None, db_password=None, db_name=None, use_test_db=False):
        if use_test_db:
            self.db_host = db_host or os.getenv('test_db_host')
            self.db_user = db_user or os.getenv('test_db_user')
            self.db_password = db_password or os.getenv('test_db_password')
            self.db_name = db_name or os.getenv('test_db_name')
        else:
            self.db_host = db_host or os.getenv('db_host')
            self.db_user = db_user or os.getenv('db_user')
            self.db_password = db_password or os.getenv('db_password')
            self.db_name = db_name or os.getenv('db_name')
        
        
        self.mydb = mysql.connector.connect(
            host=self.db_host,
            user=self.db_user,
            password=self.db_password,
            database=self.db_name
        )
        self.mycursor = self.mydb.cursor()

    def close_connection(self):
        if self.mydb.is_connected():
            self.mycursor.close()
            self.mydb.close()
            print("Database connection closed.")

