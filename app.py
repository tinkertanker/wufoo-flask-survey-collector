from flask import Flask, render_template, redirect, url_for, request, flash
import sqlite3
import os
import pandas as pd
from werkzeug.utils import secure_filename
from flask_restful import Resource, Api
from flask_login import LoginManager,login_required,login_user,logout_user,UserMixin


app = Flask(__name__, template_folder='Templates')
app.config["SECRET_KEY"] = "mysecretkey"

api = Api(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

def get_db():
    db = sqlite3.connect("db.sqlite3")
    db.row_factory = sqlite3.Row
    return db

def create_db():
    db = get_db()
    db.execute("CREATE TABLE surveys" + \
                "(student_index INT, " + \
                "survey TEXT, " + \
                "name TEXT, " + \
                "ability_follow TEXT, " + \
                "ability_complete TEXT," + \
                "pace TEXT," + \
                "problems TEXT," + \
                "additional_qn TEXT," + \
                "PRIMARY KEY(student_index, survey))")
    db.commit()
    db.close()


if not os.path.isfile('db.sqlite3'):
    create_db()

order = ["Strongly Disgree","Disagree","Neutral","Agree","Strongly Agree"]
color = {"Strongly Disgree":"bg-danger",
        "Disagree":"list-group-item-danger",
        "Neutral":"list-group-item-secondary",
        "Agree":"list-group-item-success",
        "Strongly Agree":"bg-success"}

class User(UserMixin):
    def __init__(self, username, password):
        self.username = username
        self.password = password

users = [User("username","password")]

@login_manager.user_loader
def load_user(user_id):
    for user in users:
        if user.username == user_id:
            user_object = user
            return user_object
            break
        else:
            user_object = None
            return user_object

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("pwd")
        for user in users:
            if user.username == username and user.password == password:
                user.id = username
                login_user(user)
                flash("Logged in successfully")

                next = request.args.get("next")

                if next == None or not next[0]=="/":
                    next = url_for("home")

                return redirect(next)

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route("/lesson", methods=["GET","POST"])
def lesson_page():
    if request.method == "POST":
        lesson_number = request.form.get("lesson_number")
        survey_lesson = "swift-accelerator-2020-"+str(lesson_number)+"-attendance-exit-survey_entries"
        db = get_db()
        cursor = db.execute("SELECT COUNT(ability_follow),ability_follow FROM surveys WHERE survey = ? GROUP BY ability_follow",(survey_lesson,))
        responses_follow = cursor.fetchall()
        cursor = db.execute("SELECT COUNT(ability_complete),ability_complete FROM surveys WHERE survey = ? GROUP BY ability_complete",(survey_lesson,))
        responses_complete = cursor.fetchall()
        cursor = db.execute("SELECT COUNT(pace),pace FROM surveys WHERE survey = ? GROUP BY pace",(survey_lesson,))
        responses_pace = cursor.fetchall()
        cursor = db.execute("SELECT problems,student_index FROM surveys WHERE survey = ?",(survey_lesson,))
        responses_problems = []
        all_problems = cursor.fetchall()
        for i in all_problems:
            if i["problems"] != None and len(i["problems"]) > 5:
                responses_problems.append(i)
        cursor = db.execute("SELECT additional_qn,student_index FROM surveys WHERE survey = ?",(survey_lesson,))
        responses_additional = cursor.fetchall()
        missing = []
        for i in range(1,59):
            cursor = db.execute("SELECT * FROM surveys WHERE survey = ? AND student_index = ?",(survey_lesson,i))
            check = cursor.fetchone()
            if check == None:
                missing.append(i)
        db.close()
        return render_template("lesson.html", lesson_number=lesson_number, missing=missing, order=order,color=color, survey_lesson=survey_lesson, responses_follow=responses_follow, responses_complete=responses_complete, responses_pace=responses_pace, responses_problems=responses_problems, responses_additional=responses_additional)
    return render_template("lesson.html")

@app.route("/student", methods=["GET","POST"])
@login_required
def student_page():
    if request.method == "POST":
        student_selected = request.form.get("student_selected")
        db = get_db()
        cursor = db.execute("SELECT COUNT(student_index) FROM surveys WHERE student_index = ?",(student_selected,))
        attendance = cursor.fetchone()[0]
        cursor = db.execute("SELECT survey,ability_follow FROM surveys WHERE student_index = ?",(student_selected,))
        responses_follow = cursor.fetchall()
        cursor = db.execute("SELECT survey,ability_complete FROM surveys WHERE student_index = ?",(student_selected,))
        responses_complete = cursor.fetchall()
        cursor = db.execute("SELECT survey,pace FROM surveys WHERE student_index = ?",(student_selected,))
        responses_pace = cursor.fetchall()
        cursor = db.execute("SELECT problems,survey FROM surveys WHERE student_index = ?",(student_selected,))
        responses_problems = []
        all_problems = cursor.fetchall()
        for i in all_problems:
            if i["problems"] != None and len(i["problems"]) > 5:
                responses_problems.append(i)
        cursor = db.execute("SELECT additional_qn,survey FROM surveys WHERE student_index = ?",(student_selected,))
        responses_additional = cursor.fetchall()
        db.close()
        return render_template("student.html",color=color,student_selected=student_selected,attendance=attendance, responses_follow=responses_follow, responses_complete=responses_complete, responses_pace=responses_pace, responses_problems=responses_problems, responses_additional=responses_additional)
    return render_template("student.html")

@app.route("/upload", methods=["GET","POST"])
@login_required
def upload_page():
    if request.method == "POST":
        csv_file = request.files["file"]
        csv_filename = secure_filename(csv_file.filename)
        #csv_file.save(csv_filename)
        csv_filename = csv_filename[:-4]
        df = pd.read_csv(csv_file)
        for index,row in df.iterrows():
            db = get_db()
            db.text_factory = str
            cursor = db.execute("SELECT * FROM surveys WHERE student_index = ? AND survey = ?",(row[8],csv_filename))
            test = cursor.fetchone()
            if test != None:
                pass
            else:
                cursor = db.execute("INSERT INTO surveys VALUES(?,?,?,?,?,?,?,?)",(row[8],csv_filename,row[9],row[10],row[11],row[12],row[13],row[14]))
                db.commit()
            db.close()
        return redirect(url_for("home"))
    return render_template("upload.html")

@app.route("/table")
@login_required
def table_page():
    db = get_db()
    follow_table = []
    for i in range(1,59):
        temp_list = []
        for j in range(5):
            cursor = db.execute("SELECT COUNT(ability_follow) FROM surveys WHERE student_index=? AND ability_follow=?",(i,order[j]))
            response_counts = cursor.fetchall()
            temp_list.append(response_counts[0])
        follow_table.append(temp_list)
    complete_table = []
    for i in range(1,59):
        temp_list = []
        for j in range(5):
            cursor = db.execute("SELECT COUNT(ability_complete) FROM surveys WHERE student_index=? AND ability_complete=?",(i,order[j]))
            response_counts = cursor.fetchall()
            temp_list.append(response_counts[0])
        complete_table.append(temp_list)
    pace_table = []
    for i in range(1,59):
        temp_list = []
        for j in range(5):
            cursor = db.execute("SELECT COUNT(pace) FROM surveys WHERE student_index=? AND pace=?",(i,order[j]))
            response_counts = cursor.fetchall()
            temp_list.append(response_counts[0])
        pace_table.append(temp_list)
    db.close()
    return render_template("table.html",follow_table=follow_table,complete_table=complete_table,pace_table=pace_table)


class Webhook(Resource):

    def post(self,lesson):
        student_index = request.form.get("Field19")
        name = request.form.get("Field123")
        ability_follow = request.form.get("Field125")
        ability_complete =  request.form.get("Field126")
        pace =  request.form.get("Field127")
        problems =  request.form.get("Field227")
        additional_qn = request.form.get("Field225")
        db = get_db()
        cursor = db.execute("SELECT * FROM surveys WHERE student_index = ? AND survey = ?",(student_index,"swift-accelerator-2020-"+str(lesson)+"-attendance-exit-survey_entries"))
        test = cursor.fetchone()
        if test != None:
                db.close()
        else:
          db = get_db()
          cursor = db.execute("INSERT INTO surveys VALUES(?,?,?,?,?,?,?,?)",(student_index,"swift-accelerator-2020-"+str(lesson)+"-attendance-exit-survey_entries",name,ability_follow,ability_complete,pace,problems,additional_qn))
          db.commit()
          db.close()



api.add_resource(Webhook,"/webhook/<int:lesson>")

if __name__ == "__main__":
    app.run(debug=True)
