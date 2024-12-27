import psycopg
from flask import request, render_template, redirect, url_for, flash
from app import app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, current_user, logout_user
from app.user import User
from datetime import datetime, timedelta, timezone
import pytz

user_timezone = pytz.timezone('Europe/Moscow')


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
        password = request.form.get("password")

        # Проверяем введенные данные
        if not login or not password:
            flash("Пожалуйста, заполните все поля.", "error")
            return render_template("registration.html")

        # Ограничения на длину
        if len(login) > 20:
            flash("Логин не должен превышать 20 символов.", "error")
            return render_template("registration.html")

        if len(password) > 50:
            flash("Пароль не должен превышать 50 символов.", "error")
            return render_template("registration.html")

        # Генерация хеша пароля
        hashed_password = generate_password_hash(password)

        conn = connect_to_db()
        if conn:
            cur = conn.cursor()
            try:
                cur.execute("INSERT INTO users (user_login, password) VALUES (%s, %s)", (login, hashed_password))
                conn.commit()
                return redirect(url_for("login"))
            except psycopg.IntegrityError:
                conn.rollback()
                error = "Пользователь с таким логином уже существует."
            except psycopg.Error:
                conn.rollback()
                flash("Ошибка базы данных.", "error")
            finally:
                cur.close()
                conn.close()

    return render_template("registration.html", error=error)

@app.route("/base")
def base():
    return render_template("base.html")

from datetime import datetime

@app.route('/create-event', methods=["GET", "POST"])
def create_event():
    if request.method == "POST":
        event_name = request.form.get("event_name")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        location = request.form.get("location")
        category = request.form.get("category")
        comment = request.form.get("comment")
        is_regular = request.form.get("is_regular")  # Получаем значение чекбокса
        regularity_interval = request.form.get("regularity_interval")
        days_of_week = request.form.get("days_of_week")
        end_repeat = request.form.get("end_repeat")  # Получаем дату окончания повторений

        user_login = current_user.user_login

        # Проверка обязательных полей
        if not event_name or not start_time or not end_time:
            flash("Пожалуйста, заполните все обязательные поля.", "error")
            return redirect(url_for("create_event"))

        # Проверка форматирования дней недели
        if days_of_week and not all(day in '1234567' for day in days_of_week):
            flash("Некорректный формат дней недели. Используйте только цифры от 1 до 7.", "error")
            return redirect(url_for("create_event"))

        # Проверка длины названия события
        if event_name and len(event_name) > 30:
            flash("Название события не должно превышать 30 символов.", "error")
            return redirect(url_for("create_event"))

        # Проверка длины места
        if location and len(location) > 30:
            flash("Место не должно превышать 30 символов.", "error")
            return redirect(url_for("create_event"))

        # Проверка длины комментария
        if comment and len(comment) > 30:
            flash("Комментарий не должен превышать 30 символов.", "error")
            return redirect(url_for("create_event"))
        try:
            # Локализуем время начала и окончания с учетом часового пояса пользователя
            start_time = user_timezone.localize(datetime.strptime(start_time, "%Y-%m-%dT%H:%M"))
            end_time = user_timezone.localize(datetime.strptime(end_time, "%Y-%m-%dT%H:%M"))

            if end_repeat:
                end_repeat = user_timezone.localize(datetime.strptime(end_repeat, "%Y-%m-%dT%H:%M"))

            # Проверка, не находится ли время в прошлом и время окончания больше времени начала
            if start_time < datetime.now(user_timezone):
                flash("Время начала не может быть в прошлом.", "error")
                return redirect(url_for("create_event"))

            if end_time <= start_time:
                flash("Время окончания должно быть позже времени начала.", "error")
                return redirect(url_for("create_event"))
        except ValueError:
            flash("Некорректный формат даты и времени.", "error")
            return redirect(url_for("create_event"))

        conn = connect_to_db()
        try:
            cur = conn.cursor()

            regularity_id = None  # Инициализация переменной
            # Если событие регулярное, сначала создаем регулярность.
            if is_regular:
                # Проверка: не раньше ли дата и время конца события
                if end_repeat < end_time:
                    # Если условия не соблюдены, обрабатываем ошибку.
                    flash("Конец повторений должна быть позже времени окончания события.", "error")
                    return redirect(url_for("create_event"))

                cur.execute(
                    """
                    INSERT INTO Regularity (Regularity_interval, Days_of_week, End_date)
                    VALUES (%s, %s, %s) RETURNING Regularity_ID
                    """,
                    (regularity_interval, days_of_week, end_repeat)
                )
                regularity_id = cur.fetchone()[0]  # Получение созданного Regularity_ID

                # Создание основного события с привязкой к Regularity_ID
                cur.execute(
                    """
                    INSERT INTO Events (User_login, Event_name, Start_time_and_date, End_time_and_date, Location, Category, Comment, Regularity_ID)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING Event_ID
                    """,
                    (user_login, event_name, start_time, end_time, location, category, comment, regularity_id)
                )
            else:
                # Если событие не регулярное, просто создаем его
                cur.execute(
                    """
                    INSERT INTO Events (User_login, Event_name, Start_time_and_date, End_time_and_date, Location, Category, Comment)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING Event_ID
                    """,
                    (user_login, event_name, start_time, end_time, location, category, comment)
                )

            event_id = cur.fetchone()[0]  # Получение созданного Event_ID

            # Если событие регулярное, создаем его экземпляры
            if is_regular:
                current_event_start_time = start_time
                current_event_end_time = end_time
                current_event_start_time += timedelta(weeks=int(regularity_interval))
                current_event_end_time += timedelta(weeks=int(regularity_interval))
                while current_event_start_time <= end_repeat:
                    cur.execute(
                        """
                        INSERT INTO Events (User_login, Event_name, Start_time_and_date, End_time_and_date, Location, Category, Comment, Regularity_ID)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (user_login, event_name, current_event_start_time, current_event_end_time, location, category, comment, regularity_id)
                    )
                    current_event_start_time += timedelta(weeks=int(regularity_interval))  # Увеличиваем на интервал
                    current_event_end_time += timedelta(weeks=int(regularity_interval))

            conn.commit()
            return redirect(url_for("my_events"))

        except psycopg.Error as e:
            conn.rollback()
            flash(f"Ошибка базы данных при создании события", "error")
            return redirect(url_for("my_events"))  # Перенаправление на страницу со списком событий

        finally:
            cur.close()
            conn.close()

    return render_template('create-event.html', active_page='my_events')

import datetime
from datetime import datetime
import pytz
from datetime import datetime, timedelta

#
#_____ОТОБРАЖЕНИЕ ОБЫЧНЫХ СОБЫТИЙ СОВМЕЩЕННЫХ С СОВМЕСТНЫМИ СОБЫТИЯМИ______
@app.route('/my-events')
def my_events():

    conn = connect_to_db()
    events_by_date = {}
    cur = None
    participant = None
    is_shared_event = False
    user_timezone = pytz.timezone('Europe/Moscow')
    current_time = datetime.now(user_timezone)  # Теперь это offset-aware время
    #current_time = datetime.datetime.now()  # Получаем текущее время с часовым поясом UTC
    #is_shared_event = False  # Переменная для проверки наличия совместных событий

    try:
        cur = conn.cursor()
        event_id = None

        # Получение событий пользователя
        cur.execute("""
            SELECT Event_ID, Event_name, Start_time_and_date, End_time_and_date, Location, Category, Comment, regularity_id
            FROM Events WHERE User_login = %s ORDER BY Start_time_and_date
        """, (current_user.user_login,))

        fetched_events = cur.fetchall()
        for event in fetched_events:
            event_id, event_name, start_time, end_time, location, category, comment, regularity_id = event

            # Преобразуем start_time и end_time в часовой пояс пользователя
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=pytz.utc).astimezone(user_timezone)
            else:
                start_time = start_time.astimezone(user_timezone)

            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=pytz.utc).astimezone(user_timezone)
            else:
                end_time = end_time.astimezone(user_timezone)

            # Проверяем, прошел ли уже срок события
            if end_time < current_time:
                # Удаляем событие из базы данных, если оно прошло
                cur.execute("DELETE FROM Events WHERE Event_ID = %s AND User_login = %s",
                            (event_id, current_user.user_login))
                conn.commit()
            else:
                # Форматируем даты и время
                if start_time.date() != end_time.date():
                    display_time = f"{start_time.strftime('%Y-%m-%d')} {start_time.strftime('%H:%M')} - " \
                                   f"{end_time.strftime('%Y-%m-%d')} {end_time.strftime('%H:%M')}"
                else:
                    display_time = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

                event_entry = {
                    "id": event_id,
                    "name": event_name,
                    "time": display_time,
                    "location": location,
                    "category": category,
                    "comment": comment,
                    "regularity_id": regularity_id,
                    "is_shared_event": False,
                    "user-login": participant
                }

                event_date = start_time.date()  # Получаем только дату из Start_time_and_date
                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                events_by_date[event_date].append(event_entry)  # Добавляем запись события

        # Получение совместных событий
        cur.execute("""
            SELECT se.Shared_event_ID, se.Shared_event_name, se.Start_time_and_date, se.End_time_and_date, 
                   se.Location, se.Category, se.Comment, se.regularity_id
            FROM SharedEvents AS se
            INNER JOIN JointSharedEventParticipation AS jp ON se.Shared_event_ID = jp.Shared_event_ID
            WHERE jp.User_login = %s
            ORDER BY se.Start_time_and_date
        """, (current_user.user_login,))

        fetched_shared_events = cur.fetchall()

        for event in fetched_shared_events:
            event_id, event_name, start_time, end_time, location, category, comment, regularity_id = event

            # Преобразуем start_time и end_time в часовой пояс пользователя
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=pytz.utc).astimezone(user_timezone)
            else:
                start_time = start_time.astimezone(user_timezone)

            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=pytz.utc).astimezone(user_timezone)
            else:
                end_time = end_time.astimezone(user_timezone)

            # Получение 'совместно с ...'
            cur.execute("""
                SELECT User_login
                FROM JointSharedEventParticipation AS jp 
                WHERE jp.Shared_event_ID = %s AND User_login != %s
            """, (event_id, current_user.user_login))

            participants = cur.fetchall()
            # Преобразуем список участников в простой список строк
            participant_usernames = [row[0] for row in participants]

            # Проверяем, прошел ли уже срок события
            if end_time < current_time:
                # Удаляем событие из базы данных, если оно прошло
                cur.execute("DELETE FROM Events WHERE Event_ID = %s AND User_login = %s",
                            (event_id, current_user.user_login))
                conn.commit()
            else:
                # Форматируем даты и время для совместных событий
                if start_time.date() != end_time.date():
                    display_time = f"{start_time.strftime('%Y-%m-%d')} {start_time.strftime('%H:%M')} - " \
                                   f"{end_time.strftime('%Y-%m-%d')} {end_time.strftime('%H:%M')}"
                else:
                    display_time = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

                shared_event_entry = {
                    "id": event_id,
                    "name": event_name,
                    "time": display_time,
                    "location": location,
                    "category": category,
                    "comment": comment,
                    "regularity_id": regularity_id,
                    "is_shared_event": True,
                    "user-login": participant_usernames  # Передаем список участников
                }

                event_date = start_time.date()  # Получаем только дату
                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                # Пример проверки на существование записи
                if shared_event_entry not in events_by_date[event_date]:
                    events_by_date[event_date].append(shared_event_entry)


    except psycopg.Error as e:
        flash(f"Ошибка базы данных", "error")
    finally:
        if cur:
            cur.close()
        conn.close()

    return render_template('my-events.html', active_page='my_events', events_by_date=events_by_date)

#____УДАЛЕНИЕ И ОБЫЧНЫХ СОБЫТИЙ, И СОВМЕСТНЫХ_____
@app.route('/events/delete/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    conn = connect_to_db()
    if conn:
        cur = conn.cursor()
        try:
            # Определяем событие совместное или нет
            cur.execute(
                "SELECT COUNT(*) FROM JointSharedEventParticipation WHERE Shared_event_ID = %s AND User_login = %s",
                (event_id, current_user.user_login))
            is_shared_event = cur.fetchone()[0] > 0  # Имеется ли запись в JointSharedEventParticipation с этим Shared_event_ID

            regularity_id = None
            delete_option = request.form.get('delete_option')

            if is_shared_event:  # Это совместное событие
                if delete_option == 'all':
    # ____________________________________
                    # Удаляем все связанные совместные события
                    cur.execute("DELETE FROM JointSharedEventParticipation WHERE Shared_event_ID = %s", (event_id,))
                    cur.execute("DELETE FROM SharedEvents WHERE Shared_event_ID = %s", (event_id,))
                    flash("Все совместные события успешно удалены!", "success")
                elif delete_option == 'single':
                    # Удаляем само совместное событие
                    cur.execute("DELETE FROM JointSharedEventParticipation WHERE Shared_event_ID = %s AND User_login = %s",
                               (event_id, current_user.user_login))
                    flash("Совместное событие успешно удалено!", "success")
    # ____________________________________
                elif delete_option == 'delete_for_self':
                    # Удаляем только у себя из JointSharedEventParticipation
                    cur.execute("DELETE FROM JointSharedEventParticipation WHERE Shared_event_ID = %s AND User_login = %s",
                               (event_id, current_user.user_login))
                    flash("Вы успешно удалили свое участие в совместном событии!", "success")
                elif delete_option == 'delete_for_all':
                    # Удаляем участие пользователя и другие записи
                    cur.execute("DELETE FROM JointSharedEventParticipation WHERE Shared_event_ID = %s", (event_id,))
                    flash("Вы удалили событие для себя и для остальных участников!", "success")

            else:  # Это обычное событие
                cur.execute("SELECT Regularity_ID FROM Events WHERE Event_ID = %s", (event_id,))
                regularity_id = cur.fetchone()

                if regularity_id:
                    if delete_option == 'all':
                        cur.execute("DELETE FROM Events WHERE Regularity_ID = %s", (regularity_id[0],))
                        flash("Все повторяющиеся события успешно удалены!", "success")
                    else:
                        # Удаляем только это событие
                        cur.execute("DELETE FROM Events WHERE User_login = %s AND Event_ID = %s",
                                    (current_user.user_login, event_id))
                        flash("Событие успешно удалено!", "success")
                else:
                    # Удаляем только это событие, если Regularity_ID нет
                    cur.execute("DELETE FROM Events WHERE User_login = %s AND Event_ID = %s",
                                (current_user.user_login, event_id))
                    flash("Событие успешно удалено!", "success")

            conn.commit()
        except psycopg.Error as e:
            conn.rollback()
            flash(f"Ошибка базы данных: {str(e)}", "error")
        finally:
            cur.close()
            conn.close()

    return redirect(url_for('my_events'))

@app.route('/edit-event/<int:event_id>', methods=["GET", "POST"])
def edit_event(event_id):
    conn = connect_to_db()
    if conn:
        cur = conn.cursor()
        participant = None
        is_shared_event = False
        user_timezone = pytz.timezone('Europe/Moscow')
        current_time = datetime.now(user_timezone)
        if request.method == 'POST':
            # Получаем данные из формы
            event_name = request.form.get('event_name')
            event_category = request.form.get('category')
            event_start_time_str = request.form.get('start_time')
            event_end_time_str = request.form.get('end_time')
            event_location = request.form.get('location')
            event_comment = request.form.get('comment')
            is_regular = request.form.get("is_regular")  # Чекбокс: регулярное событие или нет
            regularity_interval = request.form.get("regularity_interval")
            days_of_week = request.form.get("days_of_week")
            end_repeat_str = request.form.get("end_repeat")  # Дата окончания повторений

            #user_timezone = pytz.timezone('Europe/Moscow')  # Замените на нужный вам часовой пояс

            try:
                event_start_time = user_timezone.localize(datetime.strptime(event_start_time_str, "%Y-%m-%dT%H:%M"))
                event_end_time = user_timezone.localize(datetime.strptime(event_end_time_str, "%Y-%m-%dT%H:%M"))


                if end_repeat_str:
                    end_repeat = user_timezone.localize(datetime.strptime(end_repeat_str, "%Y-%m-%dT%H:%M"))
                else:
                    end_repeat = None

                if is_regular:
                    # Проверка: не ранее ли дата и время конца события
                    if end_repeat and end_repeat < event_end_time:
                        flash("Конец повторений должен быть позже времени окончания события.", "error")
                        return redirect(url_for("edit_event", event_id=event_id))

                    # Обновление или создание записи регулярности
                    cur.execute("""
                        INSERT INTO Regularity (Regularity_interval, Days_of_week, End_date)
                        VALUES (%s, %s, %s) 
                        ON CONFLICT (Regularity_ID) DO UPDATE
                        SET Regularity_interval = excluded.Regularity_interval,
                            Days_of_week = excluded.Days_of_week,
                            End_date = excluded.End_date
                        RETURNING Regularity_ID
                    """, (regularity_interval, days_of_week, end_repeat))

                    regularity_id = cur.fetchone()[0]

                    # Обновляем событие с привязкой к Regularity_ID
                    cur.execute("""
                        UPDATE Events
                        SET Event_name = %s, Category = %s, Start_time_and_date = %s, End_time_and_date = %s,
                            Location = %s, Comment = %s, Regularity_ID = %s
                        WHERE Event_ID = %s AND User_login = %s
                    """, (event_name, event_category, event_start_time, event_end_time, event_location,
                          event_comment, regularity_id, event_id, current_user.user_login))

                else:
                    # Если событие не регулярное, обновляем без изменения Regularity_ID
                    cur.execute("""
                        UPDATE Events
                        SET Event_name = %s, Category = %s, Start_time_and_date = %s, End_time_and_date = %s,
                            Location = %s, Comment = %s, Regularity_ID = NULL
                        WHERE Event_ID = %s AND User_login = %s
                    """, (event_name, event_category, event_start_time, event_end_time, event_location,
                          event_comment, event_id, current_user.user_login))
                conn.commit()
                flash("Событие успешно обновлено!", "success")
            except ValueError:
                flash("Некорректный формат даты и времени.", "error")
            except psycopg.Error as e:
                conn.rollback()
                flash(f"Ошибка базы данных: {str(e)}", "error")
            finally:
                cur.close()
                conn.close()

            return redirect(url_for('my_events'))
        else:
            # Получаем текущее состояние события для отображения в форме
            cur.execute("""
                SELECT Event_name, Category, Start_time_and_date, End_time_and_date, Location, Comment, Regularity_ID
                FROM Events WHERE Event_ID = %s
                """, (event_id,))

            event = cur.fetchone()

            if event:  # Проверяем, существует ли событие
                event_name, category, start_time, end_time, location, comment, regularity_id = event

                # Преобразуем start_time и end_time в часовой пояс пользователя
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=pytz.utc).astimezone(user_timezone)
                else:
                    start_time = start_time.astimezone(user_timezone)

                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=pytz.utc).astimezone(user_timezone)
                else:
                    end_time = end_time.astimezone(user_timezone)

                # Проверяем, прошел ли уже срок события
                if end_time < current_time:
                    # Удаляем событие из базы данных, если оно прошло
                    cur.execute("DELETE FROM Events WHERE Event_ID = %s AND User_login = %s",
                                (event_id, current_user.user_login))
                    conn.commit()
                    flash("Событие было удалено, так как оно прошло!", "info")
                    return redirect(url_for('my_events'))

                # Форматируем даты и время
                if start_time.date() != end_time.date():
                    display_time = f"{start_time.strftime('%Y-%m-%d')} {start_time.strftime('%H:%M')} - " \
                                   f"{end_time.strftime('%Y-%m-%d')} {end_time.strftime('%H:%M')}"
                else:
                    display_time = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

                # Получаем данные регулярности, если они есть
                if regularity_id:  # Если Regularity_ID существует
                    cur.execute("""
                            SELECT Regularity_interval, Days_of_week, End_date
                            FROM Regularity WHERE Regularity_ID = %s
                        """, (regularity_id,))
                    regularity = cur.fetchone()
                else:
                    regularity = None

                return render_template('edit-event.html', event=event, regularity=regularity, display_time=display_time)

            else:
                flash("Событие не найдено!", "error")
                return redirect(url_for('my_events'))

    return render_template('edit-event.html', active_page='my_events')

@app.route('/todos', methods=['GET', 'POST'])
def todos():
    current_datetime = datetime.now().replace(tzinfo=None)  # Оставляем как datetime
    if request.method == 'POST':
        task_name = request.form.get('task_name')
        deadline_date = request.form.get('deadline')
        deadline_time = request.form.get('time')
        user_login = current_user.user_login

        if not task_name:
            flash("Пожалуйста, введите название задачи.", "error")
            return redirect(url_for('todos'))

        if len(task_name) > 60:
            flash("Название задачи не может превышать 60 символов.", "error")
            return redirect(url_for('todos'))

        conn = connect_to_db()
        if conn:
            cur = conn.cursor()
            try:
                if not deadline_date or not deadline_time:
                    deadline = None
                else:
                    deadline_str = f"{deadline_date} {deadline_time}"
                    deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M").replace(tzinfo=None)

                cur.execute(
                    "INSERT INTO Tasks (User_login, Task_name, Creation_date, Deadline, Task_status) VALUES (%s, %s, NOW(), %s, %s) RETURNING taskid",
                    (user_login, task_name, deadline, 'Новая')
                )
                taskid = cur.fetchone()[0]
                conn.commit()
                flash("Задача успешно добавлена!", "success")
                return redirect(url_for('todos'))
            except psycopg.Error as e:
                conn.rollback()
                flash(f"Ошибка базы данных: {e}", "error")
            finally:
                cur.close()
                conn.close()

    # Получаем список задач
    tasks = []
    conn = connect_to_db()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT Taskid, Task_name, Deadline FROM Tasks WHERE User_login = %s", (current_user.user_login,))
        fetched_tasks = cur.fetchall()

        for task in fetched_tasks:
            taskid, task_name, deadline = task
            if deadline is not None:
                deadline_date = deadline.replace(tzinfo=None)
            else:
                deadline_date = None
            tasks.append((taskid, task_name, deadline_date))

        cur.close()
        conn.close()

    return render_template('todos.html', active_page='todos', tasks=tasks, current_datetime=current_datetime)

@app.route('/todos/delete/<int:taskid>', methods=['POST'])
def delete_task(taskid):
    conn = connect_to_db()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM Tasks WHERE User_login = %s AND Taskid = %s",
                        (current_user.user_login, taskid))
            conn.commit()
            flash("Задача успешно удалена!", "success")
        except psycopg.Error as e:
            conn.rollback()
            flash(f"Ошибка базы данных", "error")
        finally:
            cur.close()
            conn.close()
    return redirect(url_for('todos'))

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
            flash("Заявка не найдена.", "error")

        # Получаем актуальный список

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

@app.route('/cancel_friend_request/<recipient_login>', methods=['POST'])
def cancel_friend_request(recipient_login):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    conn = connect_to_db()

    if conn:
        cur = conn.cursor()

        # Логика для отмены запроса
        cur.execute("DELETE FROM FriendRequest WHERE recipient_login = %s", (recipient_login,))
        conn.commit()

        flash("Запрос на дружбу был отменен.", "info")

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
            flash(f"Пользователь {friend_login} не найден.", "error")
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

@app.route('/remove_friend/<friend_login>', methods=['POST'])
def remove_friend(friend_login):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    conn = connect_to_db()
    if conn:
        cur = conn.cursor()

        #двунаправленное удаление
        # *** OR позволяет удалить запись о дружбе в любом из двух случаев ***

        # Удаляем запись о дружбе из таблицы friendships
        cur.execute("""
            DELETE FROM friendships 
            WHERE (senders_login = %s AND recipient_login = %s) OR 
                  (senders_login = %s AND recipient_login = %s)
        """, (current_user.user_login, friend_login, friend_login, current_user.user_login))
        conn.commit()

        # Удаляем запись о запросе на дружбу из таблицы friendrequest
        cur.execute("""
                    DELETE FROM friendrequest
                    WHERE (senders_login = %s AND recipient_login = %s) OR 
                          (senders_login = %s AND recipient_login = %s)
                """, (current_user.user_login, friend_login, friend_login, current_user.user_login))
        conn.commit()


        # Проверяем, если запись была удалена
        if cur.rowcount > 0:
            flash(f"Вы удалили {friend_login} из друзей!", "success")
        else:
            flash(f"Не удалось удалить {friend_login} из друзей.", "error")

        cur.close()
        conn.close()
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
    error = None
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

            # Проверяем, не пытается ли пользователь добавить самого себя
            if current_user.user_login == user_login:
                search_result = {
                    'user_login': user_login,
                    'is_friend': is_friend,
                    'error_message': "Вы не можете отправить запрос самому себе."
                }
            else:
                search_result = {
                    'user_login': user_login,
                    'is_friend': is_friend
                }
        else:
            search_result = {
                'error_message': f"Пользователь {friend_login} не найден."
            }

        cur.close()
        conn.close()

    return render_template('friends.html', active_page='friends', friends=friends_list, search_result=search_result)

@app.route('/send_friend_request/<recipient_login>', methods=['POST'])
def send_friend_request(recipient_login):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    if current_user.user_login == recipient_login:
        flash("Вы не можете отправить запрос самому себе.", "error")
        return redirect(url_for('friends'))

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

        if incoming_request_exists:
            flash("Пользователь уже отправил вам запрос на дружбу.", "error")
        elif outgoing_request_exists:
            flash("Вы уже отправили запрос на дружбу этому пользователю.", "error")
        else:
            # Если заявки не существуют, выполняем вставку
            cur.execute(
                "INSERT INTO FriendRequest (senders_login, Recipient_login, Status_request) "
                "VALUES (%s, %s, 'pending') RETURNING request_id;",
                (current_user.user_login, recipient_login)
            )
            conn.commit()
            flash("Запрос на дружбу успешно отправлен.")

        # Получаем актуальный список друзей
        cur.execute("SELECT senders_login FROM Friendships WHERE recipient_login = %s", (current_user.user_login,))
        friends = cur.fetchall()

        cur.close()
        conn.close()

        return render_template('friends.html', friends=friends, active_page='friends')

    return redirect(url_for('friends'))


@app.route('/view-friend-events/<friend_username>')
def view_friend_events(friend_username):
    conn = connect_to_db()
    events_by_date = {}
    cur = None
    current_time = datetime.now(pytz.utc)  # Получаем текущее время с часовым поясом UTC
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT Event_ID, Event_name, Start_time_and_date, End_time_and_date, Location, Category, Comment
            FROM Events WHERE User_login = %s ORDER BY Start_time_and_date
        """, (friend_username,))  # Смотрим события по friend_username в бд

        fetched_events = cur.fetchall()
        for event in fetched_events:
            event_id, event_name, start_time, end_time, location, category, comment = event

            # Преобразуем end_time в UTC, если он не имеет информации о часовом поясе
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=pytz.utc)  # Устанавливаем UTC, если нет информации о часовом поясе

            # Проверяем, прошел ли уже срок события
            if end_time < current_time:
                # Удаляем событие из базы данных, если оно прошло
                cur.execute("DELETE FROM Events WHERE Event_ID = %s AND User_login = %s",
                            (event_id, friend_username))  # Изменено на friend_username
                conn.commit()  # Подтверждаем изменение
            else:
                # Проверяем, начинаются ли события и заканчиваются в разные дни
                if start_time.date() != end_time.date():
                    # Если события в разные дни, формируем строку с датами и временем
                    event_time_display = f"{start_time.date()} {start_time.strftime('%H:%M')} - {end_time.date()} {end_time.strftime('%H:%M')}"
                else:
                    # Если события в один день, просто отображаем время
                    event_time_display = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

                # Обновляем событие в массиве
                event_with_time_display = (event_id, event_name, event_time_display, location, category, comment)
                event_date = start_time.date()  # Получаем только дату из Start_time_and_date
                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                events_by_date[event_date].append(event_with_time_display)  # Добавляем обновленный элемент события

    except psycopg.Error as e:
        flash(f"Ошибка базы данных: {e}", "error")
    finally:
        if cur:
            cur.close()
        conn.close()

    return render_template('view-friend-events.html', active_page='friends', events_by_date=events_by_date, friend_name=friend_username)

@app.route('/request-shared-event/<recipient_login>', methods=["GET", "POST"])
def request_shared_event(recipient_login):
    if request.method == "POST":
        event_name = request.form.get("event_name")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        location = request.form.get("location")
        #СДЕЛАТЬ КАТЕГОРИЮ СОВМЕТНОЙ ДЕФОЛТ
        #category = request.form.get("category")
        category = "Совместное"
        comment = request.form.get("comment")
        request_status = 'pending'

        is_regular = request.form.get("is_regular")  # Получаем значение чекбокса
        regularity_interval = request.form.get("regularity_interval")
        days_of_week = request.form.get("days_of_week")
        end_repeat = request.form.get("end_repeat")  # Получаем дату окончания повторений

        user_login = current_user.user_login

        # Проверка обязательных полей
        if not event_name or not start_time or not end_time:
            flash("Пожалуйста, заполните все обязательные поля.", "error")
            return redirect(url_for("request_shared_event", recipient_login=recipient_login))

        # Проверка форматирования дней недели
        if days_of_week and not all(day in '1234567' for day in days_of_week):
            flash("Некорректный формат дней недели. Используйте только цифры от 1 до 7.", "error")
            return redirect(url_for("request_shared_event", recipient_login=recipient_login))

        # Проверка длины названия события
        if event_name and len(event_name) > 30:
            flash("Название события не должно превышать 30 символов.", "error")
            return redirect(url_for("request_shared_event", recipient_login=recipient_login))

        # Проверка длины места
        if location and len(location) > 30:
            flash("Место не должно превышать 30 символов.", "error")
            return redirect(url_for("request_shared_event", recipient_login=recipient_login))


        # Проверка длины комментария
        if comment and len(comment) > 30:
            flash("Комментарий не должен превышать 30 символов.", "error")
            return redirect(url_for("request_shared_event", recipient_login=recipient_login))

        try:
            start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
            end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")
            if end_repeat:
                end_repeat = datetime.strptime(end_repeat, "%Y-%m-%dT%H:%M")

            # Проверка, не находится ли время в прошлом и время окончания больше времени начала
            if start_time < datetime.now():
                flash("Время начала не может быть в прошлом.", "error")
                return redirect(url_for("request_shared_event", recipient_login=recipient_login))
            if end_time <= start_time:
                flash("Время окончания должно быть позже времени начала.", "error")
                return redirect(url_for("request_shared_event", recipient_login=recipient_login))

        except ValueError:
            flash("Некорректный формат даты и времени.", "error")
            return redirect(url_for("request_shared_event", recipient_login=recipient_login))

        conn = connect_to_db()

        #_______ДОБАВЛЕНИЕ ДАННЫХ В БД_______
        try:
            cur = conn.cursor()
            regularity_id = None  # Инициализация переменной

            # Если событие регулярное, сначала создаем регулярность.
            if is_regular:

                # Проверка: не раньше ли дата и время конца события
                if end_repeat < end_time:
                    # Если условия не соблюдены, обрабатываем ошибку.
                    flash("Конец повторений должна быть позже времени окончания события.", "error")
                    return redirect(url_for("create_event"))

                cur.execute(
                    """
                    INSERT INTO Regularity (Regularity_interval, Days_of_week, End_date)
                    VALUES (%s, %s, %s) RETURNING Regularity_ID
                    """,
                    (regularity_interval, days_of_week, end_repeat)
                )
                regularity_id = cur.fetchone()[0]  # Получение созданного Regularity_ID

                # Создание основного совместного события с привязкой к Regularity_ID
                cur.execute(
                    """
                    INSERT INTO JointSharedEventRequests (Senders_login, Recipient_login, Shared_event_name, Start_time_and_date, End_time_and_date, Regularity_ID, Location, Category, Comment, request_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING request_id;;
                    """,
                    (current_user.user_login, recipient_login, event_name, start_time, end_time, regularity_id, location, category, comment, request_status)
                )
            else:
                # Если событие не регулярное, просто создаем его
                cur.execute(
                    """
                    INSERT INTO JointSharedEventRequests (Senders_login, Recipient_login, Shared_event_name, Start_time_and_date, End_time_and_date, Location, Category, Comment, request_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING request_id;
                    """,
                    (current_user.user_login, recipient_login, event_name, start_time, end_time, location, category, comment, request_status)
                )

            event_id = cur.fetchone()[0]  # Получение созданного Request_ID

            # Если событие регулярное, создаем его экземпляры
            if is_regular:
                current_event_start_time = start_time
                current_event_end_time = end_time
                current_event_start_time += timedelta(weeks=int(regularity_interval))
                current_event_end_time += timedelta(weeks=int(regularity_interval))
                while current_event_start_time <= end_repeat:
                    cur.execute(
                            """
                            INSERT INTO JointSharedEventRequests (Senders_login, Recipient_login, Shared_event_name, Start_time_and_date, End_time_and_date, Regularity_ID, Location, Category, Comment, request_status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING request_id;
                            """,
                        (current_user.user_login, recipient_login, event_name, current_event_start_time, current_event_end_time, regularity_id, location, category, comment, request_status)
                    )
                    current_event_start_time += timedelta(weeks=int(regularity_interval))  # Увеличиваем на интервал
                    current_event_end_time += timedelta(weeks=int(regularity_interval))

            conn.commit()
            return redirect(url_for("shared_events"))

        except psycopg.Error as e:
            conn.rollback()
            flash(f"Ошибка базы данных при создании события: {e}", "error")
            return redirect(url_for("friends"))  # Перенаправление на страницу со списком событий

        finally:
            cur.close()
            conn.close()

    return render_template('request-shared-event.html', active_page='friends')

@app.route('/shared-events')
def shared_events():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    conn = None
    shared_events_requests_received = []
    shared_events_requests_sent = []

    try:
        conn = connect_to_db()
        if conn:
            cur = conn.cursor()

            # Получаем заявки, отправленные к текущему пользователю
            cur.execute(
                "SELECT request_id, senders_login, Shared_event_name, Start_time_and_date, End_time_and_date, LOCATION, comment FROM JointSharedEventRequests WHERE Recipient_login = %s AND request_status = 'pending'",
                (current_user.user_login,))
            received_requests = cur.fetchall()

            # Обрабатываем полученные заявки
            for row in received_requests:
                shared_events_requests_received.append({
                    'request_id': row[0],
                    'senders_login': row[1],
                    'event_name': row[2],
                    'start_time': row[3],
                    'end_time': row[4],
                    'location': row[5],
                    'comment': row[6]
                })

            # Получаем заявки, отправленные текущим пользователем
            cur.execute(
                "SELECT request_id, senders_login, recipient_login, Shared_event_name, Start_time_and_date, End_time_and_date, LOCATION, comment FROM JointSharedEventRequests WHERE senders_login = %s AND request_status = 'pending'",
                (current_user.user_login,))
            sent_requests = cur.fetchall()

            # Обрабатываем отправленные заявки
            for row in sent_requests:
                shared_events_requests_sent.append({
                    'request_id': row[0],
                    'senders_login': row[1],
                    'recipient_login': row[2],
                    'event_name': row[3],
                    'start_time': row[4],
                    'end_time': row[5],
                    'location': row[6],
                    'comment': row[7]
                })

            cur.close()
    except Exception as e:
        flash(f"Ошибка при получении данных: {e}", "error")
    finally:
        if conn:
            conn.close()

    return render_template(
        'shared-events.html',
        active_page='shared_events',
        shared_events_requests_received=shared_events_requests_received,
        shared_events_requests_sent=shared_events_requests_sent
    )

@app.route('/accept_share_event_request/<int:request_id>', methods=['POST'])
def accept_share_event_request(request_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    conn = connect_to_db()

    if conn:
        cur = conn.cursor()

        try:
            # Получаем информацию о запросе
            cur.execute(
                """
                SELECT 
                    senders_login, 
                    shared_event_name, 
                    start_time_and_date, 
                    end_time_and_date, 
                    location, 
                    category, 
                    comment,
                    regularity_id 
                FROM JointSharedEventRequests 
                WHERE request_id = %s
                """,
                (request_id,)
            )
            request_info = cur.fetchone()

            if request_info:
                senders_login, shared_event_name, start_time, end_time, location, category, comment, regularity_id = request_info

                # Вставляем данные в SharedEvents
                cur.execute(
                    """
                    INSERT INTO SharedEvents 
                    (Shared_event_name, Start_time_and_date, End_time_and_date, LOCATION, Category, COMMENT, Regularity_ID) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING shared_event_id
                    """,
                    (shared_event_name, start_time, end_time, location, category, comment, regularity_id)
                )

                conn.commit()

                # Получаем ID созданного события
                shared_event_id = cur.fetchone()[0]

                # Добавляем участника события (текущего пользователя)
                cur.execute(
                    "INSERT INTO JointSharedEventParticipation (Shared_event_ID, User_login) VALUES (%s, %s)",
                    (shared_event_id, current_user.user_login)
                )

                # Добавляем второго участника события (отправителя запроса)
                cur.execute(
                    "INSERT INTO JointSharedEventParticipation (Shared_event_ID, User_login) VALUES (%s, %s)",
                    (shared_event_id, senders_login)  # Добавляем отправителя запроса как участника
                )

                conn.commit()

                # Обновляем статус заявки на 'accepted'
                cur.execute(
                    "UPDATE JointSharedEventRequests SET request_status = 'accepted' WHERE request_id = %s",
                    (request_id,)
                )

                conn.commit()

                flash("Вы приняли запрос на совместное событие!", "success")
            else:
                flash("Заявка не найдена.", "error")

        except Exception as e:
            flash(f"Произошла ошибка: {e}", "error")
            conn.rollback()  # В случае ошибки откатить изменения
        finally:
            cur.close()
            conn.close()
    else:
        flash("Ошибка подключения к базе данных", "danger")

    return redirect(url_for('shared_events'))  # Перенаправляем на страницу совместных событий

@app.route('/decline_share_event_request/<int:request_id>', methods=['POST'])
def decline_share_event_request(request_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    conn = connect_to_db()

    if conn:
        cur = conn.cursor()

        try:
            # Удаляем заявку из JointSharedEventRequests
            cur.execute("DELETE FROM JointSharedEventRequests WHERE request_id = %s", (request_id,))
            conn.commit()
            flash("Заявка была отклонена.", "success")
        except Exception as e:
            flash(f"Произошла ошибка при отклонении заявки: {e}", "error")
            conn.rollback()  # В случае ошибки откатить изменения
        finally:
            cur.close()
            conn.close()

    else:
        flash("Ошибка подключения к базе данных", "danger")

    return redirect(url_for('shared_events'))  # Перенаправляем на страницу совместных событий

@app.route('/cancel_share_event_request/<int:request_id>', methods=['POST'])
def cancel_share_event_request(request_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    conn = connect_to_db()

    if conn:
        cur = conn.cursor()

        try:
            # Удаляем заявку из JointSharedEventRequests
            cur.execute("DELETE FROM JointSharedEventRequests WHERE request_id = %s AND senders_login = %s",
                        (request_id, current_user.user_login))
            if cur.rowcount > 0:
                # Если удаление прошло успешно
                conn.commit()
                flash("Запрос на совместное событие был отменен.", "info")
            else:
                # Если не найдено ни одной записи для удаления (например, неверный request_id или не тот отправитель)
                flash("Не удалось отменить запрос. Возможно, он уже был отменен.", "warning")
        except Exception as e:
            flash(f"Произошла ошибка при отмене заявки: {e}", "error")
            conn.rollback()  # В случае ошибки откатить изменения
        finally:
            cur.close()
            conn.close()
    else:
        flash("Ошибка подключения к базе данных", "danger")

    return redirect(url_for('shared_events'))  # Перенаправляем на страницу совместных событий


