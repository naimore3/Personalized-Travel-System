import mysql.connector

class Database:
    def __init__(self):
        self.conn = mysql.connector.connect(
            host="localhost",
            user="your_username",
            password="your_password",
            database="travel_db"
        )
        self.cursor = self.conn.cursor()

    def get_recommended_places(self):
        query = "SELECT * FROM places ORDER BY rating DESC"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_place_details(self, place_id):
        query = "SELECT * FROM places WHERE id = %s"
        self.cursor.execute(query, (place_id,))
        return self.cursor.fetchone()

    def add_punch_record(self, place, picture, title, content):
        query = "INSERT INTO punch_records (place, picture, title, content) VALUES (%s, %s, %s, %s)"
        self.cursor.execute(query, (place, picture, title, content))
        self.conn.commit()
    