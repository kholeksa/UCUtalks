print('Importing libs')
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from flask_login import LoginManager, UserMixin
from pymongo.mongo_client import MongoClient
import os
from neural import classifier

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

print('Creating app')
app = Flask(__name__)
app.secret_key = '123'
login_manager = LoginManager(app)

print('Connecting to db')
client = MongoClient("mongodb+srv://oleksa:oleksa2@uctk.oc9ucj1.mongodb.net/?retryWrites=true&w=majority&appName=Uctk")

mydb = client["mydb"]
courses_db = mydb["course"]
users_db = mydb["users"]
courses = [course['name'] for course in courses_db.find()]
users = [user['email'] for user in users_db.find()]

print('Done')
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

blueprint = make_google_blueprint(
    client_id="582748017051-d1o8ek940oot1f6akhd3ab06cehnpj3s.apps.googleusercontent.com",
    client_secret="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",
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
)

app.register_blueprint(blueprint, url_prefix="/login")

class User(UserMixin):
    users = {user['email'] for user in users_db.find()}
    is_authenticated = False

    def __init__(self, name, email):
        self.name = name
        self.email = email

    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email}

    @classmethod
    def get(cls, id):
        return cls.users.get(id)


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if not google.authorized:
        return redirect(url_for("google.login"))

@oauth_authorized.connect_via(blueprint)
def logged_in(blueprint, token):
    resp = blueprint.session.get("/oauth2/v1/userinfo")
    if resp.ok:
        email = resp.json()["email"]
        name = resp.json()["name"]
        user = User(name, email)
        User.is_authenticated = True
        session['user'] = user.to_dict()
        print(session.get('user'))
        if email not in User.users:
            users_db.insert_one({'email': email, 'name': name})
        print('Logged in as', email)

@app.route("/")
def index():
    if not User.is_authenticated:
        user = User('Анонімний Користувач', None)
        session['user'] = user.to_dict()
    return render_template("index.html", courses=courses)

@app.route("/", methods=["GET", "POST"])
def search():
    if request.method == 'POST':
        search = request.form.get('search', '').lower()
        result = [i for i in courses if search in i.lower()]
        no_results = not bool(result)
        session['result'] = result
        session['no_results'] = no_results
        return redirect(url_for('get_results'))
    else:
        return render_template("index.html", courses=result)

@app.route("/results", methods=["GET"])
def get_results():
    result = session.get('result', courses)
    no_results = session.get('no_results', False)
    return render_template("index.html", courses=result, no_results=no_results)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/course', methods=['GET', 'POST'])
def course():
    if request.method == 'POST':
        course = request.form.get('course')
    else:
        course = request.args.get('course')
    if not course:
        return redirect(url_for('index'))
    session['course'] = course
    info = courses_db.find_one({'name': course})
    course_info = (info['name'].split('. ')[1], info['teacher'], info['teacher_description'],\
                    info['course'], info['image'], info['comments'])
    
    session['course_info'] = course_info
    return render_template('course.html', info=course_info, user = session.get('user'))

@app.route('/add_comment', methods=['POST'])
def add_comment():
    course = session.get('course')
    comment = request.form.get('comment-input')

    if not comment:
        flash('Comment cannot be empty')
        return redirect(url_for('course', course=course))

    for i in comment.split():
        print(i, classifier.detect(i))
        if classifier.detect(i):
            comment = comment.replace(i, '*'*len(i))
        elif classifier.detect(''.join(comment.split())):
            comment = comment.replace(i, '*'*len(i))

    if not request.form.get('anonymous'):
        courses_db.update_one({'name': course},\
        {'$push': {'comments': [(session['user']['email'], session['user']['name'], comment)]}})
    else:
        courses_db.update_one({'name': course},\
        {'$push': {'comments': [('anonimous@ucu.edu.ua', 'Анонімний користувач', comment)]}})

    return redirect(url_for('course', course=course))

if __name__ == "__main__":
    app.run(debug=True)
