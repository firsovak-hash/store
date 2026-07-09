#!/usr/bin/env bash
# Локальный запуск STORE как Telegram Mini App одной командой:
#   ./start.sh
# Поднимает Flask (:8080) → SSH-туннель localhost.run (HTTPS) →
# вписывает свежий URL в .env (WEBAPP_URL) → запускает бота.
# Ctrl+C останавливает всё разом.

cd "$(dirname "$0")" || exit 1

PIDS=()
cleanup() {
    echo ""
    echo "⏹  Останавливаю Flask, туннель и бота…"
    for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null; done
    exit 0
}
trap cleanup INT TERM EXIT

# 0. Освобождаем порт 8080, если занят прошлым запуском
lsof -ti tcp:8080 2>/dev/null | xargs kill 2>/dev/null

# 1. Flask
echo "▶  Запускаю Flask на :8080…"
python3 app.py > flask.log 2>&1 &
PIDS+=($!)
for i in $(seq 1 20); do
    curl -s -o /dev/null http://localhost:8080/ && break
    sleep 0.5
done

# 2. Туннель localhost.run (HTTPS без аккаунта)
echo "▶  Поднимаю туннель localhost.run…"
: > tunnel.log
# -T отключает PTY (в фоне его всё равно нет) — URL печатается через stdout
ssh -T -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 \
    -o ExitOnForwardFailure=yes \
    -R 80:localhost:8080 localhost.run > tunnel.log 2>&1 &
SSH_PID=$!
PIDS+=($SSH_PID)

URL=""
for i in $(seq 1 30); do
    # Проверяем, жив ли ещё SSH-процесс
    if ! kill -0 "$SSH_PID" 2>/dev/null; then
        echo "✗  SSH-туннель упал. Лог:"
        cat tunnel.log
        exit 1
    fi
    URL=$(grep -oE 'https://[a-z0-9]+\.lhr\.life' tunnel.log | head -1)
    [ -n "$URL" ] && break
    sleep 1
done
if [ -z "$URL" ]; then
    echo "✗  Не удалось получить URL туннеля за 30 сек. Лог:"
    tail -n 20 tunnel.log
    exit 1
fi
echo "✔  Туннель: $URL"

# 3. Прописываем свежий URL в .env
if grep -q '^WEBAPP_URL=' .env 2>/dev/null; then
    sed -i '' "s#^WEBAPP_URL=.*#WEBAPP_URL=$URL#" .env
else
    echo "WEBAPP_URL=$URL" >> .env
fi
echo "✔  .env → WEBAPP_URL обновлён"

# 4. Бот (в этом же окне; Ctrl+C гасит всё через trap)
echo "▶  Запускаю бота @TYTYuiop09_bot… (Ctrl+C — остановить всё)"
echo "────────────────────────────────────────────"
python3 bot.py
