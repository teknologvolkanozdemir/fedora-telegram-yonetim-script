#!/usr/bin/env python3
"""Fedora (x86_64) sistemini Telegram uzerinden yoneten bot (yalnizca standart kutuphane)."""
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

PKG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+:-]*$")
VERSION_RE = re.compile(r"^[0-9]{2,3}$")

HELP = (
    "Komutlar:\n"
    "/shutdown - bilgisayarı kapat\n"
    "/reboot - yeniden başlat\n"
    "/logout - oturumu kapat\n"
    "/lock - ekranı kilitle\n"
    "/update - paketleri güncelle (dnf upgrade --refresh)\n"
    "/upgrade <sürüm> - Fedora sürümünü yükselt (dnf system-upgrade)\n"
    "/upgrade_reboot - indirilen yükseltmeyi uygulamak için yeniden başlat\n"
    "/install <paket> - program kur\n"
    "/remove <paket> - program kaldır\n"
    "/cancel - bekleyen işlemi iptal et"
)


def build_command(name, arg=None):
    """Return (argv, needs_sudo) for a command, or None if invalid."""
    if name == "shutdown":
        return ["systemctl", "poweroff"], True
    if name == "reboot":
        return ["systemctl", "reboot"], True
    if name == "logout":
        return ["loginctl", "terminate-user", str(os.getuid())], False
    if name == "lock":
        return ["loginctl", "lock-session"], False
    if name == "update":
        return ["dnf", "upgrade", "--refresh", "-y"], True
    if name == "upgrade":
        if not arg or not VERSION_RE.match(arg):
            return None
        return ["dnf", "system-upgrade", "download", "--releasever=" + arg, "-y"], True
    if name == "upgrade_reboot":
        return ["dnf", "system-upgrade", "reboot"], True
    if name in ("install", "remove"):
        if not arg:
            return None
        pkgs = arg.split()
        if not all(PKG_RE.match(p) for p in pkgs):
            return None
        return ["dnf", name, "-y"] + pkgs, True
    return None


def sudo_needs_password():
    if os.geteuid() == 0:
        return False
    return subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode != 0


def run(argv, needs_sudo, pw=None, timeout=3600):
    """Run command; returns (returncode, output)."""
    inp = None
    if needs_sudo and os.geteuid() != 0:
        argv = ["sudo", "-S", "-k", "-p", ""] + argv if pw is not None else ["sudo", "-n"] + argv
        if pw is not None:
            inp = pw + "\n"
    try:
        p = subprocess.run(argv, input=inp, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 1, "Zaman aşımı."
    except FileNotFoundError as e:
        return 127, str(e)
    return p.returncode, (p.stdout + p.stderr).strip()


class Bot:
    def __init__(self, token, allowed):
        self.api = "https://api.telegram.org/bot%s/" % token
        self.allowed = allowed
        self.pending = {}  # chat_id -> (name, arg)

    def call(self, method, **params):
        data = urllib.parse.urlencode(params).encode()
        with urllib.request.urlopen(self.api + method, data, timeout=70) as r:
            return json.load(r)

    def send(self, chat_id, text):
        self.call("sendMessage", chat_id=chat_id, text=text[-3500:] or "(çıktı yok)")

    def execute(self, chat_id, name, arg, pw=None):
        cmd = build_command(name, arg)
        argv, sudo = cmd
        self.send(chat_id, "Çalıştırılıyor: " + name)
        code, out = run(argv, sudo, pw)
        if code != 0 and "incorrect password" in out.lower():
            self.pending[chat_id] = (name, arg)
            self.send(chat_id, "Parola hatalı, tekrar gönderin (iptal: /cancel).")
            return
        self.send(chat_id, ("Tamamlandı." if code == 0 else "Hata (%d)." % code) + "\n" + out)

    def handle(self, msg):
        chat_id = msg["chat"]["id"]
        if chat_id not in self.allowed:
            return
        text = (msg.get("text") or "").strip()
        if chat_id in self.pending and not text.startswith("/"):
            name, arg = self.pending.pop(chat_id)
            try:
                self.call("deleteMessage", chat_id=chat_id, message_id=msg["message_id"])
            except Exception:
                pass
            self.execute(chat_id, name, arg, text)
            return
        if not text.startswith("/"):
            return
        parts = text[1:].split(None, 1)
        name = parts[0].split("@")[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else None
        if name in ("start", "help"):
            self.send(chat_id, HELP)
        elif name == "cancel":
            self.pending.pop(chat_id, None)
            self.send(chat_id, "İptal edildi.")
        elif build_command(name, arg) is None:
            self.send(chat_id, "Geçersiz komut veya argüman.\n\n" + HELP)
        elif build_command(name, arg)[1] and sudo_needs_password():
            self.pending[chat_id] = (name, arg)
            self.send(chat_id, "sudo parolası gerekiyor. Parolanızı gönderin (mesaj silinmeye çalışılır; iptal: /cancel).")
        else:
            self.execute(chat_id, name, arg)

    def loop(self):
        offset = 0
        while True:
            try:
                res = self.call("getUpdates", offset=offset, timeout=60)
                for u in res.get("result", []):
                    offset = u["update_id"] + 1
                    if "message" in u:
                        self.handle(u["message"])
            except Exception as e:
                print("Hata:", e, file=sys.stderr)
                time.sleep(5)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    ids = os.environ.get("ALLOWED_CHAT_IDS", "")
    allowed = {int(i) for i in ids.replace(",", " ").split() if i.lstrip("-").isdigit()}
    if not token or not allowed:
        sys.exit("TELEGRAM_BOT_TOKEN ve ALLOWED_CHAT_IDS ortam değişkenleri gerekli.")
    if platform.machine() != "x86_64":
        print("Uyarı: x86_64 dışı mimari:", platform.machine(), file=sys.stderr)
    Bot(token, allowed).loop()


if __name__ == "__main__":
    main()
