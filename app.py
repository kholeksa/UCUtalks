'''
 --- UCUtalks ---

Team:
 - Khita Oleksa
 - Dizhak Nazar
 - Zaklekta Roman
 - Dovhai Ruslan
 - Dumai Kateryna'''

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from pymongo.mongo_client import MongoClient
import base64
import os

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = '123'

client = MongoClient("mongodb+srv://oleksa:oleksa2@uctk.oc9ucj1.mongodb.net/?retryWrites=true&w=majority&appName=Uctk")

mydb = client["mydb"]
courses_db = mydb["course"]
users_db = mydb["users"]
courses = [course['name'] for course in courses_db.find()]
users = [user['email'] for user in users_db.find()]

with open('swears.txt', 'rb') as file:
    encoded_data = file.read()
    swears = base64.b64decode(encoded_data)
    swears = swears.decode('utf-8').split()

class User():
    users = {user['email'] for user in users_db.find()}
    is_authenticated = False

    def __init__(self, name, email, picture):
        self.name = name
        self.email = email
        self.picture = picture

    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email}

blueprint = make_google_blueprint(
    client_id="582748017051-d1o8ek940oot1f6akhd3ab06cehnpj3s.apps.googleusercontent.com",
    client_secret="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",
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"])

app.register_blueprint(blueprint, url_prefix="/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    '''Redirects to Google login page'''
    session.clear()
    if not google.authorized:
        return redirect(url_for("google.login"))
    
@app.route("/logout", methods=['GET', 'POST'])
def logout():
    '''Logs out the user and redirects to the index page'''
    session.clear()
    user = User('Анонімний Користувач', None, None)
    session['user'] = user.to_dict()
    return redirect(url_for("index"))

@oauth_authorized.connect_via(blueprint)
def logged_in(blueprint, token):
    '''Logs the user in and saves his data to the session'''
    resp = blueprint.session.get("/oauth2/v1/userinfo")
    if resp.ok:
        email = resp.json()["email"]
        name = resp.json()["name"]
        profile_image = resp.json()["picture"]
        user = User(name, email, profile_image)
        User.is_authenticated = True
        session['user'] = user.to_dict()
        session['picture'] = profile_image
        if email not in User.users:
            users_db.insert_one({'email': email, 'name': name})
        print('Logged in as', email)

@app.route("/")
def index():
    '''Renders the index page'''
    if not User.is_authenticated:
        user = User('Анонімний Користувач', None, None)
        session['user'] = user.to_dict()
    print(session.get('user'))
    return render_template("index.html", courses=courses)

@app.route("/", methods=["GET", "POST"])
def search():
    '''Searches for courses'''
    search = request.form.get('search').lower()
    result = [i for i in courses if search in i.lower()]
    session['result'] = result
    return redirect(url_for('get_results'))

@app.route("/results", methods=["GET"])
def get_results():
    '''Renders the search results page'''
    result = session.get('result', courses)
    return render_template("index.html", courses=result)

@app.route('/about')
def about():
    '''Renders the "about" page'''
    return render_template('about.html')

@app.route('/course', methods=['GET', 'POST'])
def course():
    '''Redirects to the course page with the course name provided in the form'''
    course_name = request.form.get('course')
    if not course_name:
        abort(400, description="No course name provided")
    return redirect(url_for('course_name', course=request.form.get('course')))

@app.route('/course/<course>', methods=['GET'])
def course_name(course):
    '''Renders the course page with the course name provided in the URL'''
    info = courses_db.find_one({'name': course})

    if info is None:
        abort(404, description="This course doesn't exist")
    
    session['course'] = course
    course_info = (info['name'].split('. ')[1], info['teacher'], info['teacher_description'],\
                    info['course'], info['image'], info['comments'][::-1])

    return render_template('course.html', info=course_info, user = session.get('user'))

@app.route('/add_comment', methods=['POST'])
def add_comment():
    '''Adds a comment to the course'''
    course = session.get('course')
    comment = request.form.get('comment-input')

    for i in comment.split():
        if i in swears:
            comment = comment.replace(i, '*'*len(i))

    # Add comment to the database
    if not request.form.get('anonymous'):
        courses_db.update_one({'name': course},\
        {'$push': {'comments': [(session['user']['email'], session['user']['name'], comment)]}})
    else:
        courses_db.update_one({'name': course},\
        {'$push': {'comments': [('anonimous@ucu.edu.ua', 'Анонімний користувач', comment)]}})

    return redirect(url_for('course_name', course=course))

if __name__ == "__main__":
    app.run(debug=True)   
