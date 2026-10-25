
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit
import secrets
import re

app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(32)
socketio = SocketIO(app, cors_allowed_origins=[])

rooms = {}

@app.route("/")
def home():
    return render_template("index.html")

@socketio.on("create_room")
def create_room(data=None):
    sid = request.sid
    code = secrets.randbelow(900000) + 100000

    while str(code) in rooms:
        code = secrets.randbelow(900000) + 100000

    room = str(code)
    rooms[room] = {"members": set(), "messages": []}
    join_room(room)
    rooms[room]["members"].add(sid)

    emit("room_created", {"room": room}, to=sid)

@socketio.on("join_room")
def handle_join(data):
    room = str((data or {}).get("room", "")).strip()

    if not re.fullmatch(r"\d{6}", room) or room not in rooms:
        emit("room_error", {"message": "رقم الغرفة غير صحيح أو الغرفة غير موجودة."}, to=request.sid)
        return

    for old_room, info in rooms.items():
        if request.sid in info["members"]:
            leave_room(old_room)
            info["members"].discard(request.sid)

    join_room(room)
    rooms[room]["members"].add(request.sid)

    emit("room_joined", {"room": room, "messages": rooms[room]["messages"]}, to=request.sid)
    emit("room_notice", {"message": "انضم عضو جديد إلى الغرفة."}, to=room, include_self=False)

@socketio.on("leave_room")
def handle_leave_room(data=None):
    sid = request.sid
    for room, info in rooms.items():
        if sid in info["members"]:
            info["members"].discard(sid)
            leave_room(room)
            emit("room_notice", {"message": "غادر عضو الغرفة."}, to=room)
            emit("room_left", {"message": "خرجت من الغرفة."}, to=sid)
            return
    emit("room_left", {"message": "أنت لست داخل غرفة."}, to=sid)


@socketio.on("send_message")
def handle_message(data):
    data = data or {}
    room = str(data.get("room", "")).strip()
    name = str(data.get("name", "مستخدم")).strip()[:30]
    text = str(data.get("text", "")).strip()[:2000]

    if room not in rooms or request.sid not in rooms[room]["members"]:
        emit("room_error", {"message": "انضم إلى غرفة أولًا."}, to=request.sid)
        return

    if not text:
        return

    message = {"name": name or "مستخدم", "text": text}
    rooms[room]["messages"].append(message)
    rooms[room]["messages"] = rooms[room]["messages"][-200:]
    emit("new_message", message, to=room)

@socketio.on("disconnect")
def handle_disconnect(reason=None):
    for room, info in rooms.items():
        info["members"].discard(request.sid)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 9002))
    print(f"KatKot Chat يعمل على المنفذ {port}")
    socketio.run(app, host="0.0.0.0", port=port, debug=False)

