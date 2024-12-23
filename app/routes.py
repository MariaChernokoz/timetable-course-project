import psycopg
from flask import request, render_template, redirect, url_for, flash
from app import app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, current_user, logout_user
from app.user import User
from datetime import datetime



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


@app.route('/create-event', methods=["GET", "POST"])
def create_event():
   # (Оставляем код создания события без изменений)
    if request.method == "POST":
        event_name = request.form.get("event_name")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        location = request.form.get("location")
        category = request.form.get("category")  # Будет получать значение из выпадающего списка
        comment = request.form.get("comment")

        user_login = current_user.user_login

        if not event_name or not start_time or not end_time:
            flash("Пожалуйста, заполните все обязательные поля.", "error")
            return redirect(url_for("create_event"))

        try:
            start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
            end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("Некорректный формат даты и времени.", "error")
            return redirect(url_for("create_event"))

        conn = connect_to_db()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO Events (User_login, Event_name, Start_time_and_date, End_time_and_date, Location, Category, Comment)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (user_login, event_name, start_time, end_time, location, category, comment)
            )
            conn.commit()
            return redirect(url_for("my_events"))
        except psycopg.Error as e:
            conn.rollback()
            flash(f"Ошибка базы данных при создании события: {e}", "error")
        finally:
            cur.close()
            conn.close()

    return render_template('create-event.html')


@app.route('/my-events')
def my_events():
    conn = connect_to_db()
    events_by_date = {}  # Используем словарь, где ключ - дата, а значение - список событий
    cur = None
    try:
        cur = conn.cursor()
        # Получите события для текущего пользователя
        cur.execute("SELECT Event_name, Start_time_and_date, End_time_and_date, LOCATION, Category, COMMENT FROM Events WHERE User_login = %s ORDER BY Start_time_and_date",
                    (current_user.user_login,))
        fetched_events = cur.fetchall()

        for event in fetched_events:
            event_date = event[1].date()  # Получаем только дату из Start_time_and_date
            if event_date not in events_by_date:
                events_by_date[event_date] = []  # Если нет ключа, создаем список
            events_by_date[event_date].append(
                (event[0], event[1].strftime('%H:%M'), event[2].strftime('%H:%M'), event[3], event[4], event[5])  # Добавляем event[5] для комментария
            )
    except psycopg.Error as e:
        flash(f"Ошибка базы данных: {e}", "error")
    finally:
        if cur:
            cur.close()
        conn.close()

    return render_template('my-events.html', active_page='my_events', events_by_date=events_by_date)


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


@app.route('/friendsrequests')
def friendsrequests():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    conn = connect_to_db()
    friend_requests_received = []
    friend_requests_sent = []

    if conn:
        cur = conn.cursor()

        # Получаем заявки в друзья, отправленные к текущему пользователю
        cur.execute("SELECT request_id, senders_login FROM FriendRequest WHERE Recipient_login = %s AND Status_request = 'pending'", (current_user.user_login,))
        friend_requests_received = [{'request_id': row[0], 'senders_login': row[1]} for row in cur.fetchall()]

        # Получаем заявки в друзья, отправленные текущим пользователем
        cur.execute("SELECT Recipient_login FROM FriendRequest WHERE senders_login = %s AND Status_request = 'pending'", (current_user.user_login,))
        friend_requests_sent = [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()

    return render_template('friendsrequests.html',
                           active_page='friendsrequests',
                           friend_requests=friend_requests_received,
                           friend_requests_sent=friend_requests_sent)

@app.route('/accept_friend_request/<int:request_id>', methods=['POST'])
def accept_friend_request(request_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    conn = connect_to_db()

    if conn:
        cur = conn.cursor()

        # Получаем информацию о запросе
        cur.execute("SELECT senders_login FROM FriendRequest WHERE request_id = %s", (request_id,))
        sender = cur.fetchone()

        if sender:
            sender_login = sender[0]

            # Создаем запись о дружбе (двусторонняя дружба)
            cur.execute("INSERT INTO Friendships (senders_login, recipient_login) VALUES (%s, %s)", (sender_login, current_user.user_login))
            cur.execute("INSERT INTO Friendships (senders_login, recipient_login) VALUES (%s, %s)", (current_user.user_login, sender_login))
            conn.commit()

            # Обновляем статус заявки на 'accepted'
            cur.execute("UPDATE FriendRequest SET Status_request = 'accepted' WHERE request_id = %s", (request_id,))
            conn.commit()

            flash(f"Вы приняли заявку от {sender_login} в друзья!", "success")
        else:
            flash("Заявка не найдена.", "danger")

        cur.close()
        conn.close()
    else:
        flash("Ошибка подключения к базе данных", "danger")

    return redirect(url_for('friendsrequests'))

@app.route('/decline_friend_request/<int:request_id>', methods=['POST'])
def decline_friend_request(request_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    conn = connect_to_db()

    if conn:
        cur = conn.cursor()

        # Удаляем заявку
        cur.execute("DELETE FROM FriendRequest WHERE request_id = %s", (request_id,))
        conn.commit()

        flash("Заявка была отклонена.", "info")

        cur.close()
        conn.close()
    else:
        flash("Ошибка подключения к базе данных", "danger")

    return redirect(url_for('friendsrequests'))

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

@app.route('/search_friend', methods=['POST'])
def search_friend():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    friend_login = request.form['friend_login']
    conn = connect_to_db()
    search_result = None
    friends_list = []  # Инициализируйте список друзей

    if conn:
        cur = conn.cursor()

        # Получаем список друзей текущего пользователя для отображения
        cur.execute("SELECT recipient_login FROM friendships WHERE senders_login = %s", (current_user.user_login,))
        friends_list = cur.fetchall()

        # Проверяем, существует ли пользователь с логином friend_login
        cur.execute("SELECT user_login FROM users WHERE user_login = %s", (friend_login,))
        user = cur.fetchone()

        if user:
            user_login = user[0]

            # Проверяем, есть ли этот пользователь в друзьях
            cur.execute("SELECT COUNT(*) FROM friendships WHERE (senders_login = %s AND recipient_login = %s) OR (senders_login = %s AND recipient_login = %s)",
                        (current_user.user_login, user_login, user_login, current_user.user_login))
            is_friend = cur.fetchone()[0] > 0

            search_result = {
                'user_login': user_login,
                'is_friend': is_friend
            }
        else:
            flash(f"Пользователь {friend_login} не найден.", "danger")

        cur.close()
        conn.close()

    return render_template('friends.html', active_page='friends', friends=friends_list, search_result=search_result)


@app.route('/send_friend_request/<recipient_login>', methods=['POST'])
def send_friend_request(recipient_login):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    # Проверка, пытается ли пользователь отправить заявку самому себе
    if current_user.user_login == recipient_login:
        error = "Вы не можете отправить запрос самому себе."
        return render_template('friendsrequests.html', error=error, active_page='friendsrequests')

    conn = connect_to_db()
    if conn:
        cur = conn.cursor()

        # Проверка на существование входящей заявки
        cur.execute(
            "SELECT 1 FROM FriendRequest WHERE senders_login = %s AND Recipient_login = %s AND Status_request = 'pending'",
            (recipient_login, current_user.user_login)
        )
        incoming_request_exists = cur.fetchone() is not None

        # Проверка на существование исходящей заявки
        cur.execute(
            "SELECT 1 FROM FriendRequest WHERE senders_login = %s AND Recipient_login = %s AND Status_request = 'pending'",
            (current_user.user_login, recipient_login)
        )
        outgoing_request_exists = cur.fetchone() is not None

        error = None

        if incoming_request_exists:
            error = "Пользователь уже отправил вам запрос на дружбу."
        elif outgoing_request_exists:
            error = "Вы уже отправили запрос на дружбу этому пользователю."
        else:
            # Если заявки не существуют, выполняем вставку
            cur.execute(
                "INSERT INTO FriendRequest (senders_login, Recipient_login, Status_request) "
                "VALUES (%s, %s, 'pending') RETURNING request_id;",
                (current_user.user_login, recipient_login)
            )
            conn.commit()
            request_id = cur.fetchone()[0]
            success_message = "Запрос на дружбу успешно отправлен."

            # Возвращение к списку заявок с сообщением об успехе
            return render_template('friends.html', success=success_message, active_page='friends')

        # Если ошибка есть, возвращаем её на страницу
        cur.close()
        conn.close()
        return render_template('friends.html', error=error, active_page='friends')

    return redirect(url_for('friends'))