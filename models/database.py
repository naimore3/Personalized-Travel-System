# database.py
import mysql.connector
from config import DB_CONFIG

class Database:
    def __init__(self):
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor()
        except mysql.connector.Error as err:
            print(f"数据库连接错误: {err}")

    def __del__(self):
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()

    def get_recommended_places(self):
        try:
            # 这里假设你有一个名为 places 的表，根据实际情况修改 SQL 查询语句
            query = "SELECT * FROM places"
            self.cursor.execute(query)
            places = self.cursor.fetchall()
            return places
        except mysql.connector.Error as err:
            print(f"查询推荐地点时出错: {err}")
            return []