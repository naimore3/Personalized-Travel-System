# app.py
from flask import Flask, render_template, request, session, redirect, url_for
from models.database import Database
from utils.big_model import BigModel
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用于会话管理
db = Database()
big_model = BigModel()

# 添加 x-content-type-options 头
@app.after_request
def add_x_content_type_options(response):
    response.headers['x-content-type-options'] = 'nosniff'
    return response

@app.route('/')
def index():
    username = session.get('username')
    return render_template('index.html', username=username)

@app.route('/recommend')
def recommend():
    places = db.get_recommended_places()
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
        db.add_punch_record(place, picture, title, content)
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
    place = db.get_place_details(place_id)
    return render_template('details.html', place=place)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if re.match(r'^[a-zA-Z0-9]+$', username) and re.match(r'^[a-zA-Z0-9]+$', password):
            if db.register_user(username, password):
                return '注册成功'
            else:
                return '注册失败'
        else:
            return '用户名和密码只能由英文和数字组成'
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if db.check_user(username, password):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return '请注册账号'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)