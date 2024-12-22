from flask_login import UserMixin
#from app.routes import login


class User(UserMixin):
    def __init__(self, user_login, password):
        self.id = user_login
        self.user_login = user_login
        self.password = password

    def __repr__(self):
        return f"<User {self.user_login}>"
