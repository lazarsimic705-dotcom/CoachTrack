import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host="localhost",
        port=1111,
        user="root",
        password="123456",
        database="coachtrack",
        charset="utf8"
    )

