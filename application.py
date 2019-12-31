import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd

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

# Configure Sumo Travel Library to use SQLite database
db = SQL("sqlite:///data.db")


@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    # via POST
    if request.method == "POST":

        if request.form['action'] == 'Add New Hotel / Airline Membership':
            return redirect("/addmember")
        elif request.form['action'] == 'Membership List':
            return redirect("/member")
        elif request.form['action'] == 'Add New Travel Entry':
            return redirect("/addentry")
        elif request.form['action'] == 'Travel Journal':
            return redirect("/diary")

    # via GET
    elif request.method == 'GET':
        name = db.execute("SELECT name FROM users WHERE id = :id", id=session["user_id"])

        return render_template("index.html", names=name)


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""

    # If request made via GET
    if request.method == "GET":

        # Takes username as argument from username
        username = request.args.get('username')

        # If not user, then username is free
        users = db.execute("SELECT username FROM users WHERE username=:username", username=username)
        if not users:
            return jsonify(True)
        else:
            return jsonify(False)


@app.route("/addmember", methods=["GET", "POST"])
@login_required
def addmember():
    """Add New Membership Entry"""

    # via GET
    if request.method == "GET":
        return render_template("addmember.html")

    # via POST
    else:
        comptype = request.form.get("comptype")
        compname = request.form.get("compname")
        nameuser = request.form.get("nameuser")
        email = request.form.get("email")
        memnum = request.form.get("memnum")
        points = request.form.get("points")

        # add entry into membership database
        db.execute("INSERT INTO membership(id, comptype, compname, nameuser, email, memnum, points) \
                    VALUES (:id, :comptype, :compname, :nameuser, :email, :memnum, :points)", id=session["user_id"], comptype=comptype, compname=compname, nameuser=nameuser, email=email, memnum=memnum, points=points)

        flash("Membership Added")
        return redirect("/member")


@app.route("/member", methods=["GET", "POST"])
@login_required
def member():
    """Show list of airline / hotel membership"""

    # via POST
    if request.method == "POST":

        return redirect("/addmember")

    # via GET
    else:
        # show membership
        mem = db.execute("SELECT * FROM membership WHERE id=:id", id=session["user_id"])

        return render_template("member.html", mems=mem)


@app.route("/addentry", methods=["GET", "POST"])
@login_required
def addentry():
    """Add New Travel Entry"""

    # via POST
    if request.method == "POST":
        place = request.form.get("place")
        airline = request.form.get("airline")
        hotel = request.form.get("hotel")
        depart = request.form.get("depart")
        arrive = request.form.get("arrive")
        miles = request.form.get("miles")
        points = request.form.get("points")
        money = float(request.form.get("money"))

        # add entry into travel diary database
        db.execute("INSERT INTO diary(id, place, airline, hotel, depart, arrive, miles, points, money) \
                    VALUES (:id, :place, :airline, :hotel, :depart, :arrive, :miles, :points, :money)", id=session["user_id"], place=place, airline=airline, hotel=hotel, depart=depart, arrive=arrive, miles=miles, points=points, money=usd(money))

        # update airline miles into the membership database
        db.execute("UPDATE membership SET points = points + :miles WHERE id = :id AND compname = :compname", id=session["user_id"], compname=airline, miles=miles)

        # update hotel points into the membership database
        db.execute("UPDATE membership SET points = points + :points WHERE id = :id AND compname = :compname", id=session["user_id"], compname=hotel, points=points)

        flash("New Entry Added")
        return redirect("/diary")

    # via GET
    else:

        airs = db.execute("SELECT compname FROM membership WHERE id = :id AND comptype = :comptype", id=session["user_id"], comptype="Airline")
        hots = db.execute("SELECT compname FROM membership WHERE id = :id AND comptype = :comptype", id=session["user_id"], comptype="Hotel")

        return render_template("addentry.html", airs=airs, hots=hots)


@app.route("/diary", methods=["GET", "POST"])
@login_required
def diary():
    """Show history of travels"""

    # via POST
    if request.method == "POST":

        return redirect("/addentry")

    # via GET
    else:

        # show travel diary
        trip = db.execute("SELECT * FROM diary WHERE id=:id", id=session["user_id"])

        return render_template("diary.html", trips=trip)


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
    flash("You have been logged out")
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must Provide Username", 400)

        # Ensure name field was filled
        elif not request.form.get("name"):
            return apology("Must Provide Full Name", 400)

        # Ensure email field was filled
        elif not request.form.get("email"):
            return apology("Please Fill Email Address", 400)

        # Ensure password field was filled
        elif not request.form.get("password"):
            return apology("Missing Password", 400)

        # Ensure password and password confirmation field matches
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("passwords don't match", 400)

        # Hash password
        hash = generate_password_hash(request.form.get("password"))

        # Insert a new user in the database
        new_user_id = db.execute("INSERT INTO users (username, name, email, hash) VALUES(:username, :name, :email, :hash)",
                                 username=request.form.get("username"), name=request.form.get("name"), email=request.form.get("email"), hash=hash)

        # Username already taken
        if not new_user_id:
            return apology("Username Already Taken", 400)

        # Log them in automatically and store id in session
        session["user_id"] = new_user_id
        flash("Registered!")
        return redirect("/")

    # via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
