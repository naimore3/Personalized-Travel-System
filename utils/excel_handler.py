import pandas as pd
import json
from datetime import datetime
import os
import struct
import base64
from collections import defaultdict

class ExcelHandler:
    def __init__(self):
        self.places_file = 'data/places.xlsx'
        self.users_file = 'data/users.xlsx'
        self.user_diaries_file = 'data/user_diaries.xlsx'
        self.browse_history_file = 'data/browse_history.xlsx'
        self.compression_threshold = 100  # 压缩阈值
        self.compression_marker = "COMPRESSED:"  # 压缩标记
        self.dict_size = 4096  # 字典大小
        
        # 初始化所有Excel文件
        self._init_excel_files()
    
    def _init_excel_files(self):
        """初始化所有Excel文件，如果不存在则创建"""
        # 初始化地点表
        try:
            df_places = pd.read_excel(self.places_file)
            if 'View_Count' not in df_places.columns:
                df_places['View_Count'] = 0
            else:
                # 确保 View_Count 是整数类型，无法转换的填充为0
                df_places['View_Count'] = pd.to_numeric(df_places['View_Count'], errors='coerce').fillna(0).astype(int)
            df_places.to_excel(self.places_file, index=False)
        except FileNotFoundError:
            df = pd.DataFrame(columns=['ID', 'Place_Name', 'Place_Category', 'Country', 'City', 'Tags', 'Description', 'Rating', 'View_Count', 'Picture'])
            df['View_Count'] = 0 #确保新创建的文件也有初始化的View_Count
            df['Picture'] = ''  # 确保新创建的文件也有初始化的Picture
            df.to_excel(self.places_file, index=False)
        except Exception as e:
            print(f"Error initializing places file {self.places_file}: {e}")
        
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
            df = pd.DataFrame(columns=['id', 'user_id', 'title', 'content', 'picture', 'created_at', 'username', 'place', 'views', 'rating', 'video_url', 'video_status'])
            df['views'] = 0
            df['rating'] = 0
            df['video_status'] = 'pending'  # pending, processing, completed, failed
            df.to_excel(self.user_diaries_file, index=False)
        
        # 初始化浏览历史表
        try:
            pd.read_excel(self.browse_history_file)
        except FileNotFoundError:
            df = pd.DataFrame(columns=['id', 'user_id', 'place_name', 'view_time'])
            df.to_excel(self.browse_history_file, index=False)
        
        # 初始化日记评分表
        try:
            pd.read_excel('data/diary_ratings.xlsx')
        except FileNotFoundError:
            df = pd.DataFrame(columns=['id', 'diary_id', 'user_id', 'rating', 'created_at'])
            df.to_excel('data/diary_ratings.xlsx', index=False)

    def get_recommended_places(self):
        """获取所有推荐地点"""
        try:
            df = pd.read_excel(self.places_file)
            # 确保 View_Count 列存在且为整数
            if 'View_Count' not in df.columns:
                df['View_Count'] = 0
            else:
                df['View_Count'] = pd.to_numeric(df['View_Count'], errors='coerce').fillna(0).astype(int)
            return df.to_dict('records')
        except Exception as e:
            print(f"获取推荐地点时出错: {e}")
            return []

    def check_user_exists(self, username):
        """检查用户名是否已存在"""
        try:
            if not os.path.exists(self.users_file):
                print(f"用户文件不存在: {self.users_file}")
                return False
            
            df = pd.read_excel(self.users_file)
            if 'username' not in df.columns:
                print("用户文件中缺少username列")
                return False
            
            return any(df['username'] == username)
        except Exception as e:
            print(f"检查用户名时出错: {e}")
            return False

    def create_user(self, username, password):
        """创建新用户"""
        try:
            username = username.strip()
            password = password.strip()
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
            username = username.strip()
            password = password.strip()
            if not os.path.exists(self.users_file):
                print(f"用户文件不存在: {self.users_file}")
                return False
            
            df = pd.read_excel(self.users_file)
            if 'username' not in df.columns or 'password' not in df.columns:
                print("用户文件中缺少必要的列")
                return False
            
            user = df[(df['username'].astype(str).str.strip() == username) & (df['password'].astype(str).str.strip() == password)]
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

    def get_all_diaries(self):
        """获取所有用户的日记"""
        try:
            if not os.path.exists(self.user_diaries_file):
                print(f"日记文件不存在: {self.user_diaries_file}")
                return []
                
            df = pd.read_excel(self.user_diaries_file)
            if df.empty:
                print("日记文件为空")
                return []
            
            # 解压所有日记内容
            diaries = df.sort_values('created_at', ascending=False)
            diary_list = diaries.to_dict('records')
            for diary in diary_list:
                diary['content'] = self._decompress_content(diary['content'])
            return diary_list
        except Exception as e:
            print(f"获取所有日记时出错: {e}")
            import traceback
            print(traceback.format_exc())
            return []

    def get_user_diaries(self, user_id):
        """获取指定用户的日记"""
        try:
            df = pd.read_excel(self.user_diaries_file)
            diaries = df[df['user_id'] == user_id].sort_values('created_at', ascending=False)
            diary_list = diaries.to_dict('records')
            # 解压所有日记内容
            for diary in diary_list:
                diary['content'] = self._decompress_content(diary['content'])
            return diary_list
        except Exception as e:
            print(f"获取用户日记时出错: {e}")
            return []

    def build_dictionary(self, text):
        """构建高频字符字典"""
        freq = defaultdict(int)
        for char in text:
            freq[char] += 1
        # 按频率排序，取前dict_size个字符
        sorted_chars = sorted(freq.items(), key=lambda x: -x[1])
        dictionary = [char for char, count in sorted_chars[:self.dict_size]]
        return dictionary

    def _compress_content(self, content):
        """使用字典压缩算法压缩日记内容"""
        print(f"开始压缩内容，原始长度: {len(content)}")
        if len(content) < self.compression_threshold:
            print(f"内容长度小于阈值 {self.compression_threshold}，不进行压缩")
            return content
            
        try:
            # 构建字典
            dictionary = self.build_dictionary(content)
            
            # 创建字符到编码的映射
            char_to_code = {char: idx for idx, char in enumerate(dictionary)}
            
            compressed = []
            for char in content:
                if char in char_to_code:
                    # 如果在字典中，使用2字节编码（0-65535）
                    compressed.append(char_to_code[char].to_bytes(2, 'big'))
                else:
                    # 如果不在字典中，使用3字节标记（0xFF + 原始UTF-8字节）
                    compressed.append(b'\xff' + char.encode('utf-8'))
            
            # 将压缩数据转换为base64字符串
            compressed_data = b''.join(compressed)
            compressed_base64 = base64.b64encode(compressed_data).decode('ascii')
            
            # 将字典和压缩数据一起存储
            result = {
                'dict': dictionary,
                'data': compressed_base64  # 存储base64字符串而不是二进制数据
            }
            compressed_str = f"{self.compression_marker}{base64.b64encode(json.dumps(result).encode('utf-8')).decode('ascii')}"
            print(f"压缩完成，压缩后长度: {len(compressed_str)}")
            return compressed_str
        except Exception as e:
            print(f"压缩内容时出错: {e}")
            import traceback
            print(traceback.format_exc())
            return content

    def _decompress_content(self, content):
        """解压字典压缩的内容"""
        print(f"开始解压内容，内容前100个字符: {content[:100]}")
        if not content.startswith(self.compression_marker):
            print("内容未压缩，直接返回")
            return content
            
        try:
            # 解码base64和JSON
            decoded = json.loads(base64.b64decode(content[len(self.compression_marker):].encode('ascii')).decode('utf-8'))
            dictionary = decoded['dict']
            compressed_base64 = decoded['data']
            
            # 解码压缩数据
            data = base64.b64decode(compressed_base64)
            
            # 创建编码到字符的映射
            code_to_char = {idx: char for idx, char in enumerate(dictionary)}
            
            decompressed = []
            i = 0
            while i < len(data):
                if data[i] != 0xff:
                    # 读取2字节编码
                    code = int.from_bytes(data[i:i+2], 'big')
                    decompressed.append(code_to_char[code])
                    i += 2
                else:
                    # 读取原始UTF-8字符
                    char_bytes = data[i+1:i+4]  # UTF-8中文通常3字节
                    decompressed.append(char_bytes.decode('utf-8'))
                    i += 1 + len(char_bytes)
            
            result = ''.join(decompressed)
            print(f"解压完成，解压后长度: {len(result)}")
            return result
        except Exception as e:
            print(f"解压内容时出错: {e}")
            import traceback
            print(traceback.format_exc())
            return content

    def add_user_diary(self, user_id, title, content, user_username, picture_path=None, place_id=None):
        try:
            print(f"Attempting to save diary: user_id={user_id}, title={title}, content={content}, picture={picture_path}, place_id={place_id}, username={user_username}")
            
            # 验证输入
            if not content or not isinstance(content, str):
                print("错误：日记内容为空或不是字符串类型")
                return False
                
            if not title or not isinstance(title, str):
                print("错误：日记标题为空或不是字符串类型")
                return False
            
            # 压缩内容
            print("开始压缩日记内容...")
            compressed_content = self._compress_content(content)
            print(f"压缩后的内容前100个字符: {compressed_content[:100]}")
            
            # 确保data目录存在
            os.makedirs('data', exist_ok=True)
            
            # 检查文件是否存在
            if not os.path.exists(self.user_diaries_file):
                print(f"Diary file not found: {self.user_diaries_file}")
                df = pd.DataFrame(columns=['id', 'user_id', 'title', 'content', 'picture', 'created_at', 'username', 'place', 'views', 'rating'])
                df['views'] = 0
                df['rating'] = 0
                df.to_excel(self.user_diaries_file, index=False)
            else:
                df = pd.read_excel(self.user_diaries_file)
            
            # 检查必要的列是否存在
            required_columns = ['id', 'user_id', 'title', 'content', 'picture', 'created_at', 'username', 'place', 'views', 'rating']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                print(f"Missing columns in diary file: {missing_columns}")
                for col in missing_columns:
                    df[col] = None
            
            new_id = len(df) + 1
            
            # 处理图片路径，移除 'static/' 前缀
            if picture_path and picture_path.startswith('static/'):
                picture_path = picture_path[7:]
            
            new_diary = pd.DataFrame({
                'id': [new_id],
                'user_id': [user_id],
                'title': [title],
                'content': [compressed_content],  # 存储压缩后的内容
                'picture': [picture_path],
                'created_at': [datetime.now()],
                'username': [user_username],
                'place': [place_id],
                'views': [0],
                'rating': [0.0]
            })
            
            print("正在保存日记到Excel文件...")
            df = pd.concat([df, new_diary], ignore_index=True)
            df.to_excel(self.user_diaries_file, index=False)
            print("Diary saved successfully")
            return True
            
        except Exception as e:
            print(f"Error saving diary: {str(e)}")
            import traceback
            print(traceback.format_exc())
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
        """添加浏览历史（如果已存在则增加计数）并更新地点总浏览次数"""
        try:
            df_history = pd.read_excel(self.browse_history_file)
            
            # 确保 user_id 和 place_name 列存在且类型正确以便比较
            if 'user_id' not in df_history.columns:
                df_history['user_id'] = None
            if 'place_name' not in df_history.columns:
                df_history['place_name'] = None
            
            # 将user_id转换为与Excel中一致的类型，通常是int或str
            # 假设excel中的user_id是整数，如果不是，需要相应调整
            try:
                current_user_id = int(user_id)
                df_history['user_id'] = pd.to_numeric(df_history['user_id'], errors='coerce').fillna(-1).astype(int)
            except ValueError: # 如果user_id不能转为int，则按字符串处理
                current_user_id = str(user_id)
                df_history['user_id'] = df_history['user_id'].astype(str)

            df_history['place_name'] = df_history['place_name'].astype(str)
            current_place_name = str(place_name)

            # 查找现有记录
            existing_record_idx = df_history[(df_history['user_id'] == current_user_id) & (df_history['place_name'] == current_place_name)].index

            if not existing_record_idx.empty:
                # 记录已存在，增加 user_specific_view_count
                idx_to_update = existing_record_idx[0]
                if 'user_specific_view_count' not in df_history.columns: # 确保列存在
                    df_history['user_specific_view_count'] = 0
                
                # 确保 user_specific_view_count 列是数值类型
                df_history['user_specific_view_count'] = pd.to_numeric(df_history['user_specific_view_count'], errors='coerce').fillna(0).astype(int)
                df_history.at[idx_to_update, 'user_specific_view_count'] += 1
            else:
                # 记录不存在，添加新记录
                new_id = len(df_history) + 1 if not df_history.empty else 1
                new_history_record = pd.DataFrame({
                    'id': [new_id],
                    'user_id': [current_user_id],
                    'place_name': [current_place_name],
                    'user_specific_view_count': [1] 
                })
                df_history = pd.concat([df_history, new_history_record], ignore_index=True)
            
            df_history.to_excel(self.browse_history_file, index=False)

            # 更新地点总浏览次数 (View_Count in places.xlsx)
            # 这部分逻辑保持不变，因为每次调用此函数都代表一次新的查看行为
            df_places = pd.read_excel(self.places_file)
            # 确保 Place_Name 列类型一致
            df_places['Place_Name'] = df_places['Place_Name'].astype(str)
            place_idx = df_places[df_places['Place_Name'] == current_place_name].index
            if len(place_idx) > 0:
                idx_to_update_place = place_idx[0]
                if 'View_Count' not in df_places.columns:
                    df_places['View_Count'] = 0
                
                # 确保 View_Count 列是数值类型
                df_places['View_Count'] = pd.to_numeric(df_places['View_Count'], errors='coerce').fillna(0).astype(int)
                df_places.at[idx_to_update_place, 'View_Count'] += 1
                df_places.to_excel(self.places_file, index=False)
            
            return True
        except Exception as e:
            print(f"添加浏览历史或更新计数时出错: {e}")
            return False


    def get_place_details(self, place_id):
        """获取指定地点的详细信息"""
        try:
            df = pd.read_excel(self.places_file)
            # 确保 View_Count 列存在且为整数
            if 'View_Count' not in df.columns:
                df['View_Count'] = 0
            else:
                df['View_Count'] = pd.to_numeric(df['View_Count'], errors='coerce').fillna(0).astype(int)

            place_series = df[df['ID'] == place_id]
            if not place_series.empty:
                place_dict = place_series.iloc[0].to_dict()
                # 确保从字典中获取的View_Count也是整数
                place_dict['View_Count'] = int(place_dict.get('View_Count', 0))
                return place_dict
            return None
        except Exception as e:
            print(f"获取地点详情时出错: {e}")
            return None

    def get_places(self):
        """
        Get all places from places.xlsx
        Returns:
            list: List of places with their details
        """
        try:
            df = pd.read_excel(self.places_file)
            return df.to_dict('records')
        except Exception as e:
            print(f"Error reading places: {e}")
            return []

    def get_diary_by_id(self, diary_id):
        """获取指定ID的日记"""
        try:
            print(f"正在获取日记ID: {diary_id}")
            df = pd.read_excel(self.user_diaries_file)
            # 确保 id 字段为 int 类型
            df['id'] = df['id'].astype(int)
            diary = df[df['id'] == int(diary_id)]
            if not diary.empty:
                diary_dict = diary.iloc[0].to_dict()
                #diary_dict['picture'] = 
                # 解压内容
                diary_dict['content'] = self._decompress_content(diary_dict['content'])
                
                # 根据地点名称获取地点ID
                try:
                    if diary_dict.get('place'):
                        place_name = diary_dict['place']
                        place_df = pd.read_excel(self.places_file)
                        place = place_df[place_df['Place_Name'] == place_name]
                        if not place.empty:
                            diary_dict['place_id'] = place.iloc[0]['ID']
                except Exception as e:
                    print(f"获取地点ID时出错: {e}")
                    diary_dict['place_id'] = None
                
                print(f"成功获取日记内容: ID={diary_dict['id']}, 标题={diary_dict['title']}")
                print(f"内容预览: {diary_dict['content'][:100]}...")
                print(f"图片路径: {diary_dict['picture']}")
                return diary_dict
            print(f"未找到ID为{diary_id}的日记")
            return None
        except Exception as e:
            print(f"获取日记详情时出错: {e}")
            import traceback
            print(traceback.format_exc())
            return None

    def increment_diary_views(self, diary_id):
        """增加日记浏览量"""
        try:
            df = pd.read_excel(self.user_diaries_file)
            diary_idx = df[df['id'] == diary_id].index
            if len(diary_idx) > 0:
                if 'views' not in df.columns:
                    df['views'] = 0
                df.at[diary_idx[0], 'views'] = df.at[diary_idx[0], 'views'] + 1
                df.to_excel(self.user_diaries_file, index=False)
                return True
            return False
        except Exception as e:
            print(f"增加日记浏览量时出错: {e}")
            return False

    def rate_diary(self, diary_id, user_id, rating):
        """对日记进行评分"""
        try:
            # 检查评分是否在有效范围内
            if not (0 <= rating <= 5):
                return False, "评分必须在0-5之间"

            # 检查用户是否已经评分过
            df_ratings = pd.read_excel('data/diary_ratings.xlsx')
            existing_rating = df_ratings[(df_ratings['diary_id'] == diary_id) & (df_ratings['user_id'] == user_id)]
            
            if not existing_rating.empty:
                # 更新已有评分
                df_ratings.at[existing_rating.index[0], 'rating'] = rating
                df_ratings.at[existing_rating.index[0], 'created_at'] = datetime.now()
            else:
                # 添加新评分
                new_id = len(df_ratings) + 1
                new_rating = pd.DataFrame({
                    'id': [new_id],
                    'diary_id': [diary_id],
                    'user_id': [user_id],
                    'rating': [rating],
                    'created_at': [datetime.now()]
                })
                df_ratings = pd.concat([df_ratings, new_rating], ignore_index=True)
            
            df_ratings.to_excel('data/diary_ratings.xlsx', index=False)

            # 更新日记的平均评分
            df_diaries = pd.read_excel(self.user_diaries_file)
            diary_idx = df_diaries[df_diaries['id'] == diary_id].index
            if len(diary_idx) > 0:
                avg_rating = df_ratings[df_ratings['diary_id'] == diary_id]['rating'].mean()
                df_diaries.at[diary_idx[0], 'rating'] = round(avg_rating, 1)
                df_diaries.to_excel(self.user_diaries_file, index=False)

            return True, "评分成功"
        except Exception as e:
            print(f"评分时出错: {e}")
            return False, "评分失败"

    def get_diary_rating(self, diary_id, user_id):
        """获取用户对日记的评分"""
        try:
            df = pd.read_excel('data/diary_ratings.xlsx')
            rating = df[(df['diary_id'] == diary_id) & (df['user_id'] == user_id)]
            if not rating.empty:
                return rating.iloc[0]['rating']
            return None
        except Exception as e:
            print(f"获取用户评分时出错: {e}")
            return None

    def increment_place_view_count(self, place_id):
        """增加指定地点的浏览次数"""
        try:
            df_places = pd.read_excel(self.places_file)
            
            # 确保 View_Count 列存在且为整数类型
            if 'View_Count' not in df_places.columns:
                df_places['View_Count'] = 0 # 如果列不存在，则创建并初始化为0
            df_places['View_Count'] = pd.to_numeric(df_places['View_Count'], errors='coerce').fillna(0).astype(int)

            place_index = df_places[df_places['ID'] == place_id].index
            
            if not place_index.empty:
                idx = place_index[0]
                current_views = df_places.loc[idx, 'View_Count']
                df_places.loc[idx, 'View_Count'] = int(current_views) + 1
                df_places.to_excel(self.places_file, index=False)
                print(f"Place ID {place_id} View_Count incremented to {df_places.loc[idx, 'View_Count']}")
                return True
            else:
                print(f"Place ID {place_id} not found for incrementing view count.")
                return False
        except Exception as e:
            print(f"Error incrementing view count for place_id {place_id}: {e}")
            return False

    def update_diary_video(self, diary_id, video_url, status='completed'):
        """更新日记的视频信息"""
        try:
            df = pd.read_excel(self.user_diaries_file)
            diary_idx = df[df['id'] == diary_id].index
            if len(diary_idx) > 0:
                df.at[diary_idx[0], 'video_url'] = video_url
                df.at[diary_idx[0], 'video_status'] = status
                df.to_excel(self.user_diaries_file, index=False)
                return True
            return False
        except Exception as e:
            print(f"更新日记视频信息时出错: {e}")
            return False

    def get_diary_video_status(self, diary_id):
        """获取日记视频生成状态"""
        try:
            df = pd.read_excel(self.user_diaries_file)
            diary = df[df['id'] == diary_id]
            if not diary.empty:
                return {
                    'status': diary.iloc[0]['video_status'],
                    'video_url': diary.iloc[0]['video_url']
                }
            return None
        except Exception as e:
            print(f"获取日记视频状态时出错: {e}")
            return None
    
    
    def update_user_tags_based_on_browsing(self, user_id):
        """根据用户浏览历史中访问次数最多的地点分类来更新用户标签"""
        try:
            # 1. 获取该用户的所有浏览记录
            df_history = pd.read_excel(self.browse_history_file)
            if df_history.empty or 'user_id' not in df_history.columns:
                print(f"用户 {user_id} 的浏览历史为空或格式不正确。")
                return False
            
            # 确保 user_id 列和传入的 user_id 类型一致以便比较
            try:
                current_user_id = int(user_id)
                df_history['user_id'] = pd.to_numeric(df_history['user_id'], errors='coerce').fillna(-1).astype(int)
            except ValueError:
                current_user_id = str(user_id)
                df_history['user_id'] = df_history['user_id'].astype(str)

            user_history = df_history[df_history['user_id'] == current_user_id]
            if user_history.empty:
                print(f"用户 {user_id} 没有浏览历史。")
                return False # 或者可以设置为空标签 []

            # 2. 获取地点数据以映射 place_name 到 Place_Category
            df_places = pd.read_excel(self.places_file)
            if df_places.empty or 'Place_Name' not in df_places.columns or 'Place_Category' not in df_places.columns:
                print("地点数据不完整或格式不正确。")
                return False
            
            # 确保比较的列类型一致
            df_places['Place_Name'] = df_places['Place_Name'].astype(str)
            user_history['place_name'] = user_history['place_name'].astype(str)

            # 3. 计算用户对每个 Place_Category 的总访问次数
            category_view_counts = {}
            for _, row in user_history.iterrows():
                place_name = row['place_name']
                user_specific_counts = row.get('user_specific_view_count', 0)
                
                # 查找地点对应的分类
                place_info = df_places[df_places['Place_Name'] == place_name]
                if not place_info.empty:
                    category = place_info.iloc[0]['Place_Category']
                    category_view_counts[category] = category_view_counts.get(category, 0) + user_specific_counts
            
            if not category_view_counts:
                print(f"无法为用户 {user_id} 计算分类访问次数 (可能所有浏览过的地点都不在places.xlsx中)。")
                # 可以选择将用户标签设置为空列表
                # df_users = pd.read_excel(self.users_file)
                # user_idx = df_users[df_users['id'] == current_user_id].index
                # if not user_idx.empty:
                #     df_users.at[user_idx[0], 'tags'] = json.dumps([])
                #     df_users.to_excel(self.users_file, index=False)
                return False

            # 4. 找出访问次数最高的 Place_Category
            max_view_count = 0
            for category in category_view_counts:
                if category_view_counts[category] > max_view_count:
                    max_view_count = category_view_counts[category]
            
            # 如果最大访问次数为0（例如，所有 user_specific_view_count 都是0），则不更新标签或设置为空
            if max_view_count == 0:
                print(f"用户 {user_id} 对所有分类的总访问次数为0，不更新标签。")
                # 或者，将标签设为空列表 []
                # new_tags_list = []
                return True # 认为操作成功，只是没有标签可更新

            top_categories = [cat for cat, count in category_view_counts.items() if count == max_view_count]

            # 5. 更新 users.xlsx 中的 tags
            df_users = pd.read_excel(self.users_file)
            # 确保 id 列和 current_user_id 类型一致
            try:
                df_users['id'] = pd.to_numeric(df_users['id'], errors='coerce').fillna(-1).astype(int)
            except ValueError: # 如果 df_users['id'] 无法安全转换为数字
                 pass # 保持原样，后续比较可能依赖 current_user_id 的类型
            
            user_idx = df_users[df_users['id'] == current_user_id].index
            if not user_idx.empty:
                idx_to_update = user_idx[0]
                df_users.at[idx_to_update, 'tags'] = json.dumps(top_categories, ensure_ascii=False)
                df_users.to_excel(self.users_file, index=False)
                print(f"用户 {user_id} 的标签已更新为: {top_categories}")
                return True
            else:
                print(f"在 users.xlsx 中未找到用户 ID: {user_id}")
                return False

        except Exception as e:
            print(f"更新用户 {user_id} 标签时出错: {e}")
            return False

def save_to_excel(filepath, data):
    if not os.path.exists(filepath):
        df = pd.DataFrame(columns=['username', 'place', 'title', 'content', 'picture', 'timestamp'])
    else:
        df = pd.read_excel(filepath)
    
    df = df.append(data, ignore_index=True)
    df.to_excel(filepath, index=False)
