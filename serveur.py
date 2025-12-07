import asyncio
from aiohttp import web
import json
import os

import os
SERVER_PASSWORD = os.getenv("SERVER_PASSWORD")

USER_DB_FILE = "users.json"
admin_username = "Purple_key"

clients = {}           # ws -> username
pending_requests = []  # (ws_client, new_user, new_pass)
admin_queues = {}      # ws_admin -> asyncio.Queue()
admin_waiting = {}     # ws_admin -> bool

# Charger la base utilisateur
try:
    with open(USER_DB_FILE, "r") as f:
        USER_DB = json.load(f)
except FileNotFoundError:
    USER_DB = {}

def save_users():
    with open(USER_DB_FILE, "w") as f:
        json.dump(USER_DB, f)


# -------------------------------------------------
# WS HANDLER
# -------------------------------------------------
async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    print("Nouvelle connexion WS")

    try:
        # --------------------------
        # AUTH SERVEUR
        # --------------------------
        msg = await ws.receive_str()
        if not msg.startswith("[AUTH] "):
            await ws.close()
            return ws

        pwd = msg.split(" ", 1)[1].strip()
        if pwd != SERVER_PASSWORD:
            await ws.send_str("ERREUR: Mauvais mot de passe serveur.")
            await ws.close()
            return ws

        await ws.send_str("OK_SERVEUR")

        # --------------------------
        # REGISTER OU LOGIN
        # --------------------------
        msg = await ws.receive_str()

        # --------------------------------
        # REGISTER (demande admin)
        # --------------------------------
        if msg.startswith("[NEWUSER] "):
            _, new_user, new_pass = msg.split(" ", 2)

            admin_ws = next((c for c, u in clients.items() if u == admin_username), None)

            if admin_ws:
                # envoyer la demande
                await admin_ws.send_str(f"[REQUEST] création : <{new_user}>")

                # placer l’admin en attente
                admin_waiting[admin_ws] = True

                # attendre la réponse
                decision = await admin_queues[admin_ws].get()

                if decision == "y":
                    USER_DB[new_user] = new_pass
                    save_users()

                    clients[ws] = new_user
                    await ws.send_str("OK_NEWUSER")
                else:
                    await ws.send_str("REFUSE_CREATION")

            else:
                # aucun admin connecté → mettre en file
                pending_requests.append((ws, new_user, new_pass))
                await ws.send_str("OK_WAITING_ADMIN")

        # --------------------------------
        # LOGIN
        # --------------------------------
        elif msg.startswith("[LOGIN] "):
            _, user, upass = msg.split(" ", 2)

            if user == admin_username or (user in USER_DB and USER_DB[user] == upass):

                clients[ws] = user
                await ws.send_str("OK_LOGIN")

                # admin → créer une queue perso
                if user == admin_username:
                    admin_queues[ws] = asyncio.Queue()

                    # traiter demandes en attente
                    for req_ws, u, p in pending_requests.copy():
                        await ws.send_str(f"[REQUEST] création : <{u}>")
                        decision = await admin_queues[ws].get()

                        if decision == "y":
                            USER_DB[u] = p
                            save_users()
                            await req_ws.send_str("OK_NEWUSER")
                            clients[req_ws] = u
                        else:
                            await req_ws.send_str("REFUSE_CREATION")

                        pending_requests.remove((req_ws, u, p))

            else:
                await ws.send_str("ERREUR: ID ou mot de passe incorrect.")
                return ws
        else:
            await ws.send_str("ERREUR: Format invalide.")
            return ws

        # --------------------------
        # BOUCLE PRINCIPALE
        # --------------------------
        async for message in ws:
            if message.type != web.WSMsgType.TEXT:
                continue

            txt = message.data.strip()
            username = clients.get(ws, "???")

            # ADMIN EN MODE "y/n"
            if ws in admin_waiting and admin_waiting[ws]:
                admin_waiting[ws] = False
                await admin_queues[ws].put(txt.lower())
                continue

            # MESSAGE NORMAL
            print(f"{username}: {txt}")

            # broadcast
            for cli in clients:
                if cli != ws and not cli.closed:
                    await cli.send_str(f"[{username}] {txt}")

    finally:
        # nettoyage propre
        if ws in clients:
            print(f"{clients[ws]} déconnecté.")
            del clients[ws]
        if ws in admin_queues:
            del admin_queues[ws]
        if ws in admin_waiting:
            del admin_waiting[ws]

    return ws


# -------------------------------------------------
# HTTP
# -------------------------------------------------
async def http_root(request):
    return web.Response(text="Purple-msg server OK. WebSocket: /ws")


# -------------------------------------------------
# APP
# -------------------------------------------------
def create_app():
    app = web.Application()
    app.router.add_get("/", http_root)
    app.router.add_get("/ws", ws_handler)
    return app


if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 10000))
    print(f"Serveur lancé sur port {PORT}")
    web.run_app(create_app(), host="0.0.0.0", port=PORT)
