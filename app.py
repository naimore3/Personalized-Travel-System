# app.py
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from utils.excel_handler import ExcelHandler
from utils.big_model import BigModel
from utils.sorting_algorithm import get_top_ten_places  # 导入排序方法
from utils.graph import Graph
from utils.select_routing_planner import plan_route
from utils.food_search import search_and_sort_foods, CUISINES, get_all_places
from utils.indoor_path_finder import find_path_across_floors
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用于会话管理
excel_handler = ExcelHandler()
big_model = BigModel()
graph = Graph()  # 使用Graph类处理所有图相关操作

# 添加 x-content-type-options 头
@app.after_request
def add_x_content_type_options(response):
    response.headers['x-content-type-options'] = 'nosniff'
    return response

@app.route('/')
def index():
    username = session.get('username')
    places = excel_handler.get_recommended_places()  # 获取所有地点
    top_ten_places = get_top_ten_places(places)  # 调用排序方法获取前十个地点
    return render_template('index.html', username=username, top_ten_places=top_ten_places)

@app.route('/recommend')
def recommend():
    places = excel_handler.get_recommended_places()
    return render_template('recommend.html', places=places)

@app.route('/map')
def map():
    return render_template('map.html')

@app.route('/punch', methods=['GET', 'POST'])
def punch():
    if request.method == 'POST':
        place = request.form.get('place')
        picture = request.files.get('picture')
        title = request.form.get('title')
        content = request.form.get('content')
        # TODO: 实现打卡记录功能
    return render_template('punch.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        question = request.form.get('question')
        result = big_model.query(question)
        return render_template('search.html', result=result)
    return render_template('search.html')

@app.route('/details/<int:place_id>')
def details(place_id):
    place = excel_handler.get_place_details(place_id)
    return render_template('details.html', place=place)

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
                'message': '登录成功！'
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
    """环球地图页面"""
    return render_template('global_map.html')

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

if __name__ == '__main__':
    app.run(debug=True)
