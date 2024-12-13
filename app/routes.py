from app import app
from flask import Flask, request, render_template, redirect, url_for, flash, blueprints
import psycopg

from passlib.hash import bcrypt

'''@app.route('/')
def login():
    return render_template('main.html')'''

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        login = request.form["login"]
        password = request.form["password"]

        conn = connect_to_db()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE user_login = %s AND password = %s", (login, password))
            user = cur.fetchone()
            cur.close()
            conn.close()

            if user:
                flash(f"Добро пожаловать в Расписание, {user[1]}!", "success")
                return redirect(url_for("base"))
            else:
                error = "Ошибка ввода логина или пароля"

    return render_template("main.html", error=error)


#@app.route('/testdb')
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
    '''finally:
        if con:
            con.close()'''




@app.route("/registration", methods=["GET", "POST"])
def registration():
    error = None
    if request.method == "POST":
        login = request.form.get("login")
        password = request.form.get("password")

        if not login or not password:
            flash("Пожалуйста, заполните все поля.", "error")
            return render_template("registration.html")

        conn = connect_to_db()
        if conn:
            cur = conn.cursor()
            try:
                cur.execute("INSERT INTO users (user_login, password) VALUES (%s, %s)", (login, password))
                conn.commit()
                flash("Регистрация прошла успешно!", "success")
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

