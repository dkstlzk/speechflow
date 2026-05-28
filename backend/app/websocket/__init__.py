from flask_socketio import SocketIO

from .events import register_events


def register_socketio_events(socketio: SocketIO) -> None:
    register_events(socketio)
