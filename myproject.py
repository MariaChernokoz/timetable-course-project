from app import app
from flask import blueprints

if __name__ == '__main__':
    app.run(debug=True)

#print(app.config['DB_SERVER'])  # localhost

from flask import Flask, render_template
from app import routes

app = Flask(__name__)

#app.register_blueprint(routes.bp)
@app.route("/", methods=["GET", "POST"])
def login():
    return render_template('main.html')


@app.route("/registration", methods=["GET", "POST"])
def registration():
    return render_template('post/registration.html')

##################################################


