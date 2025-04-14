from flask import Flask, render_template, request
from models.database import Database
from utils.big_model import BigModel

app = Flask(__name__)
db = Database()
big_model = BigModel()

# 添加 x-content-type-options 头
@app.after_request
def add_x_content_type_options(response):
    response.headers['x-content-type-options'] = 'nosniff'
    return response

@app.route('/')
def index():
    return render_template('index.html')

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

if __name__ == '__main__':
    app.run(debug=True)