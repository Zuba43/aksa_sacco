import pymysql
from app import create_app, db
from config import Config
import app.models as _models  # <-- import FIRST, with different name

def ensure_mysql_database_exists():
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            port=int(Config.DB_PORT)
        )
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        connection.commit()
        connection.close()
        print(f"-> Database '{Config.DB_NAME}' verified/created.")
    except Exception as e:
        print(f"-> Warning: Could not auto-create DB: {e}")

# 1. Make sure DB exists BEFORE we create app
ensure_mysql_database_exists()

# 2. Create app
app = create_app()

# 3. Create tables BOTH on laptop AND on PythonAnywhere
with app.app_context():
    try:
        db.create_all()
        print("-> Database tables verified/created.")
    except Exception as e:
        print(f"-> create_all error: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)