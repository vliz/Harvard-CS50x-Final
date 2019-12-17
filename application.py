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

    # show list of stocks owned
    portfolios = db.execute("SELECT symbol, shares, price FROM portfolio WHERE id=:id", id=session["user_id"])

    # total cash + shares
    capital = 0

    # updating the total price for each stock owned and adding to capital
    for portfolio in portfolios:
        symbol = portfolio["symbol"]
        shares = portfolio["shares"]
        share_price = portfolio["price"]
        amount = shares * share_price
        capital += amount
        db.execute("UPDATE portfolio SET total=:amount WHERE id=:id AND symbol=:symbol", amount=usd(amount), id=session["user_id"], symbol=symbol)

    # get cash balance and add total
    cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    balance = cash[0]["cash"]
    capital += balance

    # show updated portfolio
    updated = db.execute("SELECT * FROM portfolio WHERE id=:id", id=session["user_id"])

    return render_template("index.html", stocks=updated, cash=usd(balance), total=usd(capital))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # via GET
    if request.method == "GET":
        return render_template("buy.html")

    else:
        quote = lookup(request.form.get("symbol"))

        # if symbol does not exist
        if not quote:
            return apology("invalid symbol", 400)

        # check if share was a positive integer
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("must be positive integer", 400)

        # check if number of shares more than 0
        if shares < 0:
            return apology("have to buy one or more", 400)

        # query database for this user
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])

        # check the remaining cash balance of the user and stock price per share
        cash_balance = rows[0]["cash"]
        share_price = quote["price"]

        # not enough cash for purchase
        if (share_price * shares) > cash_balance:
            return apology("can't afford", 400)

        # add transaction into history database
        db.execute("INSERT INTO history(id, symbol, shares, price) \
                    VALUES (:id, :symbol, :shares, :price)", \
                    id=session["user_id"], symbol=quote["symbol"], shares=shares, price=usd(share_price))

        # update cash balance
        db.execute("UPDATE users SET cash = cash - :price WHERE id = :id", price=share_price * shares, id=session["user_id"])

        # Select user shares of that symbol
        user_shares = db.execute("SELECT shares FROM portfolio \
                           WHERE id = :id AND symbol=:symbol", \
                           id=session["user_id"], symbol=quote["symbol"])

        # if user doesn't has shares of that symbol, create new stock object
        if not user_shares:
            db.execute("INSERT INTO portfolio (id, symbol, name, shares, price) \
                        VALUES(:id, :symbol, :name, :shares, :price)", \
                        id=session["user_id"], symbol=quote["symbol"], name=quote["name"], \
                        shares=shares, price=quote["price"])

        # Else increment the shares count
        else:
            shares_total = user_shares[0]["shares"] + shares
            db.execute("UPDATE portfolio SET shares=:shares \
                        WHERE id=:id AND symbol=:symbol", \
                        shares=shares_total, id=session["user_id"], \
                        symbol=quote["symbol"])

        flash("Bought!")
        return redirect("/")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    return jsonify("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    histories = db.execute("SELECT symbol, shares, price, date FROM history WHERE id = :id ORDER BY date ASC", id=session["user_id"])

    return render_template("history.html", histories=histories)


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

@app.route("/funds", methods=["GET", "POST"])
@login_required
def funds():
    """Adding Funds to User's Cash"""

    # via POST
    if request.method == "POST":

        # check if share was a positive integer
        try:
            money = float(request.form.get("funds"))
        except:
            return apology("can't deduct money", 400)

        # check if funds more than 0
        if money < 0:
            return apology("have to add more than 0", 400)

        # update user's cash
        db.execute("UPDATE users SET cash = cash + :amount WHERE id=:id", id=session["user_id"], amount=money)

        flash("Balance Added!")
        return redirect("/")

    # via GET
    else:
        return render_template("funds.html")



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
        session["user_id"] = new_user_id
        flash("Registered!")
        return redirect("/index")

    # via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # via POST
    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))

        # if symbol does not exist
        if not quote:
            return apology("invalid symbol", 400)

        # check if share was a positive integer
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("must be positive integer", 400)

        # check if number of shares more than 0
        if shares <= 0:
            return apology("have to sell more than 0 stock", 400)

        # select the symbol shares of that user
        user_shares = db.execute("SELECT shares FROM portfolio \
                                  WHERE id = :id AND symbol=:symbol", \
                                  id=session["user_id"], symbol=quote["symbol"])

        # check if enough shares to sell
        if not user_shares or int(user_shares[0]["shares"]) < shares:
            return apology("Not enough shares")

        # calculate the total price of sold shares
        share_price = quote["price"]
        total_price = shares * share_price

        # update history of the sale
        db.execute("INSERT INTO history (id, symbol, shares, price) \
                    VALUES(:id, :symbol, :shares, :price)", \
                    symbol=quote["symbol"], shares=-shares, \
                    price=usd(share_price), id=session["user_id"])

        # update user cash
        db.execute("UPDATE users SET cash = cash + :sale WHERE id = :id", \
                    id=session["user_id"], \
                    sale=total_price)

        # decrement the shares count
        shares_total = user_shares[0]["shares"] - shares

        # if after decrement is zero, delete shares from portfolio
        if shares_total == 0:
            db.execute("DELETE FROM portfolio \
                        WHERE id=:id AND symbol=:symbol", \
                        id=session["user_id"], \
                        symbol=quote["symbol"])
        # otherwise, update portfolio shares count
        else:
            db.execute("UPDATE portfolio SET shares=:shares \
                    WHERE id=:id AND symbol=:symbol", \
                    shares=shares_total, id=session["user_id"], \
                    symbol=quote["symbol"])

        flash("Sold!")
        return redirect("/")

    # via GET
    else:
        stocks = db.execute("SELECT symbol FROM portfolio \
        WHERE id = :id", id=session["user_id"])

        return render_template("sell.html", stocks=stocks)



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
