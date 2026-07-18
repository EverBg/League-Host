import json
import os

FILE = os.path.join(os.path.dirname(__file__), "data", "games.json")


def ensure_file():
    directory = os.path.dirname(FILE)
    if not os.path.exists(directory):
        os.makedirs(directory)

    if not os.path.exists(FILE):
        with open(FILE, "w") as f:
            json.dump({}, f, indent=4)


ensure_file()


def load_games():
    with open(FILE, "r") as f:
        return json.load(f)


def save_games(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)


def create_game(
    game_id,
    host_id,
    host_name,
    gametype,
    matchtype,
    region,
    vip,
    thread_id,
    message_id,
    players_needed=1,
    channel_id=None
):
    games = load_games()

    games[game_id] = {
        "host_id": host_id,
        "host_name": host_name,
        "gametype": gametype,
        "matchtype": matchtype,
        "region": region,
        "vip": vip,
        "thread": thread_id,
        "message": message_id,
        "channel": channel_id,
        "players_needed": players_needed,
        "players": [],
        "finished": False,
        "locked": False
    }

    save_games(games)


def delete_game(game_id):
    games = load_games()

    if game_id in games:
        del games[game_id]

    save_games(games)


def get_game(game_id):
    games = load_games()
    return games.get(game_id)


def add_player(game_id, player):
    """player is a dict: {"id": int, "display_name": str, "rank": str}"""
    games = load_games()

    if game_id not in games:
        return

    if not any(p["id"] == player["id"] for p in games[game_id]["players"]):
        games[game_id]["players"].append(player)

    save_games(games)


def remove_player(game_id, player_id):
    games = load_games()

    if game_id not in games:
        return

    games[game_id]["players"] = [
        p for p in games[game_id]["players"] if p["id"] != player_id
    ]

    save_games(games)


def get_game_by_thread(thread_id):
    games = load_games()

    for game_id, game in games.items():
        if game.get("thread") == thread_id:
            return game_id, game

    return None, None


def get_player(game_id, player_id):
    game = get_game(game_id)

    if not game:
        return None

    for p in game["players"]:
        if p["id"] == player_id:
            return p

    return None


def set_finished(game_id, finished=True):
    games = load_games()

    if game_id not in games:
        return

    games[game_id]["finished"] = finished
    save_games(games)
