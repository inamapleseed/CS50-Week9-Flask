import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.execute("SELECT DISTINCT(stock_symbol), SUM(shares) as shares FROM user_stocks WHERE user_id = ? GROUP BY stock_symbol", session["user_id"])

    global overall
    overall = 0

    for row in stocks:
        # stock_symbol =
        result = lookup(row['stock_symbol'])
        if result:
            price = result['price']
            row.update({'price': price})

            stock_total = row['shares'] * price
            row.update({'total': stock_total})
            overall += stock_total

    cash_bal = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])
    grand_total = cash_bal[0]['cash'] + overall

    return render_template("/index.html", results=stocks, cash_bal=cash_bal, grand_total=grand_total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        result = lookup(symbol)
        shares = request.form.get("shares")

        if not result or not symbol:
            return apology("stock code invalid", 400)

        if not shares.isdigit():
            return apology("invalid shares", 400)

        total = result["price"] * float(shares)

        user_id = session["user_id"]
        row = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        cash = float(row[0]["cash"])
        date = datetime.now()

        if not result:
            return apology("invalid stock code", 400)

        if total > cash:
            return apology("not enough cash", 403)
        else:
            db.execute("INSERT INTO user_stocks (user_id, stock_symbol, shares, timestamp) VALUES(?, ?, ?, ?)", user_id, symbol, shares, date)

            balance = cash - total

            db.execute("UPDATE users SET cash = ? WHERE id = ?", balance, user_id)

        return redirect("/")

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        code = request.form.get("symbol")
        result = lookup(code)

        if result:
            return render_template("quoted.html", name=result["name"], symbol=result["symbol"], price=result["price"])
        else:
            return apology("stock code invalid", 400)

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        pw = request.form.get("password")
        pwconfi = request.form.get("confirmation")
        user = request.form.get("username")

        db = SQL("sqlite:///finance.db")
        usernames = db.execute("SELECT username FROM users")

        if not user:
            return apology("must provide username", 400)
        elif not pw:
            return apology("must provide password", 400)
        elif pw != pwconfi:
            return apology("password and confirmation mismatch", 400)

        # if users exist
        if usernames:
            for username in usernames:
                # if user already exists
                if user == username['username']:
                    return apology("username already exists", 400)

        pwhash = generate_password_hash(pw)
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", user, pwhash)

        return render_template("/login.html")

    return render_template("/register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    stocks = db.execute("SELECT DISTINCT(stock_symbol), SUM(shares) as shares FROM user_stocks WHERE user_id = ? GROUP BY stock_symbol", session["user_id"])

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # if stocks:
        return render_template('/sell.html', stocks=stocks, symbol=symbol, shares=shares)
        #     for row in stocks:
        #         result = lookup(row['stock_symbol'])
        #         if result:
        #             price = result['price']

        #             return render_template('/sell.html')
        # else:
        #     return apology("Invalid stock", 400)

    return render_template('/sell.html', stocks=stocks)
