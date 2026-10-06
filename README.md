# fedora-telegram-yonetim-script
x86 mimarisinde çalışan fedora işletim sisteminizi telegramdan yönetin. güncelleme, kapatma, yeniden başlatma, ekranı kilitleme, program kur, kaldır işlemlerini yapmak için yapıldı.

## Kullanım

```
export TELEGRAM_BOT_TOKEN=...      # BotFather'dan alınan token
export ALLOWED_CHAT_IDS="12345"    # yetkili chat id'leri (boşluk/virgül ile)
python3 bot.py
```

Komutlar: `/shutdown /reboot /logout /lock /update /upgrade <sürüm> /upgrade_reboot /install <paket> /remove <paket> /cancel`.
sudo parolası gerekirse bot parolayı Telegram'dan ister; parola yalnızca ilgili komuta iletilir, saklanmaz.
Bot, oturum kullanıcısı olarak çalıştırılmalıdır (lock/logout için).
