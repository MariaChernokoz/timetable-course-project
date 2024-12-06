from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, DateField, IntegerField, PasswordField, SubmitField, validators

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', [validators.Length(min=4, max=25)])
    email = StringField('E-mail', [validators.Length(min=6, max=100), validators.Email()])
    password = PasswordField('Пароль', [validators.InputRequired(),
                                        validators.Length(min=6, max=100),
                                        validators.EqualTo('confirm', message='Пароли должны совпадать')])
    confirm  = PasswordField('Повторите пароль')
    birth_date = DateField('Дата рождения', format='%Y-%m-%d', validators=[validators.InputRequired()])
    region_code = IntegerField('Код региона', [validators.InputRequired()])
    want_spam = BooleanField('Я согласен получать рекламную рассылку', [validators.InputRequired()])
    submit = SubmitField('Зарегистрироваться')