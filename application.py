import os
from datetime import datetime

from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from functools import wraps
from flask_socketio import SocketIO, emit
from werkzeug.security import check_password_hash, generate_password_hash

chatrooms = []
users = []
messages = []
ids=177

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Route for requiring login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# Homepage function to sign in, navigate to chatrooms, enter chatrooms, etc.
@app.route("/")
@login_required
def index():
    user = session["user_id"]
    active_chatrooms_id = []
    active_chatrooms_name = []

    # Search for all messages and see where the user has last been active (100 messages)
    for message in messages:
        if message["user_id"] == user and message["chatroom_id"] not in active_chatrooms_id:
            active_chatrooms_id.append(message["chatroom_id"])
            active_chatrooms_name.append(next(item["room_name"] for item in chatrooms if item["room_id"] == message["chatroom_id"]))
    
    return render_template("index.html", active_chatrooms_id=active_chatrooms_id, active_chatrooms_name=active_chatrooms_name, chatrooms=chatrooms)

@app.route("/create_chatroom", methods=["GET", "POST"])
def create_chatroom():
    global ids

    if request.method == "GET":
        return render_template("create_chatroom.html")
    else:
        if not request.form.get("chatroom_name"):
            return render_template("error.html", error="Please Enter A Name")
        
        chatroom_name = request.form.get("chatroom_name")
        
        # Check that a chatroom with the same name does not already exist
        for room in chatrooms:
            if room["room_name"].upper() == chatroom_name.upper():
                return render_template("error.html", error="Chatroom Name Already Taken")

        # Create the chatroom if it iterates fully over
        x = {"room_name": chatroom_name, "room_id": ids}
        ids += 5
        chatrooms.append(x)

        # Redirect to the chatroom
        return redirect("/room/" + str(ids-5))


# Logs in the user
@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    
    if request.method == "GET":
        return render_template("login.html")
    else:
        if not request.form.get("username"):
            return render_template("error.html", error="No Username Input")
        if not request.form.get("password"):
            return render_template("error.html", error="No Password Input")

        username = request.form.get("username")
        password = request.form.get("password")
        
        for user in users:
            if user["username"] == username:
                if check_password_hash(user["password"], password):
                    session["user_id"] = username
                    return redirect("/")
                else:
                    return render_template("error.html", error="Invalid Password")

        # If iterated over the entire for loop and never breaks, username is invalid
        return render_template("error.html", error="Invalid Username")

@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()

    if request.method == "GET":
        return render_template("register.html")
    else:
        if not request.form.get("username"):
            return render_template("error.html", error="No Username Input")
        if not request.form.get("password"):
            return render_template("error.html", error="No Password Input")
        if not request.form.get("confirm_password"):
            return render_template("error.html", error="No Confirm Password Input")
        if request.form.get("password") != request.form.get("confirm_password"):
            return render_template("error.html", error="Input Password and Confirm Password Do Not Match")
        
        username = request.form.get("username")
        password = request.form.get("password")

        for user in users:
            if user["username"].upper() == username.upper():
                return render_template("error.html", error="Username Already Exists, Please Choose Another Username")

        # Add new user into list
        new_user = {"username": username, "password":generate_password_hash(password)}
        users.append(new_user)
        session["user_id"] = username

        return redirect("/")


# Logs out the user
@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    session.clear()
    return redirect("/")

# Chatroom route wherein user can view the current chat
@app.route("/room/<int:id>", methods=["GET", "POST"])
@login_required
def room(id):
    chatroom = next((item for item in chatrooms if item["room_id"] == id), None)
    if chatroom is None:
        return render_template("error.html", error="Invalid Chatroom")
    
    if request.method == "GET":
        chatroom_name = chatroom["room_name"]

        # Find messages associated with chatroom
        filtered_messages = [i for i in messages if i["chatroom_id"] == id]

        return render_template("chatroom.html", chatroom_name=chatroom_name, filtered_messages=filtered_messages)
    else:
        

        return render_template("error.html")



@socketio.on("submit message")
def message(data):
    content = data["content"]
    chatroom_id = int(data["chatroom_id"])
    user = session["user_id"]
    
    now = datetime.now()
    time = now.strftime("%H:%M %d/%m/%Y")

    message = {"chatroom_id": chatroom_id, "content": content, "user_id": user, "time": time}
    filtered_messages = [i for i in messages if i["chatroom_id"] == chatroom_id]
    
    if len(filtered_messages)==100:
        # Go through and delete the first message for this chatroom
        for i in range(len(messages)):
            if messages[i]["chatroom_id"] == chatroom_id:
                del messages[i]
                break
    
    # Add message into messages, and emit the message
    messages.append(message)
    emit("receive message", {"chatroom_id": chatroom_id, "content": content, "user_id": user, "time": time}, broadcast=True)

