import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    stocks = db.execute("SELECT * FROM portfolio WHERE id = :user_id", user_id=session["user_id"])
    purchase_total = db.execute("SELECT SUM(total) FROM portfolio WHERE id = :user_id", user_id=session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])
    # total = purchase_total + cash

    return render_template("index.html", stocks=stocks, cash=cash, total=purchase_total)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # via POST
    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))

        # if symbol does not exist
        if not quote:
            return apology("invalid symbol", 400)

        # get the numbers of shares to be bought
        shares = int(request.form.get("shares"))

        # query database for this user
        rows = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])

        # check the remaining cash balance of the user and stock price per share
        cash_balance = rows[0]["cash"]
        share_price = quote["price"]

        # calculate the total price of bought shares
        total_price = shares * share_price

        # not enough cash for purchase
        if total_price > cash_balance:
            return apology("can't afford", 400)

        # add purchase into portfolio database
        db.execute("INSERT INTO portfolio(id, symbol, name, shares, price, total) \
                    VALUES (:id, :symbol, :name, :shares, :price, :total)", \
                    id=session["user_id"], symbol=quote["symbol"], name=quote["name"], \
                    shares=shares, price=share_price, total=total_price)

        # add transaction into history database
        db.execute("INSERT INTO history(id, symbol, shares, price) \
                    VALUES (:id, :symbol, :shares, :price)", \
                    id=session["user_id"], symbol=quote["symbol"], shares=shares, price=share_price)

        # update cash balance
        db.execute("UPDATE users SET cash = cash - :purchase WHERE id = :user_id", price=total_price, user_id=session["user_id"])

        flash("Bought!")
        return render_template("/")

    # via GET
    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    return jsonify("TODO")


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

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

    # via POST
    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))

        # if symbol does not exist
        if not quote:
            return apology("missing symbol", 400)

        return render_template("quoted.html", quote=quote)

    # via GET
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must Provide Username", 400)

        # Ensure password field was filled
        elif not request.form.get("password"):
            return apology("Missing Password", 400)

        # Ensure password and password confirmation field matches
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("passwords don't match", 400)

        # Hash password
        hash = generate_password_hash(request.form.get("password"))

        # Insert a new user in the database
        new_user_id = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                                 username=request.form.get("username"),
                                 hash=hash)

        # Username already taken
        if not new_user_id:
            return apology("Username Already Taken", 400)

        # Log them in automatically and store id in session
        flash("Registered!")
        session["user_id"] = new_user_id
        return redirect("/")

    # via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
