import psycopg
from flask import request, render_template, redirect, url_for, flash
from app import app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, current_user, logout_user
from app.user import User



def connect_to_db():
    con = 0
    try:
        con = psycopg.connect(host=app.config['POSTGRES_HOST'],
                              user=app.config['POSTGRES_USER'],
                              password=app.config['POSTGRES_PASSWORD'],
                              dbname=app.config['POSTGRES_DB'])
    except Exception as e:
        message = f"Ошибка подключения: {e}"
    else:
        return con

@app.route("/", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('base'))
    error = None
    if request.method == "POST":
        user_login = request.form["login"]
        password = request.form["password"]

        conn = connect_to_db()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE user_login = %s", (user_login,))
            user = cur.fetchone()
            cur.close()
            conn.close()

            if user and check_password_hash(user[1], password):
                user_object = User(user_login,password)
                login_user(user_object)
                print(user_login)
                #flash(f"Добро пожаловать в Расписание, {current_user.user_login}!", "success")
                return redirect(url_for("base"))
            else:
                error = "Ошибка ввода логина или пароля"

    return render_template("main.html", error=error)

@app.route('/logout', methods=['GET'])
def logout():
    logout_user()
    #flash("Вы успешно вышли из системы!", "success")
    return redirect(url_for('login'))

@app.route("/registration", methods=["GET", "POST"])
def registration():
    error = None
    if request.method == "POST":
        login = request.form.get("login")
        password = generate_password_hash(request.form["password"])

        if not login or not password:
            flash("Пожалуйста, заполните все поля.", "error")
            return render_template("registration.html")

        conn = connect_to_db()
        if conn:
            cur = conn.cursor()
            try:
                cur.execute("INSERT INTO users (user_login, password) VALUES (%s, %s)", (login, password))
                conn.commit()
                #flash("Регистрация прошла успешно!", "success")
                return redirect(url_for("login"))
            except psycopg.IntegrityError as e:
                conn.rollback()
                error = "Пользователь с таким логином уже существует."
            except psycopg.Error as e:
                conn.rollback()
                flash(f"Ошибка базы данных: {e}", "error")
            finally:
                cur.close()
                conn.close()

    return render_template("registration.html", error=error)

@app.route("/base")
def base():
    return render_template("base.html")

@app.route('/my-events')
def my_events():
    return render_template('my-events.html', active_page = 'my_events')

@app.route('/friends')
def friends():
   return render_template('friends.html', active_page = 'friends')

@app.route('/todos')
def todos():
   return render_template('todos.html', active_page = 'todos')

@app.route('/shared-events')
def shared_events():
   return render_template('shared-events.html', active_page = 'shared_events')
