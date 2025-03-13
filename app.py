from flask import Flask, render_template, request, redirect, url_for, session, abort, jsonify
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from pymongo.mongo_client import MongoClient
import base64
import os

##################################    Setup    ##############################################

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = '123'

client = MongoClient("...")

mydb = client["mydb"]
courses_db = mydb["course"]
courses = [course['name'] for course in mydb["course"].find()]
users_db = mydb["users"]

with open('swears.txt', 'rb') as file:
    encoded_data = file.read()
    swears = base64.b64decode(encoded_data)
    swears = swears.decode('utf-8').split()

blueprint = make_google_blueprint(
    client_id="...",
    client_secret="...",
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"])

app.register_blueprint(blueprint, url_prefix="/login")

##############################################################################################

class User():
    users = {user['email'] for user in mydb["users"].find()}

    def __init__(self, name = 'Анонімний Користувач', email = None, picture = None):
        self.name = name
        self.email = email
        self.picture = picture

    def to_dict(self):
        return {'name': self.name, 'email': self.email}
    
    @staticmethod
    def anonymous_user():
        '''Function creates an anonymous user and saves
          it to the session if the user is not logged in.
          Created to prevent errors when the user is not logged in
          '''
        if not google.authorized:
            user = User()
            session['user'] = user.to_dict()

@app.route("/")
def index():
    '''Renders the index page'''
    User.anonymous_user()
    return render_template("index.html", courses=courses)

@app.route("/login", methods=["GET", "POST"])
def login():
    '''Redirects to Google login page'''
    session.clear()
    if not google.authorized:
        return redirect(url_for("google.login"))

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

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    '''Logs out the user and redirects to the index page'''
    session.clear()
    User.anonymous_user()
    return redirect(url_for("index"))

@app.route("/", methods=["GET", "POST"])
def search():
    '''Searches for courses'''
    search = request.form.get('search').lower()
    result = [i for i in courses if search in i.lower()]
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(result)
    else:
        session['result'] = result
        return redirect(url_for("get_results")) 

@app.route("/results", methods=["GET"])
def get_results():
    '''Renders the search results page'''
    User.anonymous_user()
    result = session.get('result', courses)
    return render_template("index.html", courses=result)

@app.route('/about')
def about():
    '''Renders the "about" page'''
    User.anonymous_user()
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
    User.anonymous_user()
    info = courses_db.find_one({'name': course})

    if info is None:
        abort(404, description="This course doesn't exist")
    
    session['course'] = course
    course_info = ('. '.join(info['name'].split('. ')[1:]), info['teacher'], info['teacher_description'],\
                    info['course'], info['image'], info['comments'][::-1])

    return render_template('course.html', info=course_info, user = session.get('user'))

@app.route('/add_comment', methods=['POST'])
def add_comment():
    '''Adds a comment to the course'''
    course = session.get('course')
    comment = request.form.get('comment-input').strip()

    for i in comment.split():
        if i in swears:
            comment = comment.replace(i, '*'*len(i))

    if comment:
        if not request.form.get('anonymous'):
            courses_db.update_one({'name': course},\
            {'$push': {'comments': [(session['user']['email'], session['user']['name'], comment)]}})
        else:
            courses_db.update_one({'name': course},\
            {'$push': {'comments': [('None', 'Анонімний користувач', comment)]}})

    return redirect(url_for('course_name', course=course))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port) 
