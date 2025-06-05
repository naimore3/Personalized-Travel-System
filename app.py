# app.py
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from utils.excel_handler import ExcelHandler
from utils.big_model import BigModel
from utils.sorting_algorithm import get_top_ten_places, sort_diaries, kmp_search  # 导入排序方法和kmp_search
from utils.graph import Graph
from utils.select_routing_planner import plan_route
from utils.food_search import search_and_sort_foods, CUISINES, get_all_places
from utils.indoor_path_finder import find_path_across_floors
import re
import os
import uuid
import subprocess
from werkzeug.utils import secure_filename
from datetime import datetime
from PIL import Image
import numpy as np
import requests
import time
import hashlib
import hmac
import base64
import json
import websocket  # 新增依赖
import ssl
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用于会话管理
excel_handler = ExcelHandler()
big_model = BigModel()
graph = Graph()  # 使用Graph类处理所有图相关操作

# 添加 nl2br 过滤器
@app.template_filter('nl2br')
def nl2br_filter(text):
    """将文本中的换行符转换为 HTML 的 <br> 标签"""
    if not text:
        return text
    return text.replace('\n', '<br>')

def ensure_upload_dir():
    upload_dir = os.path.join('static', 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

def ensure_video_dir():
    """确保视频存储目录存在"""
    video_dir = os.path.join('static', 'videos')
    if not os.path.exists(video_dir):
        os.makedirs(video_dir)
    return video_dir

# 确保上传目录存在
ensure_upload_dir()

# 添加 x-content-type-options 头
@app.after_request
def add_x_content_type_options(response):
    response.headers['x-content-type-options'] = 'nosniff'
    return response

def heapify(arr, n, i, key_func):
    largest = i
    l = 2 * i + 1
    r = 2 * i + 2
    if l < n and key_func(arr[l]) > key_func(arr[largest]):
        largest = l
    if r < n and key_func(arr[r]) > key_func(arr[largest]):
        largest = r
    if largest != i:
        arr[i], arr[largest] = arr[largest], arr[i]
        heapify(arr, n, largest, key_func)

def get_top_ten_places_heap(places):
    # 按评分和热度构建大顶堆
    n = len(places)
    key_func = lambda x: (float(x.get('Rating', 0)), int(x.get('View_Count', 0)))
    arr = places[:]
    # 建堆
    for i in range(n // 2 - 1, -1, -1):
        heapify(arr, n, i, key_func)
    # 取前十个最大
    result = []
    size = n
    for _ in range(min(10, n)):
        arr[0], arr[size-1] = arr[size-1], arr[0]
        result.append(arr[size-1])
        size -= 1
        heapify(arr, size, 0, key_func)
    return result

@app.route('/')
def index():
    username = session.get('username')
    places = excel_handler.get_recommended_places()  # 获取所有地点
    top_ten_places = get_top_ten_places_heap(places)  # 用手写堆排序获取前十个地点
    return render_template('index.html', username=username, top_ten_places=top_ten_places)

@app.route('/recommend')
def recommend():
    all_places = excel_handler.get_recommended_places()
    categories = sorted(list(set(place['Place_Category'] for place in all_places if 'Place_Category' in place)))
    selected_category = request.args.get('category')
    search_query = request.args.get('search_query', '').strip()
    personalized = request.args.get('personalized', '0') == '1'  # 新增参数，判断是否为个性推荐

    # 默认展示所有
    places_to_display = all_places
    user_tags = []
    personalized_message = None
    if personalized and 'username' in session:
        user = excel_handler.get_user_by_username(session['username'])
        if user:
            user_tags = user.get('tags', [])
            if user_tags:
                # 只展示与用户标签相关的地点
                places_to_display = [place for place in all_places if place.get('Place_Category') in user_tags]
            else:
                # 无标签，提示先浏览
                places_to_display = []
                personalized_message = '请先浏览以获得个性推荐'
        else:
            places_to_display = []
            personalized_message = '请先登录以获得个性推荐'
    else:
        if selected_category:
            places_to_display = [place for place in places_to_display if place.get('Place_Category') == selected_category]

        # 使用kmp_search进行匹配
        if search_query:
            search_query_lower = search_query.lower()
            places_to_display = [
                place for place in places_to_display
                if kmp_search(place.get('Place_Name', '').lower(), search_query_lower)
            ]

    # 按评分和热度排序
    places_to_display.sort(key=lambda x: (float(x.get('Rating', 0)), int(x.get('View_Count', 0))), reverse=True)

    return render_template('recommend.html', 
                           places=places_to_display, 
                           categories=categories, 
                           selected_category=selected_category, 
                           search_query=search_query,
                           personalized=personalized,
                           user_tags=user_tags,
                           personalized_message=personalized_message)

@app.route('/map')
def map():
    return render_template('map.html')

@app.route('/punch', methods=['GET', 'POST'])
def punch():
    places = excel_handler.get_places()
    all_diaries = excel_handler.get_all_diaries()  # 获取所有日记
    
    if request.method == 'POST':
        if 'username' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401

        picture = request.files.get('picture')
        title = request.form.get('title')
        content = request.form.get('content')
        place_id = request.form.get('place_id')

        if not title or not content:
            return jsonify({'success': False, 'message': '标题和内容不能为空'}), 400
        
        if not place_id:
            return jsonify({'success': False, 'message': '请选择打卡地点'}), 400

        user = excel_handler.get_user_by_username(session['username'])
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404

        # 保存图片到 static/uploads 目录
        if picture:
            # 获取文件扩展名
            file_ext = os.path.splitext(picture.filename)[1]
            if not file_ext:
                file_ext = '.jpg'  # 默认扩展名
                
            # 生成安全的文件名
            original_filename = secure_filename(picture.filename)
            if not original_filename:
                original_filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
            
            # 确保文件名有扩展名
            if not os.path.splitext(original_filename)[1]:
                original_filename = f"{original_filename}{file_ext}"
            
            # 处理文件名冲突
            file_base, file_ext = os.path.splitext(original_filename)
            counter = 1
            while os.path.exists(os.path.join('static', 'uploads', original_filename)):
                original_filename = f"{file_base}_{counter}{file_ext}"
                counter += 1
            
            # 保存文件
            upload_dir = os.path.join('static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            picture.save(os.path.join(upload_dir, original_filename))
            
            # 存储相对路径（不包含static目录）
            picture_path = os.path.join('uploads', original_filename)
            print(f"Saved image to: {picture_path}")  # 调试输出
        else:
            picture_path = None

        # 保存日记数据
        if excel_handler.add_user_diary(user['id'], title, content, session['username'], picture_path, place_id):
            # 获取新创建的日记ID
            all_diaries = excel_handler.get_all_diaries()
            new_diary = all_diaries[0]  # 因为日记是按创建时间倒序排列的，所以最新的日记在第一位
            return jsonify({
                'success': True, 
                'message': '添加日记成功',
                'diary_id': new_diary['id']  # 返回新创建的日记ID
            })
        return jsonify({'success': False, 'message': '添加日记失败'}), 500 

    place_param = request.args.get('place')
    return render_template('punch.html', places=places, all_diaries=all_diaries, place_param=place_param)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        question = request.form.get('question')
        result = big_model.query(question)
        return render_template('search.html', result=result)
    return render_template('search.html')

@app.route('/details/<int:place_id>')
def details(place_id):
    from_category = request.args.get('from_category') # 获取来源分类

    try:
        place = excel_handler.get_place_details(place_id) # 首先获取地点详情，以便后续使用 place_name
    except Exception as e:
        print(f"获取地点详情异常: {e}")
        flash('请求的地点不存在。', 'error')
        return redirect(url_for('recommend'))

    if not place:
        flash('请求的地点不存在。', 'error')
        return redirect(url_for('recommend'))

    # 保证place字典字段完整，防止模板KeyError
    default_fields = {
        'Place_Name': '未知地点',
        'Place_Category': '未知分类',
        'Country': '未知国家',
        'City': '未知城市',
        'Tags': '',
        'Description': '暂无描述',
        'Rating': 0,
        'View_Count': 0,
        'Picture': 'images/default.jpg'
    }
    for k, v in default_fields.items():
        if k not in place or place[k] is None:
            place[k] = v

    try:
        if 'username' in session:
            user = excel_handler.get_user_by_username(session['username'])
            if user:
                try:
                    excel_handler.add_browse_history(user['id'], place['Place_Name'])
                    excel_handler.update_user_tags_based_on_browsing(user['id'])
                except Exception as e:
                    print(f"添加浏览历史或更新标签异常: {e}")
            else:
                try:
                    excel_handler.increment_view_count(place_id)
                except Exception as e:
                    print(f"增加浏览次数异常: {e}")
        else:
            try:
                excel_handler.increment_view_count(place_id)
            except Exception as e:
                print(f"增加浏览次数异常: {e}")
    except Exception as e:
        print(f"用户相关操作异常: {e}")

    # 重新获取地点详情，以确保 view_count 是最新的
    try:
        place = excel_handler.get_place_details(place_id)
    except Exception as e:
        print(f"重新获取地点详情异常: {e}")
    if not place:
        place = default_fields.copy()

    for k, v in default_fields.items():
        if k not in place or place[k] is None:
            place[k] = v

    return render_template('details.html', place=place, came_from_category=from_category)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return jsonify({
                'success': False,
                'message': '两次输入的密码不一致！'
            })
        
        if excel_handler.check_user_exists(username):
            return jsonify({
                'success': False,
                'message': '该用户名已被注册！'
            })
        
        if excel_handler.create_user(username, password):
            return jsonify({
                'success': True,
                'message': '注册成功！'
            })
        else:
            return jsonify({
                'success': False,
                'message': '注册失败，请稍后重试！'
            })
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 先检查用户是否存在
        if not excel_handler.check_user_exists(username):
            return jsonify({
                'success': False,
                'message': '该账号不存在！'
            })
        
        # 再检查密码是否正确
        if excel_handler.check_user(username, password):
            session['username'] = username
            return jsonify({
                'success': True,
                'message': '登录成功！',
                'username': username
            })
        else:
            return jsonify({
                'success': False,
                'message': '密码错误！'
            })
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/update_graph', methods=['POST'])
def update_graph():
    """处理搜索结果点的连接关系"""
    try:
        data = request.json
        if not data or 'pois' not in data:
            return jsonify({'error': 'No POI data provided'}), 400
        
        # 检查数据格式
        for poi in data['pois']:
            if not all(key in poi for key in ['id', 'location', 'name']):
                return jsonify({
                    'error': f'Invalid POI data format. Missing required fields in: {poi}'
                }), 400
            if not all(key in poi['location'] for key in ['lng', 'lat']):
                return jsonify({
                    'error': f'Invalid location data format in POI: {poi}'
                }), 400
        
        # 使用图处理类处理连接关系
        try:
            connections = graph.add_points(data['pois'])
            return jsonify({
                'connections': connections
            })
        except Exception as e:
            print("Error in graph.add_points:", str(e))
            import traceback
            traceback.print_exc()
            return jsonify({
                'error': f'Error processing graph: {str(e)}'
            }), 500
            
    except Exception as e:
        print("Error in update_graph:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/profile')
def profile():
    # 检查用户是否已登录
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # 获取用户信息
    user = excel_handler.get_user_by_username(session['username'])
    if not user:
        # 如果用户不存在，清除会话并重定向到登录页面
        session.pop('username', None)
        return redirect(url_for('login'))

    # 获取用户相关数据
    user_tags = excel_handler.get_user_tags(user['id'])
    user_diaries = excel_handler.get_user_diaries(user['id'])
    browse_history = excel_handler.get_browse_history(user['id'])

    # 渲染个人信息页面
    return render_template('profile.html',
                         username=user['username'],
                         user_id=user['id'],
                         user_tags=user_tags,
                         user_diaries=user_diaries,
                         browse_history=browse_history)

@app.route('/add_tag', methods=['POST'])
def add_tag():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    tag = request.form.get('tag')
    if not tag:
        return jsonify({'success': False, 'message': '标签不能为空'}), 400

    user = excel_handler.get_user_by_username(session['username'])
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    if excel_handler.add_user_tag(user['id'], tag):
        return jsonify({'success': True, 'message': '添加标签成功'})
    return jsonify({'success': False, 'message': '添加标签失败'}), 500

@app.route('/add_diary', methods=['POST'])
def add_diary():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    title = request.form.get('title')
    content = request.form.get('content')
    
    if not title or not content:
        return jsonify({'success': False, 'message': '标题和内容不能为空'}), 400

    user = excel_handler.get_user_by_username(session['username'])
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    if excel_handler.add_user_diary(user['id'], title, content):
        return jsonify({'success': True, 'message': '添加日记成功'})
    return jsonify({'success': False, 'message': '添加日记失败'}), 500

@app.route('/add_history', methods=['POST'])
def add_history():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    place_name = request.form.get('place_name')
    if not place_name:
        return jsonify({'success': False, 'message': '地点名称不能为空'}), 400

    user = excel_handler.get_user_by_username(session['username'])
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    if excel_handler.add_browse_history(user['id'], place_name):
        return jsonify({'success': True, 'message': '添加浏览记录成功'})
    return jsonify({'success': False, 'message': '添加浏览记录失败'}), 500

@app.route('/get_places', methods=['GET'])
def get_places():
    """获取所有地点列表"""
    try:
        places = excel_handler.get_recommended_places()
        place_names = [place['Place_Name'] for place in places]
        return jsonify({
            'success': True,
            'places': place_names
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/domestic_map')
def domestic_map():
    """国内地图页面"""
    return render_template('domestic_map.html')

@app.route('/global_map')
def global_map():
    """环球地图页面，动态读取国家数据"""
    # 完善国家中文名到国旗代码映射（ISO 3166-1 alpha-2）
    country_flag_map = {
        '中国': 'cn', '印度': 'in', '日本': 'jp', '韩国': 'kr', '泰国': 'th', '缅甸': 'mm',
        '印度尼西亚': 'id', '越南': 'vn', '马来西亚': 'my', '尼泊尔': 'np', '沙特阿拉伯': 'sa',
        '伊朗': 'ir', '土耳其': 'tr', '菲律宾': 'ph', '以色列': 'il', '新加坡': 'sg',
        '文莱': 'bn', '不丹': 'bt', '阿联酋': 'ae', '阿富汗': 'af', '法国': 'fr',
        '意大利': 'it', '英国': 'gb', '德国': 'de', '西班牙': 'es', '瑞典': 'se',
        '瑞士': 'ch', '荷兰': 'nl', '俄罗斯': 'ru', '希腊': 'gr', '挪威': 'no',
        '芬兰': 'fi', '丹麦': 'dk', '葡萄牙': 'pt', '奥地利': 'at', '匈牙利': 'hu',
        '波兰': 'pl', '捷克': 'cz', '比利时': 'be', '圣马力诺': 'sm', '列支敦士登': 'li',
        '美国': 'us', '巴西': 'br', '加拿大': 'ca', '墨西哥': 'mx', '阿根廷': 'ar',
        '秘鲁': 'pe', '哥伦比亚': 'co', '智利': 'cl', '古巴': 'cu', '牙买加': 'jm',
        '哥斯达黎加': 'cr', '乌拉圭': 'uy', '巴拿马': 'pa', '巴巴多斯': 'bb',
        '厄瓜多尔': 'ec', '埃及': 'eg', '南非': 'za', '肯尼亚': 'ke', '尼日利亚': 'ng',
        '摩洛哥': 'ma', '埃塞俄比亚': 'et', '坦桑尼亚': 'tz', '加纳': 'gh',
        '纳米比亚': 'na', '博茨瓦纳': 'bw', '马达加斯加': 'mg', '喀麦隆': 'cm',
        '津巴布韦': 'zw', '多哥': 'tg', '塞内加尔': 'sn', '乌干达': 'ug', '安哥拉': 'ao',
        '赞比亚': 'zm', '澳大利亚': 'au', '新西兰': 'nz', '斐济': 'fj',
        '巴布亚新几内亚': 'pg', '汤加': 'to', '所罗门群岛': 'sb', '图瓦卢': 'tv',
        '基里巴斯': 'ki', '萨摩亚': 'ws', '密克罗尼西亚': 'fm', '瓦努阿图': 'vu',
        '瑙鲁': 'nr'
    }
    countries = []
    try:
        df = pd.read_excel('data/country_features.xlsx')
        for _, row in df.iterrows():
            name = str(row[0]).strip()
            desc = str(row[1]).strip() if len(row) > 1 else ''
            flag_code = country_flag_map.get(name, 'un')
            countries.append({'name': name, 'desc': desc, 'flag_code': flag_code})
    except Exception as e:
        print(f"读取国家数据失败: {e}")
    return render_template('global_map.html', countries=countries)

@app.route('/update_map_graph', methods=['POST'])
def update_map_graph():
    """处理地图景点的连接关系"""
    try:
        data = request.json
        if not data or 'pois' not in data:
            return jsonify({'error': 'No POI data provided'}), 400
        
        # 打印接收到的数据，用于调试
        # print("Received POIs:", data['pois'])
        
        # 检查数据格式
        for poi in data['pois']:
            if not all(key in poi for key in ['id', 'location', 'name']):
                return jsonify({
                    'error': f'Invalid POI data format. Missing required fields in: {poi}'
                }), 400
            if not all(key in poi['location'] for key in ['lng', 'lat']):
                return jsonify({
                    'error': f'Invalid location data format in POI: {poi}'
                }), 400
        
        # 使用图处理类处理连接关系
        try:
            connections = graph.add_points(data['pois'])
            # print("Generated connections:", connections)
            return jsonify(connections)
        except Exception as e:
            print("Error in graph.add_points:", str(e))
            import traceback
            traceback.print_exc()
            return jsonify({
                'error': f'Error processing graph: {str(e)}'
            }), 500
            
    except Exception as e:
        print("Error in update_map_graph:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/route_planner')
def route_planner():
    return render_template('route_planner.html')

@app.route('/calculate_route', methods=['POST'])
def calculate_route():
    try:
        data = request.json
        if not data or 'pois' not in data:
            return jsonify({'error': 'No POI data provided'}), 400

        # 获取所有POI点
        pois = data['pois']
        
        # 获取规划模式
        mode = data.get('mode', 'distance')  # 默认为最短距离模式
        
        # 获取图的所有边
        edges = graph.get_all_edges()
        
        # 使用动态规划算法计算最优路径
        route = plan_route(pois, edges, mode=mode)
        
        return jsonify({
            'success': True,
            'route': route
        })
    except Exception as e:
        print("Error in calculate_route:", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/indoor_navigation')
def indoor_navigation():
    return render_template('indoor_navigation.html')

@app.route('/food_discovery')
def food_discovery():
    return render_template('food_discovery.html')

@app.route('/food_search', methods=['GET'])
def food_search():
    # 获取前端参数
    query = request.args.get('query', '', type=str)
    cuisine = request.args.get('cuisine', '', type=str)
    sort_key = request.args.get('sort', 'popularity', type=str)  # popularity, rating, distance
    n = request.args.get('n', 10, type=int)
    place = request.args.get('place', '', type=str)
    # 查询和排序
    foods = search_and_sort_foods(query=query, cuisine=cuisine, sort_key=sort_key, n=n, place=place)
    return jsonify({'foods': foods})

@app.route('/get_cuisines', methods=['GET'])
def get_cuisines():
    return jsonify({'cuisines': CUISINES})

@app.route('/api/indoor_path', methods=['POST'])
def api_indoor_path():
    """室内导航路径查找API"""
    data = request.get_json()
    start_floor = data.get('start_floor')
    start_idx = data.get('start_idx')
    end_floor = data.get('end_floor')
    end_idx = data.get('end_idx')
    floorData = data.get('floorData')
    if not all([start_floor, start_idx, end_floor, end_idx, floorData]):
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    path = find_path_across_floors(floorData, start_floor, start_idx, end_floor, end_idx)
    if not path:
        return jsonify({'success': False, 'message': '未找到可行路径'}), 200
    return jsonify({'success': True, 'path': path})

@app.route('/diary_detail/<int:diary_id>')
def diary_detail(diary_id):
    try:
        # 检查用户是否登录
        if 'username' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))

        # 获取日记详情
        diary = excel_handler.get_diary_by_id(diary_id)
        if not diary:
            flash('日记不存在', 'error')
            return redirect(url_for('punch'))
            #return redirect(url_for('profile'))

        # 增加浏览量
        excel_handler.increment_diary_views(diary_id)
        
        # 获取用户评分
        user = excel_handler.get_user_by_username(session['username'])
        if not user:
            flash('用户信息错误', 'error')
            return redirect(url_for('login'))
            
        user_rating = excel_handler.get_diary_rating(diary_id, user['id'])
        
        return render_template('diary_detail.html', 
                            diary=diary, 
                            user_rating=user_rating)
                            
    except Exception as e:
        print(f"查看日记详情出错: {str(e)}")
        flash('查看日记详情时出错', 'error')
        return redirect(url_for('profile'))

@app.route('/rate_diary', methods=['POST'])
def rate_diary():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    diary_id = request.form.get('diary_id')
    rating = request.form.get('rating')
    
    if not diary_id or not rating:
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    
    try:
        diary_id = int(diary_id)
        rating = float(rating)
    except ValueError:
        return jsonify({'success': False, 'message': '参数格式错误'}), 400
    
    user = excel_handler.get_user_by_username(session['username'])
    success, message = excel_handler.rate_diary(diary_id, user['id'], rating)
    
    return jsonify({'success': success, 'message': message})

@app.route('/sort_diaries')
def sort_diaries_route():
    """处理日记排序和搜索请求"""
    try:
        sort_by = request.args.get('sort_by', 'views')  # 默认按热度排序
        search_text = request.args.get('search_text', '')  # 搜索文本
        search_type = request.args.get('search_type', 'all')  # 搜索类型
        
        print(f"排序请求参数: sort_by={sort_by}, search_text={search_text}, search_type={search_type}")
        
        if sort_by not in ['views', 'rating']:
            print(f"无效的排序选项: {sort_by}")
            return jsonify({'success': False, 'message': '无效的排序选项'}), 400
            
        if search_type not in ['all', 'place', 'title', 'content']:
            print(f"无效的搜索类型: {search_type}")
            return jsonify({'success': False, 'message': '无效的搜索类型'}), 400
            
        # 获取所有日记
        all_diaries = excel_handler.get_all_diaries()
        print(f"获取到的日记数量: {len(all_diaries)}")
        
        if not all_diaries:
            print("没有找到任何日记")
            return jsonify({
                'success': True,
                'diaries': []
            })
        
        # 检查日记内容是否成功解压
        for diary in all_diaries:
            if not diary.get('content'):
                print(f"警告：日记ID {diary.get('id')} 的内容解压失败")
                diary['content'] = "内容读取失败"
        
        # 使用自定义排序算法进行排序和搜索
        sorted_diaries = sort_diaries(all_diaries, sort_by, search_text, search_type)
        print(f"排序后的日记数量: {len(sorted_diaries)}")
        
        return jsonify({
            'success': True,
            'diaries': sorted_diaries
        })
    except Exception as e:
        print(f"排序日记时出错: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': '排序失败'}), 500

def generate_travel_video(image_path, output_path, duration=4):
    """使用AI生成旅游动画视频"""
    try:
        # 读取原
        for i in range(num_frames):
            # 计算缩放因子和平移量
            scale = 1 + 0.1 * np.sin(i / num_frames * np.pi)
            dx = int(50 * np.sin(i / num_frames * 2 * np.pi))
            dy = int(30 * np.cos(i / num_frames * 2 * np.pi))
            
            # 创建变换矩阵
            M = np.float32([[scale, 0, dx], [0, scale, dy]])
            
            # 应用变换
            height, width = img.shape[:2]
            frame = cv2.warpAffine(img, M, (width, height))
            
            # 添加渐变效果
            alpha = 0.7 + 0.3 * np.sin(i / num_frames * np.pi)
            frame = cv2.addWeighted(frame, alpha, img, 1-alpha, 0)
            
            frames.append(frame)
        
        # 创建视频
        clip = ImageSequenceClip(frames, fps=30)
        clip.write_videofile(output_path, codec='libx264', audio=False)
        
        return True
    except Exception as e:
        print(f"生成视频时出错: {e}")
        return False

@app.route('/generate_diary_video', methods=['POST'])
def generate_diary_video():
    """处理视频生成请求"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        data = request.get_json()
        diary_id = data.get('diary_id')
        
        if not diary_id:
            return jsonify({'success': False, 'message': '参数不完整'}), 400
        
        # 获取日记信息
        diary = excel_handler.get_diary_by_id(diary_id)
        if not diary:
            return jsonify({'success': False, 'message': '日记不存在'}), 404
        
        if not diary.get('picture'):
            return jsonify({'success': False, 'message': '日记没有图片，无法生成视频'}), 400
        
        # 检查视频状态
        video_status = excel_handler.get_diary_video_status(diary_id)
        if video_status and video_status['status'] == 'processing':
            return jsonify({'success': False, 'message': '视频正在生成中，请稍候'}), 400
        
        # 更新状态为处理中
        excel_handler.update_diary_video(diary_id, None, 'processing')
        
        # 准备文件路径
        image_path = os.path.join('static', diary['picture'])
        video_filename = f"{uuid.uuid4()}.mp4"
        video_path = os.path.join(ensure_video_dir(), video_filename)
        
        # 生成视频
        if generate_travel_video(image_path, video_path):
            # 更新视频信息
            excel_handler.update_diary_video(diary_id, video_filename, 'completed')
            return jsonify({
                'success': True,
                'message': '视频生成成功',
                'video_url': video_filename
            })
        else:
            excel_handler.update_diary_video(diary_id, None, 'failed')
            return jsonify({'success': False, 'message': '视频生成失败'}), 500
            
    except Exception as e:
        print(f"处理视频生成请求时出错: {e}")
        if 'diary_id' in locals():
            excel_handler.update_diary_video(diary_id, None, 'failed')
        return jsonify({'success': False, 'message': '服务器错误'}), 500

@app.route('/ask_ai', methods=['POST'])
def ask_ai():
    try:
        data = request.get_json()
        country = data.get('country') if data else None
        if not country:
            return jsonify({'answer': '未指定国家'}), 400
        # 构造API请求体
        url = "https://spark-api-open.xf-yun.com/v2/chat/completions"
        api_data = {
            "max_tokens": 4096,
            "top_k": 4,
            "temperature": 0.5,
            "messages": [
                {
                    "role": "system",
                    "content": "你是资深的旅游达人Yoyo,用户将输入一个国家，你需要为用户返回该国家的基础介绍，该国家的人文特点，自然风光特点。然后本别向用户介绍该国家的热门景点和小众景点。最后给用户一个合适的旅游行程安排，以及旅游建议。\n\n你的语言需要生动活泼，并且使用大量emoji进行回答。"
                },
                {
                    "role": "user",
                    "content": f"请介绍{country}"
                }
            ],
            "model": "x1",
            "tools": [
                {
                    "web_search": {
                        "search_mode": "normal",
                        "enable": False
                    },
                    "type": "web_search"
                }
            ],
            "stream": True
        }
        header = {
            "Authorization": "Bearer cedkgQopndMsKnuHfMQZ:BKIGTFdFFyTTXakqABqY"
        }
        response = requests.post(url, headers=header, json=api_data, stream=True, timeout=30)
        response.encoding = "utf-8"
        answer = ""
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.strip():
                continue
            try:
                # 兼容流式返回格式
                if line.startswith("data: "):
                    line = line[6:]
                data_json = json.loads(line)
                if 'choices' in data_json and data_json['choices']:
                    delta = data_json['choices'][0].get('delta', {})
                    content = delta.get('content', '')
                    answer += content
            except Exception:
                continue
        if not answer:
            answer = 'AI未返回内容，请稍后重试。'
        return jsonify({'answer': answer})
    except Exception as e:
        print(f"AI接口调用异常: {e}")
        return jsonify({'answer': 'AI服务异常，请稍后重试。'}), 500

@app.route('/text_fantasy')
def text_fantasy():
    # 读取places表格
    df = pd.read_excel('data/places.xlsx')
    places = df['name'].dropna().unique().tolist() if 'name' in df.columns else df.iloc[:,0].dropna().unique().tolist()
    return render_template('text_fantasy.html', places=places)

@app.route('/generate_video', methods=['POST'])
def generate_video():
    data = request.get_json()
    place = data.get('place')
    desc = data.get('desc') or ''
    # 新增：查找地点详细介绍
    place_info = excel_handler.get_place_by_name(place) if place else None
    place_desc = place_info['Description'] if place_info and 'Description' in place_info else ''
    # 优先拼接详细介绍
    prompt = f"{place}，简介：{place_desc}。{desc} --resolution 720p --duration 5 --camerafixed false"
    payload = {
        "model": "doubao-seedance-1-0-lite-i2v-250428",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/see_i2v.jpeg"}}
        ]
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer 88653e63-3ec4-490a-aa56-8660983d7c44"
    }
    try:
        resp = requests.post('https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks', json=payload, headers=headers, timeout=20)
        if resp.status_code == 200 and resp.json().get('id'):
            return jsonify({'success': True, 'task_id': resp.json()['id']})
        else:
            return jsonify({'success': False, 'msg': resp.text})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/check_video_status')
def check_video_status():
    task_id = request.args.get('task_id')
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer 88653e63-3ec4-490a-aa56-8660983d7c44"
    }
    try:
        resp = requests.get(f'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}', headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print('视频生成API返回：', data)  # 调试用，查看API返回内容
            status = data.get('status')
            video_url = ''
            # 兼容content.video_url
            if status == 'succeeded':
                result = data.get('result', {})
                content = data.get('content', {})
                # 优先result.video_url，其次content.video_url
                video_url = result.get('video_url') if isinstance(result, dict) else ''
                if not video_url and isinstance(content, dict):
                    video_url = content.get('video_url', '')
            return jsonify({'status': status, 'video_url': video_url})
        else:
            return jsonify({'status': 'failed'})
    except Exception as e:
        return jsonify({'status': 'failed', 'msg': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
