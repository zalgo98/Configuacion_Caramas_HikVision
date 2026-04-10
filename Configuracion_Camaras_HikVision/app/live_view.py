import sys
import vlc

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class VideoPanel(QWidget):
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.ip= None
        self.instance = vlc.Instance("--network-caching=300")
        self.player = self.instance.media_player_new()
        self.current_url = None

        self.setMinimumSize(240, 180)
        self.setStyleSheet("background-color: black;")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(2)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: white; background-color: #222; padding: 4px;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)

        self.video_frame = QWidget(self)
        self.video_frame.setStyleSheet("background-color: black;")
        self.layout.addWidget(self.video_frame, 1)

    def set_title(self, text: str):
        self.title_label.setText(text)

    def play(self, rtsp_url: str, ip: str = None):
        self.current_url = rtsp_url
        self.ip = ip
        media = self.instance.media_new(rtsp_url)
        self.player.set_media(media)

        win_id = int(self.video_frame.winId())

        if sys.platform.startswith("linux"):
            self.player.set_xwindow(win_id)
        elif sys.platform == "win32":
            self.player.set_hwnd(win_id)
        elif sys.platform == "darwin":
            self.player.set_nsobject(win_id)

        self.player.play()

    def stop(self):
        try:
            self.player.stop()
        except Exception:
            pass
