import pandas as pd
import json
from datetime import datetime

class ExcelHandler:
    def __init__(self):
        self.places_file = 'data/places.xlsx'
        self.users_file = 'data/users.xlsx'
        self.user_diaries_file = 'data/user_diaries.xlsx'
        self.browse_history_file = 'data/browse_history.xlsx'
        
        # 初始化所有Excel文件
        self._init_excel_files()
    
    def _init_excel_files(self):
        """初始化所有Excel文件，如果不存在则创建"""
        # 初始化地点表
        try:
            pd.read_excel(self.places_file)
        except FileNotFoundError:
            df = pd.DataFrame(columns=['ID', 'Place_Name', 'Place_Category', 'Country', 'City', 'Tags', 'Description', 'Rating', 'View_Count'])
            df.to_excel(self.places_file, index=False)
        
        # 初始化用户表（包含用户标签）
        try:
            pd.read_excel(self.users_file)
        except FileNotFoundError:
            df = pd.DataFrame(columns=['id', 'username', 'password', 'tags'])
            df.to_excel(self.users_file, index=False)
        
        # 初始化用户日记表
        try:
            pd.read_excel(self.user_diaries_file)
        except FileNotFoundError:
            df = pd.DataFrame(columns=['id', 'user_id', 'title', 'content', 'created_at'])
            df.to_excel(self.user_diaries_file, index=False)
        
        # 初始化浏览历史表
        try:
            pd.read_excel(self.browse_history_file)
        except FileNotFoundError:
            df = pd.DataFrame(columns=['id', 'user_id', 'place_name', 'view_time'])
            df.to_excel(self.browse_history_file, index=False)

    def get_recommended_places(self):
        """获取所有推荐地点"""
        try:
            df = pd.read_excel(self.places_file)
            return df.to_dict('records')
        except Exception as e:
            print(f"获取推荐地点时出错: {e}")
            return []

    def check_user_exists(self, username):
        """检查用户名是否已存在"""
        try:
            df = pd.read_excel(self.users_file)
            return any(df['username'] == username)
        except Exception as e:
            print(f"检查用户名时出错: {e}")
            return False

    def create_user(self, username, password):
        """创建新用户"""
        try:
            if self.check_user_exists(username):
                return False
            
            df = pd.read_excel(self.users_file)
            new_id = len(df) + 1
            new_user = pd.DataFrame({
                'id': [new_id],
                'username': [username],
                'password': [password],
                'tags': ['[]']  # 初始化为空JSON数组字符串
            })
            df = pd.concat([df, new_user], ignore_index=True)
            df.to_excel(self.users_file, index=False)
            return True
        except Exception as e:
            print(f"创建用户时出错: {e}")
            return False

    def check_user(self, username, password):
        """检查用户登录信息"""
        try:
            df = pd.read_excel(self.users_file)
            user = df[(df['username'] == username) & (df['password'] == password)]
            return not user.empty
        except Exception as e:
            print(f"检查用户时出错: {e}")
            return False

    def get_user_by_username(self, username):
        """通过用户名获取用户信息"""
        try:
            df = pd.read_excel(self.users_file)
            user = df[df['username'] == username]
            if not user.empty:
                user_dict = user.iloc[0].to_dict()
                # 将tags从字符串转换为列表
                user_dict['tags'] = json.loads(user_dict['tags'])
                return user_dict
            return None
        except Exception as e:
            print(f"获取用户信息时出错: {e}")
            return None

    def get_user_tags(self, user_id):
        """获取用户标签"""
        try:
            df = pd.read_excel(self.users_file)
            user = df[df['id'] == user_id]
            if not user.empty:
                tags = json.loads(user.iloc[0]['tags'])
                return tags
            return []
        except Exception as e:
            print(f"获取用户标签时出错: {e}")
            return []

    def add_user_tag(self, user_id, tag):
        """添加用户标签"""
        try:
            df = pd.read_excel(self.users_file)
            user_idx = df[df['id'] == user_id].index
            if len(user_idx) > 0:
                current_tags = json.loads(df.at[user_idx[0], 'tags'])
                if tag not in current_tags:
                    current_tags.append(tag)
                    df.at[user_idx[0], 'tags'] = json.dumps(current_tags)
                    df.to_excel(self.users_file, index=False)
            return True
        except Exception as e:
            print(f"添加用户标签时出错: {e}")
            return False

    def get_user_diaries(self, user_id):
        """获取用户日记"""
        try:
            df = pd.read_excel(self.user_diaries_file)
            diaries = df[df['user_id'] == user_id].sort_values('created_at', ascending=False)
            return diaries.to_dict('records')
        except Exception as e:
            print(f"获取用户日记时出错: {e}")
            return []

    def add_user_diary(self, user_id, title, content):
        """添加用户日记"""
        try:
            df = pd.read_excel(self.user_diaries_file)
            new_id = len(df) + 1
            new_diary = pd.DataFrame({
                'id': [new_id],
                'user_id': [user_id],
                'title': [title],
                'content': [content],
                'created_at': [datetime.now()]
            })
            df = pd.concat([df, new_diary], ignore_index=True)
            df.to_excel(self.user_diaries_file, index=False)
            return True
        except Exception as e:
            print(f"添加用户日记时出错: {e}")
            return False

    def get_browse_history(self, user_id):
        """获取浏览历史"""
        try:
            df = pd.read_excel(self.browse_history_file)
            history = df[df['user_id'] == user_id].sort_values('view_time', ascending=False).head(10)
            return history.to_dict('records')
        except Exception as e:
            print(f"获取浏览历史时出错: {e}")
            return []

    def add_browse_history(self, user_id, place_name):
        """添加浏览历史并更新地点浏览次数"""
        try:
            # 添加浏览历史
            df_history = pd.read_excel(self.browse_history_file)
            new_id = len(df_history) + 1
            new_history = pd.DataFrame({
                'id': [new_id],
                'user_id': [user_id],
                'place_name': [place_name],
                'view_time': [datetime.now()]
            })
            df_history = pd.concat([df_history, new_history], ignore_index=True)
            df_history.to_excel(self.browse_history_file, index=False)

            # 更新地点浏览次数
            df_places = pd.read_excel(self.places_file)
            place_idx = df_places[df_places['Place_Name'] == place_name].index
            if len(place_idx) > 0:
                if 'View_Count' not in df_places.columns:
                    df_places['View_Count'] = 0
                df_places.at[place_idx[0], 'View_Count'] = df_places.at[place_idx[0], 'View_Count'] + 1
                df_places.to_excel(self.places_file, index=False)
            
            return True
        except Exception as e:
            print(f"添加浏览历史时出错: {e}")
            return False

    def get_place_details(self, place_id):
        """获取地点详情"""
        try:
            df = pd.read_excel(self.places_file)
            place = df[df['ID'] == place_id]
            if not place.empty:
                return {
                    'name': place.iloc[0]['Place_Name'],
                    'category': place.iloc[0]['Place_Category'],
                    'country': place.iloc[0]['Country'],
                    'city': place.iloc[0]['City'],
                    'tags': place.iloc[0]['Tags'],
                    'description': place.iloc[0]['Description'],
                    'rating': place.iloc[0]['Rating'],
                    'view_count': place.iloc[0].get('View_Count', 0)
                }
            return None
        except Exception as e:
            print(f"获取地点详情时出错: {e}")
            return None
