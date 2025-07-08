import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, emit
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

socketio = SocketIO(app)

client = MongoClient(
    "mongodb+srv://chatuser:AkhilChat2025!@cluster2.a5gequu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster2"
)
db = client.chatdb
messages_col = db.messages

# Track users in each room
users_in_rooms = {}

@app.route('/')
def home():
    rooms = messages_col.distinct('room')
    avatars = os.listdir(os.path.join(app.static_folder, 'avatars'))
    return render_template('join.html', rooms=rooms, avatars=avatars)

@app.route('/clear/<room>')
def clear_history(room):
    messages_col.delete_many({'room': room})
    return redirect(url_for('chat', room=room, name='Guest'))

@app.route('/chat/<room>/<name>')
def chat(room, name):
    history = list(messages_col.find({'room': room}).sort("timestamp", 1))
    avatar = request.args.get('avatar', 'default.png')
    return render_template('chat.html', history=history, room=room, name=name, avatar=avatar)

@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    name = data['name']
    avatar = data.get('avatar', 'default.png')

    join_room(room)

    if room not in users_in_rooms:
        users_in_rooms[room] = {}
    users_in_rooms[room][name] = avatar

    emit('user_list', [
        {'name': u, 'avatar': a} for u, a in users_in_rooms[room].items()
    ], room=room)

@socketio.on('leave_room')
def handle_leave(data):
    room = data['room']
    name = data['name']

    leave_room(room)

    if room in users_in_rooms and name in users_in_rooms[room]:
        del users_in_rooms[room][name]

    emit('user_list', [
        {'name': u, 'avatar': a} for u, a in users_in_rooms[room].items()
    ], room=room)

@socketio.on('send_message')
def handle_send_message(data):
    messages_col.insert_one({
        'sender': data['sender'],
        'message': data['message'],
        'translated_message': '',
        'timestamp': datetime.now(),
        'room': data['room']
    })
    emit('receive_message', data, room=data['room'])

@socketio.on('typing')
def handle_typing(data):
    emit('show_typing', data['sender'] + ' is typing...', room=data['room'])

@socketio.on('clear_history')
def handle_clear_history(data):
    room = data['room']
    messages_col.delete_many({'room': room})
    emit('history_cleared', room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)
