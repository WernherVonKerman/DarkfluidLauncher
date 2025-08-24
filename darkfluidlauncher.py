import sys
import subprocess
import frida
import base64
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame
)
from PyQt5.QtGui import QPixmap, QIcon, QImage
from PyQt5.QtCore import QTimer

# Steam settings
STEAM_URI = "steam://run/553850"
PROCESS_NAME = "helldivers2.exe"

# === Embedded Frida script ===
frida_script = """
var LIVE_BASE = "https://api.live.prod.thehelldiversgame.com";
var TARGET_BASE = LIVE_BASE;

const CURLOPT_URL = 10002;
var allocatedStrings = [];

function maybeRewriteUrl(url) {
    if (!url) return null;
    if (url.startsWith(LIVE_BASE)) {
        return url.replace(LIVE_BASE, TARGET_BASE);
    }
    return url;
}

var addr = Module.findExportByName("libcurl.dll", "curl_easy_setopt");
if (addr) {
    Interceptor.attach(addr, {
        onEnter: function (args) {
            let option = args[1].toInt32();
            if (option === CURLOPT_URL) {
                let origUrl = args[2].readUtf8String();
                let newUrl = maybeRewriteUrl(origUrl);
                if (newUrl && newUrl !== origUrl) {
                    let mem = Memory.allocUtf8String(newUrl);
                    allocatedStrings.push(mem);
                    args[2] = mem;
                    console.log("[+] Redirected URL: " + origUrl + " -> " + newUrl);
                }
            }
        }
    });
    console.log("[*] Hooked curl_easy_setopt");
} else {
    console.log("[-] curl_easy_setopt not found!");
}

rpc.exports = {
    setserver: function(server) {
        TARGET_BASE = server;
        console.log("[*] Switched target server to " + server);
    }
};
"""

# === Embedded base64 PNG icon ===
darkfluid_png_base64 = """
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
"""  # REPLACE with your full base64 string

def pixmap_from_base64(base64_data):
    base64_data = base64_data.strip().replace("\n", "")
    missing_padding = len(base64_data) % 4
    if missing_padding:
        base64_data += '=' * (4 - missing_padding)
    image_data = base64.b64decode(base64_data)
    return QPixmap.fromImage(QImage.fromData(image_data))

class RedirectApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Helldivers 2 DarkFluid Launcher")
        self.setFixedSize(420, 220)
        self.setStyleSheet("background-color: #9234eb;")

        # === Layout ===
        layout = QVBoxLayout()
        self.setLayout(layout)

        # === Status frame ===
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            background-color: #6a1b9a;
            border-radius: 16px;
            padding: 8px;
        """)
        status_layout = QHBoxLayout(status_frame)
        layout.addWidget(status_frame)

        # Status icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(72, 78)
        self.icon_label.setScaledContents(True)
        self.icon_label.setPixmap(pixmap_from_base64(darkfluid_png_base64))
        status_layout.addWidget(self.icon_label)

        # Status text
        self.label = QLabel("Select an operation helldiver:")
        self.label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        status_layout.addWidget(self.label)

        # Buttons
        self.btn_darkfluid = QPushButton("Darkfluid Missions")
        self.btn_TCS = QPushButton("TCS Missions")
        self.btn_TCS2 = QPushButton("Deactivate TCS Missions")
        self.buttons = [self.btn_darkfluid, self.btn_TCS, self.btn_TCS2]

        for btn in self.buttons:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #6a1b9a;
                    color: white;
                    font-weight: bold;
                    padding: 6px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #7d2bbe;
                }
            """)
            layout.addWidget(btn)

        # Connect buttons
        self.btn_darkfluid.clicked.connect(lambda: self.start_and_switch("Darkfluid Missions", "https://api2.betapixel.net"))
        self.btn_TCS.clicked.connect(lambda: self.start_and_switch("TCS Missions", "https://api.betapixel.net"))
        self.btn_TCS2.clicked.connect(lambda: self.start_and_switch("Deactivate TCS Missions", "https://api1.betapixel.net"))

        # Frida session variables
        self.session = None
        self.script = None
        self.pending_server = None
        self.pending_label_text = None

        # Timer to poll game process
        self.timer = QTimer()
        self.timer.timeout.connect(self.try_attach)

    def start_and_switch(self, friendly_text, server_url):
        self.pending_label_text = friendly_text
        self.pending_server = server_url
        self.session = None
        self.script = None
        try:
            subprocess.Popen(["start", STEAM_URI], shell=True)
            self.label.setText("Launching Helldivers 2 via Steam...")
            self.timer.start(2000)
        except Exception:
            self.label.setText("Launcher Server Failed")

    def try_attach(self):
        try:
            self.session = frida.attach(PROCESS_NAME)
            self.script = self.session.create_script(frida_script)
            self.script.load()
            if self.pending_label_text:
                self.label.setText(f"Redirect active: {self.pending_label_text}")
            else:
                self.label.setText("Redirect active")
            self.timer.stop()
            if self.pending_server:
                self.script.exports.setserver(self.pending_server)
        except frida.ProcessNotFoundError:
            self.session = None
            self.script = None
        except Exception:
            self.label.setText("Launcher Server Failed")
            self.timer.stop()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RedirectApp()
    window.show()
    sys.exit(app.exec_())