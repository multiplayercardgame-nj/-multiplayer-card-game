import random
import string
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

# All active game rooms
rooms = {}


def make_room_code():
    """Create a unique 6-character room code."""
    while True:
        code = "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=6
            )
        )

        if code not in rooms:
            return code


def make_deck():
    """Create a standard 52-card deck."""
    ranks = [
        "2", "3", "4", "5", "6", "7", "8",
        "9", "10", "J", "Q", "K", "A"
    ]

    suits = ["♠", "♥", "♦", "♣"]

    return [
        rank + suit
        for suit in suits
        for rank in ranks
    ]


def find_player(room, player_id):
    """Find a player by their ID."""
    for player in room["players"]:
        if player["id"] == player_id:
            return player

    return None


def next_turn(room):
    """Move the game to the next player's turn."""
    players = room["players"]

    if not players:
        room["current_turn"] = None
        return

    ids = [player["id"] for player in players]
    current = room["current_turn"]

    if current in ids:
        current_index = ids.index(current)
        next_index = (current_index + 1) % len(ids)

        room["current_turn"] = ids[next_index]

    else:
        room["current_turn"] = ids[0]


def make_state(room, player):
    """Create the game state sent to one player."""

    current = find_player(
        room,
        room["current_turn"]
    )

    if room["winner"]:
        status = f"{room['winner']} wins!"

    elif not room["started"]:
        status = (
            f"Lobby: {len(room['players'])}/"
            f"{room['max_players']} players"
        )

    elif current and current["id"] == player["id"]:
        status = "Your turn!"

    elif current:
        status = f"Waiting for {current['name']}"

    else:
        status = "Waiting..."

    return {
        "type": "state",

        "room_code": room["code"],

        "is_host": (
            player["id"] == room["host_id"]
        ),

        "started": room["started"],

        "game_over": bool(room["winner"]),

        "winner": room["winner"],

        "status": status,

        "top_card": room["top_card"],

        "deck_count": len(room["deck"]),

        "your_turn": (
            room["started"]
            and not room["winner"]
            and room["current_turn"] == player["id"]
        ),

        # Only this player's cards are sent to them
        "hand": player["hand"],

        "players": [
            {
                "name": p["name"],
                "cards": len(p["hand"]),
                "is_you": p["id"] == player["id"]
            }
            for p in room["players"]
        ]
    }


async def send_error(ws, message):
    """Send an error message to a client."""
    await ws.send_json({
        "type": "error",
        "message": message
    })


async def broadcast_state(room):
    """Send the current game state to every player."""

    for player in list(room["players"]):
        try:
            await player["ws"].send_json(
                make_state(room, player)
            )

        except Exception:
            pass


def initialize_game(room):
    """Create and start a new game."""

    room["deck"] = make_deck()

    random.shuffle(room["deck"])

    # Give every player 5 cards
    for player in room["players"]:
        player["hand"] = [
            room["deck"].pop()
            for _ in range(5)
        ]

    # Put one card on the table
    room["top_card"] = room["deck"].pop()

    # First player starts
    room["current_turn"] = room["players"][0]["id"]

    room["started"] = True

    room["winner"] = None


@app.get("/")
async def home():
    """Test endpoint."""
    return {
        "message": "Multiplayer card game server is running"
    }


@app.websocket("/ws")
async def game_socket(ws: WebSocket):

    await ws.accept()

    room = None
    player = None

    try:

        while True:

            data = await ws.receive_json()

            action = data.get("action")

            # ==========================================
            # CREATE ROOM
            # ==========================================

            if action == "create_room":

                if player:
                    await send_error(
                        ws,
                        "You already joined a room."
                    )
                    continue

                name = str(
                    data.get("name", "")
                ).strip()[:20]

                try:
                    maximum = int(
                        data.get("max_players", 4)
                    )

                except (ValueError, TypeError):
                    maximum = 0

                if not name or not 2 <= maximum <= 10:

                    await send_error(
                        ws,
                        "Enter a name and a player limit from 2 to 10."
                    )

                    continue

                code = make_room_code()

                player = {
                    "id": str(uuid.uuid4()),
                    "name": name,
                    "ws": ws,
                    "hand": []
                }

                room = {
                    "code": code,

                    "host_id": player["id"],

                    "max_players": maximum,

                    "players": [player],

                    "deck": [],

                    "top_card": None,

                    "current_turn": None,

                    "started": False,

                    "winner": None
                }

                rooms[code] = room

                await ws.send_json({
                    "type": "room_created",
                    "room_code": code
                })

                await broadcast_state(room)

            # ==========================================
            # JOIN ROOM
            # ==========================================

            elif action == "join_room":

                if player:

                    await send_error(
                        ws,
                        "You already joined a room."
                    )

                    continue

                code = str(
                    data.get("room_code", "")
                ).strip().upper()

                name = str(
                    data.get("name", "")
                ).strip()[:20]

                target = rooms.get(code)

                if not name:

                    await send_error(
                        ws,
                        "Enter a player name."
                    )

                elif target is None:

                    await send_error(
                        ws,
                        "Room not found."
                    )

                elif target["started"]:

                    await send_error(
                        ws,
                        "The game has already started."
                    )

                elif len(target["players"]) >= target["max_players"]:

                    await send_error(
                        ws,
                        "Room is full."
                    )

                else:

                    room = target

                    player = {
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "ws": ws,
                        "hand": []
                    }

                    room["players"].append(player)

                    await ws.send_json({
                        "type": "joined",
                        "room_code": code
                    })

                    await broadcast_state(room)

            # ==========================================
            # REQUIRE ROOM
            # ==========================================

            elif player is None or room is None:

                await send_error(
                    ws,
                    "Create or join a room first."
                )

            # ==========================================
            # START GAME
            # ==========================================

            elif action == "start_game":

                if player["id"] != room["host_id"]:

                    await send_error(
                        ws,
                        "Only the host can start."
                    )

                elif room["started"]:

                    await send_error(
                        ws,
                        "Game has already started."
                    )

                elif len(room["players"]) < 2:

                    await send_error(
                        ws,
                        "At least 2 players are required."
                    )

                else:

                    initialize_game(room)

                    await broadcast_state(room)

            # ==========================================
            # PLAY CARD
            # ==========================================

            elif action == "play_card":

                if (
                    not room["started"]
                    or room["winner"]
                ):

                    await send_error(
                        ws,
                        "The game is not active."
                    )

                    continue

                if room["current_turn"] != player["id"]:

                    await send_error(
                        ws,
                        "It is not your turn."
                    )

                    continue

                card = data.get("card")

                if (
                    not isinstance(card, str)
                    or card not in player["hand"]
                ):

                    await send_error(
                        ws,
                        "You do not have that card."
                    )

                    continue

                # Separate rank and suit
                rank = card[:-1]
                suit = card[-1]

                top_rank = room["top_card"][:-1]
                top_suit = room["top_card"][-1]

                # Card must match rank OR suit
                if (
                    rank != top_rank
                    and suit != top_suit
                ):

                    await send_error(
                        ws,
                        "Match the rank or suit of the top card."
                    )

                    continue

                # Remove card from player's hand
                player["hand"].remove(card)

                # Put card on table
                room["top_card"] = card

                # Check winner
                if not player["hand"]:

                    room["winner"] = player["name"]

                else:

                    next_turn(room)

                await broadcast_state(room)

            # ==========================================
            # DRAW CARD
            # ==========================================

            elif action == "draw_card":

                if (
                    not room["started"]
                    or room["winner"]
                    or room["current_turn"] != player["id"]
                ):

                    await send_error(
                        ws,
                        "You cannot draw now."
                    )

                    continue

                if not room["deck"]:

                    await send_error(
                        ws,
                        "The deck is empty."
                    )

                    continue

                # Draw one card
                player["hand"].append(
                    room["deck"].pop()
                )

                # Next player
                next_turn(room)

                await broadcast_state(room)

            # ==========================================
            # PASS TURN
            # ==========================================

            elif action == "pass_turn":

                if (
                    not room["started"]
                    or room["winner"]
                    or room["current_turn"] != player["id"]
                ):

                    await send_error(
                        ws,
                        "You cannot pass now."
                    )

                    continue

                next_turn(room)

                await broadcast_state(room)

            # ==========================================
            # UNKNOWN ACTION
            # ==========================================

            else:

                await send_error(
                    ws,
                    "Unknown action."
                )

    except WebSocketDisconnect:
        pass

    except Exception as error:

        print(
            "Client connection error:",
            error
        )

    finally:

        # ==========================================
        # PLAYER DISCONNECTED
        # ==========================================

        if room is not None and player is not None:

            if player in room["players"]:

                was_current = (
                    room["current_turn"]
                    == player["id"]
                )

                room["players"].remove(player)

                # Delete empty room
                if not room["players"]:

                    rooms.pop(
                        room["code"],
                        None
                    )

                else:

                    # Transfer host
                    if (
                        room["host_id"]
                        == player["id"]
                    ):

                        room["host_id"] = (
                            room["players"][0]["id"]
                        )

                    # Transfer turn
                    if was_current:

                        room["current_turn"] = (
                            room["players"][0]["id"]
                        )

                    await broadcast_state(room)

        try:

            await ws.close()

        except Exception:

            pass