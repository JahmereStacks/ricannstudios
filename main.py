from flask import Flask, render_template

import pymysql

from dynaconf import Dynaconf

app = Flask(__name__)

config = Dynaconf(settings_file=["settings.toml"])

def connect_db():
    conn = pymysql.connect(
        host="db.steamcenter.tech",
        user="jquiles",
        password=config.password,
        database="jquiles_ricann_studios",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )

    return conn

@app.route("/")
def index():
    return render_template("homepage.html.jinja")

@app.route("/browse")
def browse():
    connection = connect_db()

    cursor = connection.cursor()

    cursor.execute('SELECT * FROM `Product`')

    result = cursor.fetchall()

    connection.close()

    return render_template("browse.html.jinja", products = result)