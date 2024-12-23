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

'''
@app.route('/friends')
def friends():
   return render_template('friends.html', active_page = 'friends')
'''


@app.route('/todos', methods=['GET', 'POST'])
def todos():
    if request.method == 'POST':
        task_name = request.form.get('task_name')
        deadline = request.form.get('deadline')  # Дата может быть пустой
        user_login = current_user.user_login

        if not task_name:
            flash("Пожалуйста, введите название задачи.", "error")
            return redirect(url_for('todos'))

        conn = connect_to_db()
        if conn:
            cur = conn.cursor()
            try:
                # Если deadline не указан, используем None
                if not deadline:
                    deadline = None

                cur.execute(
                    "INSERT INTO Tasks (User_login, Task_name, Creation_date, Deadline, Task_status) VALUES (%s, %s, NOW(), %s, %s)",
                    (user_login, task_name, deadline, 'Новая')
                )
                conn.commit()
                #flash("Задача успешно добавлена!", "success")
                return redirect(url_for('todos'))
            except psycopg.Error as e:
                conn.rollback()
                flash(f"Ошибка базы данных: {e}", "error")
            finally:
                cur.close()
                conn.close()

    # Получаем список задач текущего пользователя
    tasks = []
    conn = connect_to_db()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT Task_name, Deadline FROM Tasks WHERE User_login = %s", (current_user.user_login,))
        fetched_tasks = cur.fetchall()

        # Форматируем дату и время перед передачей в шаблон
        tasks = [(task[0], task[1].strftime('%Y-%m-%d %H:%M') if task[1] else '') for task in fetched_tasks]

        cur.close()
        conn.close()

    return render_template('todos.html', active_page='todos', tasks=tasks)


@app.route('/todos/delete/<task_name>', methods=['POST'])
def delete_task(task_name):
    conn = connect_to_db()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM Tasks WHERE User_login = %s AND Task_name = %s",
                        (current_user.user_login, task_name))
            conn.commit()
            flash("Задача успешно удалена!", "success")
        except psycopg.Error as e:
            conn.rollback()
            flash(f"Ошибка базы данных: {e}", "error")
        finally:
            cur.close()
            conn.close()
    return redirect(url_for('todos'))


@app.route('/shared-events')
def shared_events():
   return render_template('shared-events.html', active_page = 'shared_events')


@app.route('/add_friend/<friend_login>', methods=['POST'])
def add_friend(friend_login):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    conn = connect_to_db()
    if conn:
        cur = conn.cursor()

        # Проверяем, существует ли пользователь с логином friend_login
        cur.execute("SELECT COUNT(*) FROM users WHERE user_login = %s", (friend_login,))
        user_exists = cur.fetchone()[0] > 0

        if not user_exists:
            flash(f"Пользователь {friend_login} не найден.", "danger")
            cur.close()
            conn.close()
            return redirect(url_for('friends'))

        # Добавляем запись о дружбе в таблицу friendships
        cur.execute("INSERT INTO friendships (senders_login, recipient_login) VALUES (%s, %s)",
                    (current_user.user_login, friend_login))
        conn.commit()
        cur.close()
        conn.close()
        flash(f"Вы добавили {friend_login} в друзья!", "success")
    else:
        flash("Ошибка подключения к базе данных", "danger")

    return redirect(url_for('friends'))


# Отображение списка друзей
@app.route('/friends')
def friends():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    conn = connect_to_db()
    friends_list = []
    if conn:
        cur = conn.cursor()
        # Получаем список друзей текущего пользователя
        cur.execute("SELECT recipient_login FROM friendships WHERE senders_login = %s", (current_user.user_login,))
        friends_list = cur.fetchall()
        cur.close()
        conn.close()

    return render_template('friends.html', active_page='friends', friends=friends_list)