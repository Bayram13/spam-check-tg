# Telegram Qrup Mühafizə Botu (CAPTCHA / Robot Doğrulaması)

Yeni qoşulan üzvü dərhal **susdurur (mute)**, şəkildə təhrif olunmuş yazı +
variant düymələri göndərir. Üzvün **30 saniyə** vaxtı var:

- ✅ Düzgün seçərsə → susdurma götürülür, qrupda yaza bilər.
- ❌ Yanlış seçərsə → susdurulmuş qalır.
- ⏱ Vaxt bitərsə → susdurulmuş qalır.

Bu, scammer/spam botların qrupa avtomatik mesaj yazmasının qarşısını alır.

---

## 1. Bot yaratmaq (@BotFather)

1. Telegram-da [@BotFather](https://t.me/BotFather) ilə danışın → `/newbot`.
2. Ad və username verin, sizə **token** verəcək (məs: `123456:ABC-DEF...`).
3. `/setprivacy` → botu seçin → **Disable** (qrupda hadisələri görməsi üçün).

## 2. Botu qrupa admin əlavə etmək

Botu qrupa əlavə edin və **admin** edin. Bu icazələr LAZIMDIR:
- **Ban users** (Üzvləri ban/məhdudlaşdırmaq) — mute/unmute üçün.
- **Delete messages** (Mesajları silmək) — CAPTCHA mesajını silmək üçün.

> Qeyd: Bot yalnız özündən SONRA qoşulan üzvləri görür.

## 3. Quraşdırma və işə salma

```bash
pip install -r requirements.txt

export BOT_TOKEN="BotFather-dən aldığınız token"
# (istəyə görə) tənzimləmələr:
export CAPTCHA_TIMEOUT=30      # cavab vaxtı (saniyə)
export CAPTCHA_OPTIONS=4       # variant sayı
export KICK_ON_FAIL=0          # 1 = yanlış/vaxt bitəndə qrupdan at; 0 = sadəcə mute qalsın

python bot.py
```

Bot 24/7 işləməlidir — bir VPS / server / Raspberry Pi üzərində saxlayın.

## 4. Serverdə daimi işlətmək (systemd nümunəsi)

`/etc/systemd/system/tg-captcha.service`:

```ini
[Unit]
Description=Telegram CAPTCHA Bot
After=network.target

[Service]
WorkingDirectory=/opt/tg_captcha_bot
Environment=BOT_TOKEN=SIZIN_TOKEN
ExecStart=/usr/bin/python3 /opt/tg_captcha_bot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now tg-captcha
```

---

## Fayllar
- `bot.py` — əsas bot məntiqi.
- `captcha.py` — CAPTCHA şəkli və variantların yaradılması.
- `requirements.txt` — asılılıqlar.

## Tənzimləmə ideyaları
- `captcha.py` içində `ALPHABET`, `CODE_LEN` dəyişib mürəkkəbliyi artıra bilərsiniz.
- Yanlış cavabda dərhal atmaq üçün `KICK_ON_FAIL=1`.
