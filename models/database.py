import mysql.connector
from config import DB_CONFIG

class Database:
    def __init__(self):
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor()
            # 创建用户表
            create_user_table_query = """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )
            """
            self.cursor.execute(create_user_table_query)
            # 创建地点表
            create_places_table_query = """
            CREATE TABLE IF NOT EXISTS places (
                ID INT AUTO_INCREMENT PRIMARY KEY,
                Place_Name VARCHAR(255),
                Place_Category VARCHAR(50),
                City VARCHAR(255),
                Tags JSON,
                Description TEXT,
                Rating FLOAT
            )
            """
            self.cursor.execute(create_places_table_query)
            self.conn.commit()
        except mysql.connector.Error as err:
            print(f"数据库连接错误: {err}")

    def __del__(self):
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()

    def get_recommended_places(self):
        try:
            # 查询 places 表
            query = "SELECT * FROM places"
            self.cursor.execute(query)
            places = self.cursor.fetchall()
            return places
        except mysql.connector.Error as err:
            print(f"查询推荐地点时出错: {err}")
            return []

    def register_user(self, username, password):
        try:
            query = "INSERT INTO users (username, password) VALUES (%s, %s)"
            self.cursor.execute(query, (username, password))
            self.conn.commit()
            return True
        except mysql.connector.Error as err:
            print(f"注册用户时出错: {err}")
            return False

    def check_user(self, username, password):
        try:
            query = "SELECT * FROM users WHERE username = %s AND password = %s"
            self.cursor.execute(query, (username, password))
            user = self.cursor.fetchone()
            return user is not None
        except mysql.connector.Error as err:
            print(f"检查用户时出错: {err}")
            return False

    def get_place_details(self, place_id):
        try:
            query = "SELECT Place_Name, Description, Rating FROM places WHERE ID = %s"
            self.cursor.execute(query, (place_id,))
            place = self.cursor.fetchone()
            if place:
                return {
                    'name': place[0],
                    'description': place[1],
                    'rating': place[2]
                }
            return None
        except mysql.connector.Error as err:
            print(f"查询地点详情时出错: {err}")
            return None