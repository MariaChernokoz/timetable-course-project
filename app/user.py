import psycopg
from app import app
from app import login_manager
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_login, password):
        self.id = user_login
        self.user_login = user_login
        self.password = password

@login_manager.user_loader
def load_user(user_login):
    with psycopg.connect(host=app.config['POSTGRES_HOST'],
                         user=app.config['POSTGRES_USER'],
                         password=app.config['POSTGRES_PASSWORD'],
                         dbname=app.config['POSTGRES_DB']) as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE user_login = %s", (user_login,))
        user = cur.fetchone()
    return User(user[0],user[1])
