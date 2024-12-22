from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, validators
from wtforms.validators import Length, EqualTo


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', [validators.InputRequired(), validators.Length(min=4, max=25)])
    password = PasswordField('Пароль', [validators.InputRequired(), validators.Length(min=6, max=100)])
    submit = SubmitField('Зарегистрироваться')


class LoginForm(FlaskForm):
    username = StringField('Логин',   [validators.InputRequired(), Length(min=4, max=25)])
    password = PasswordField('Пароль', [validators.InputRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')
