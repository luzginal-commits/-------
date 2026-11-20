"""Дворовый пенальти — запуск: python app.py (Python 3.10+)."""

import json
import random
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def resolve_shot(direction, power, history):
    # Последние удары важнее старых; замечаем повторы и чередование углов.
    weights = [1.0, 1.0, 1.0]
    for age, previous in enumerate(reversed(history)):
        weights[previous] += 2.4 / (age + 1)
    if len(history) >= 2 and history[-1] == history[-2]:
        weights[history[-1]] += 4
    elif len(history) >= 3 and history[-1] == history[-3]:
        weights[history[-2]] += 5
    keeper = random.choices(range(3), weights=weights)[0]
    if power <= 45:
        keeper = direction
        outcome = "save"
    elif power > 92:
        outcome = "miss"
    else:
        # На медленный мяч успевает среагировать даже после неверного прогноза.
        reaction_chance = max(0.08, 0.6 - (power - 46) * 0.011)
        if keeper != direction and random.random() < reaction_chance:
            keeper = direction
        catch_chance = 1.0 if power < 72 else max(0.58, 0.86 - (power - 72) * 0.012)
        outcome = "save" if keeper == direction and random.random() < catch_chance else "goal"
    return {"keeper": keeper, "outcome": outcome}


def keeper_shot_point():
    # Три четверти ударов направляем в один из четырёх углов.
    if random.random() < 0.75:
        x_range = random.choice(((0.12, 0.28), (0.72, 0.88)))
        y_range = random.choice(((0.24, 0.36), (0.64, 0.76)))
        return random.uniform(*x_range), random.uniform(*y_range)
    return random.uniform(0.12, 0.88), random.uniform(0.24, 0.76)


def resolve_keeper(direction, target=None):
    if target is not None:
        shot_x, shot_y = keeper_shot_point()
        caught = ((target["x"] - shot_x) / 0.23) ** 2 + ((target["y"] - shot_y) / 0.35) ** 2 <= 1
        outcome = "save" if caught else "goal"
        return {"keeper": direction, "outcome": outcome, "shotX": shot_x, "shotY": shot_y}
    shot_direction = random.randrange(3)
    outcome = "save" if direction == shot_direction else "goal"
    return {"keeper": direction, "direction": shot_direction, "outcome": outcome}


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        body = (ROOT / "index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/shot":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 2048:
                raise ValueError()
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError()
            role = data.get("role", "striker")
            if role not in ("striker", "keeper"):
                raise ValueError()
            direction, power, history = data["direction"], data["power"], data["history"]
            if (type(direction) is not int or direction not in range(3)
                    or type(power) not in (int, float) or not 0 <= power <= 100
                    or not isinstance(history, list) or len(history) > 4
                    or any(type(i) is not int or i not in range(3) for i in history)):
                raise ValueError()
            target = data.get("keeperTarget")
            if target is not None and (not isinstance(target, dict) or any(
                    type(target.get(axis)) not in (int, float) or not 0 <= target[axis] <= 1
                    for axis in ("x", "y"))):
                raise ValueError()
            result = resolve_keeper(direction, target) if role == "keeper" else resolve_shot(direction, power, history)
            self.send_json(200, result)
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Некорректный удар"})


if __name__ == "__main__":
    address = "http://127.0.0.1:5000"
    try:
        server = HTTPServer(("127.0.0.1", 5000), Handler)
    except OSError as exc:
        raise SystemExit(f"Не удалось запустить игру: {exc}. Возможно, порт 5000 уже занят.")
    print(f"Игра запущена: {address}\nДля остановки нажмите Ctrl+C.")
    webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nИгра остановлена.")
    finally:
        server.server_close()
