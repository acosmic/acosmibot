import mysql.connector

class Database:
    def __init__(self, db_host, db_user, db_password, db_name):
        self.mydb = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name
        )
        self.mycursor = self.mydb.cursor()

    
    def close_connection(self):
        if self.mydb.is_connected():
            self.mycursor.close()
            self.mydb.close()
            print("Database connection closed.")




    







  