import psycopg
from app import app
from app import login_manager
from flask_login import UserMixin

class User(UserMixin):

    def __init__(self, username, password):
        self.id = username
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    with psycopg.connect(host=app.config['POSTGRES_HOST'],
                         user=app.config['POSTGRES_USER'],
                         password=app.config['POSTGRES_PASSWORD'],
                         dbname=app.config['POSTGRES_DB']) as con:
        cur = con.cursor()
        username, password = cur.execute('SELECT username, password'
                                            'FROM "users" '
                                            'WHERE username = %s', (user_id,)).fetchone()
    return User(username, password)
