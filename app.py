from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from typing import Any

app = Flask(__name__)  # __name__ 代表目前執行的模組
DB_PATH = 'membership.db'


def get_db_connection() -> sqlite3.Connection:
    """
    取得 sqlite3 連線，並設定 row_factory 方便讀取 dict-like row。
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    啟動時自動建立 members 資料表（若不存在）。
    """
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS members (
            iid        INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            email      TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            phone      TEXT,
            birthdate  TEXT
        )
    ''')
    conn.commit()
    conn.close()


@app.template_filter('add_stars')
def add_stars(username: str) -> str:
    """
    為用戶名前後加上星號，如 admin -> ★admin★
    """
    return f"★{username}★"


@app.route("/")
def index() -> Any:
    return render_template("index.html")


@app.route('/register', methods=['GET', 'POST'])
def register() -> Any:
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        phone = request.form.get('phone', '').strip()
        birthdate = request.form.get('birthdate', '').strip()

        if not username or not email or not password:
            return redirect(url_for('error', message='請輸入用戶名、電子郵件和密碼'))

        conn = get_db_connection()
        cursor = conn.execute('SELECT iid FROM members WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            return redirect(url_for('error', message='用戶名已存在'))

        try:
            conn.execute(
                'INSERT INTO members (username, email, password, phone, birthdate) VALUES (?, ?, ?, ?, ?)',
                (username, email, password, phone, birthdate)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return redirect(url_for('error', message='電子郵件已被使用'))

        conn.close()
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login() -> Any:
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            return redirect(url_for('error', message='請輸入電子郵件和密碼'))

        conn = get_db_connection()
        cursor = conn.execute(
            'SELECT * FROM members WHERE email = ? AND password = ?',
            (email, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            return render_template('welcome.html', username=user['username'], iid=user['iid'])
        else:
            return redirect(url_for('error', message='電子郵件或密碼錯誤'))

    return render_template('login.html')


@app.route('/error')
def error() -> Any:
    message = request.args.get('message', '發生未知錯誤')
    return render_template('error.html', error_message=message)



@app.route("/welcome/<int:iid>")
def welcome(iid: int) -> Any:
    """
    登入後的歡迎頁：顯示 username 和操作按鈕。
    """
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM members WHERE iid = ?", (iid,)).fetchone()
    conn.close()
    if not user:
        return render_template("error.html", error_message="用戶不存在")
    return render_template(
        "welcome.html",
        username=user["username"],
        iid=user["iid"]
    )


@app.route("/edit_profile/<int:iid>", methods=["GET", "POST"])
def edit_profile(iid: int) -> Any:
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM members WHERE iid = ?", (iid,)).fetchone()
    if not user:
        conn.close()
        return render_template("error.html", error_message="用戶不存在")

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        phone = request.form.get("phone", "").strip()
        birthdate = request.form.get("birthdate", "").strip()

        if not email or not password:
            conn.close()
            return render_template("error.html", error_message="請輸入電子郵件和密碼")

        # 檢查 email 是否被他人使用
        if conn.execute(
            "SELECT 1 FROM members WHERE email = ? AND iid != ?", (email, iid)
        ).fetchone():
            conn.close()
            return render_template("error.html", error_message="電子郵件已被使用")

        conn.execute(
            "UPDATE members SET email = ?, password = ?, phone = ?, birthdate = ? WHERE iid = ?",
            (email, password, phone, birthdate, iid)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("welcome", iid=iid))

    conn.close()
    return render_template("edit_profile.html", user=user)


@app.route("/delete/<int:iid>")
def delete_user(iid: int) -> Any:
    """
    刪除使用者並回到首頁。
    """
    conn = get_db_connection()
    conn.execute("DELETE FROM members WHERE iid = ?", (iid,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
