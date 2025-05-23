# app.py
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from utils.excel_handler import ExcelHandler
from utils.big_model import BigModel
from utils.sorting_algorithm import get_top_ten_places  # 导入排序方法
from utils.search_graph import search_graph
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用于会话管理
excel_handler = ExcelHandler()
big_model = BigModel()

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
        
        # 打印接收到的数据，用于调试
        print("Received POI data:", data['pois'])
        
        # 使用图处理类处理连接关系
        connections = search_graph.add_points(data['pois'])
        
        # 打印生成的连接数据，用于调试
        print("Generated connections:", connections)
        
        return jsonify({
            'connections': connections
        })
    except Exception as e:
        print("Error in update_graph:", str(e))  # 打印错误信息
        return jsonify({'error': str(e)}), 500

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

if __name__ == '__main__':
    app.run(debug=True)