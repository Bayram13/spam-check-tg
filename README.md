# Telegram Qrup Mühafizə Botu (CAPTCHA / Robot Doğrulaması)

Yeni qoşulan üzvü dərhal **susdurur (mute)**, şəkildə təhrif olunmuş yazı +
variant düymələri göndərir. Üzvün **30 saniyə** vaxtı var:

- ✅ Düzgün seçərsə → susdurma götürülür, qrupda yaza bilər.
- ❌ Yanlış seçərsə → susdurulmuş qalır.
- ⏱ Vaxt bitərsə → susdurulmuş qalır.

Bu, scammer/spam botların qrupa avtomatik mesaj yazmasının qarşısını alır.

İki rejimdə işləyir:
- **webhook** → Render **Web Service** üçün (PORT-a bağlanır). Render-də belə işlədin.
- **polling** → Render **Background Worker** və ya lokal kompüter üçün.

---

## 1. Bot yaratmaq (@BotFather)

1. Telegram-da [@BotFather](https://t.me/BotFather) ilə `/newbot` → token alın
   (məs: `123456:ABC-DEF...`).
2. `/setprivacy` → botu seçin → **Disable** (qrupda hadisələri görməsi üçün).

## 2. Botu qrupa admin əlavə etmək

Botu qrupa əlavə edin və **admin** edin. Bu icazələr LAZIMDIR:
- **Ban users** — mute/unmute üçün.
- **Delete messages** — CAPTCHA mesajını silmək üçün.

---

## 3. Render.com-da işə salmaq (tövsiyə: webhook)

### Variant A — Blueprint (`render.yaml`) ilə (ən asan)
1. Bu faylları bir **GitHub repo**-ya yükləyin.
2. Render Dashboard → **New** → **Blueprint** → repo-nu seçin.
3. Render `render.yaml`-ı oxuyur. Yalnız **BOT_TOKEN**-i əl ilə daxil edin.
4. **Apply** → deploy bitəndə bot avtomatik webhook qurur və işləyir.

### Variant B — əl ilə Web Service
1. Render → **New** → **Web Service** → repo-nu bağlayın.
2. **Build Command:** `pip install -r requirements.txt`
3. **Start Command:** `python bot.py`
4. **Environment** bölməsinə bu dəyişənləri əlavə edin:

   | Key              | Value                          |
   |------------------|--------------------------------|
   | `BOT_TOKEN`      | BotFather-dən aldığınız token  |
   | `MODE`           | `webhook`                      |
   | `CAPTCHA_TIMEOUT`| `30`                           |
   | `CAPTCHA_OPTIONS`| `4`                            |
   | `KICK_ON_FAIL`   | `0`                            |

   > `PORT` və `RENDER_EXTERNAL_URL` Render tərəfindən **avtomatik** verilir,
   > onları əlavə etməyə ehtiyac yoxdur. İstəsəniz əlavə təhlükəsizlik üçün
   > təsadüfi `WEBHOOK_SECRET` də əlavə edə bilərsiniz.

5. **Create Web Service** → loglarda `Webhook rejimi işə düşdü` görünməlidir.

> ⚠️ **Render pulsuz (free) Web Service 15 dəq fəaliyyətsizlikdən sonra yatır.**
> Yuxu zamanı yeni qoşulan üzvlər gec doğrulana bilər (Telegram bir müddət
> yenidən cəhd edir, ilk sorğu botu oyadır). Daimi (24/7) iş üçün:
> - pulsuz qalmaq istəyirsinizsə xarici bir "ping" servisi ilə hər 10 dəq URL-ə
>   sorğu göndərin (məs. UptimeRobot), **və ya**
> - pulsuz **Background Worker** + `MODE=polling` istifadə edin (port lazım deyil),
>   **və ya** ödənişli plan seçin.

### Variant C — Background Worker (polling)
- Render → **New** → **Background Worker**.
- **Start Command:** `python bot.py`
- Env: `BOT_TOKEN` + `MODE=polling` (webhook/PORT lazım deyil).

---

## 4. Lokal işə salma (test üçün)

```bash
pip install -r requirements.txt
export BOT_TOKEN="sizin_token"
export MODE=polling
python bot.py
```

---

## Konfiqurasiya (mühit dəyişənləri)

| Dəyişən           | Default   | İzah |
|-------------------|-----------|------|
| `BOT_TOKEN`       | —         | (MƏCBURİ) BotFather token |
| `MODE`            | `polling` | `webhook` (Render Web Service) və ya `polling` |
| `CAPTCHA_TIMEOUT` | `30`      | Cavab vaxtı (saniyə) |
| `CAPTCHA_OPTIONS` | `4`       | Variant sayı |
| `KICK_ON_FAIL`    | `0`       | `1` = yanlış cavab/vaxt bitəndə qrupdan at |
| `WEBHOOK_URL`     | —         | (istəyə görə) Render `RENDER_EXTERNAL_URL`-i avtomatik istifadə edir |
| `WEBHOOK_SECRET`  | —         | (istəyə görə) webhook üçün gizli token |
| `PORT`            | `10000`   | Render avtomatik təyin edir |

## Fayllar
- `bot.py` — əsas bot məntiqi (webhook + polling).
- `captcha.py` — CAPTCHA şəkli + variant generatoru.
- `DejaVuSans-Bold.ttf` — CAPTCHA fontu (Render mühitində sistem fontu olmaya bilər).
- `render.yaml` — Render Blueprint.
- `runtime.txt` — Python versiyası.
- `requirements.txt` — asılılıqlar.
