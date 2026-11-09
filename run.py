import pymysql
from app import create_app, db
from config import Config

def ensure_mysql_database_exists():
    """Connects to MySQL server and creates the database if it doesn't exist."""
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            port=int(Config.DB_PORT)
        )
        with connection.cursor() as cursor:
            # Create database if it doesn't exist with UTF8mb4 support
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        connection.close()
        print(f"-> Database '{Config.DB_NAME}' verified/created successfully.")
    except Exception as e:
        print(f"-> Warning: Could not auto-create MySQL database. Ensure your MySQL server is running. Error: {e}")

app = create_app()

if __name__ == '__main__':
    # Step 1: Ensure the MySQL database exists before starting the app
    ensure_mysql_database_exists()

    # Step 2: Create all database tables based on models.py
    with app.app_context():
        #db.drop_all()
        db.create_all()
        #for debugging only.
        print("-> Database tables verified/created successfully.")

    # Step 3: Run the development server (accessible locally and on your local network)
    app.run(debug=True, host='0.0.0.0', port=5000)