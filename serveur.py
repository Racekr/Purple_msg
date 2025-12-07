import asyncio
from aiohttp import web
import json
import os

SERVER_PASSWORD = "1234"
USER_DB_FILE = "users.json"

clients = {}  # ws -> username
pending_requests = []  # (ws_client, new_user, new_pass)
admin_username = "Purple_key"

# Charger la base utilisateur
try:
    with open(USER_DB_FILE, "r") as f:
        USER_DB = json.load(f)
except FileNotFoundError:
    USER_DB = {}

def save_users():
    with open(USER_DB_FILE, "w") as f:
        json.dump(USER_DB, f)

# ---------------------------
# HTTP Handler
# ---------------------------
async def http_root(request):
    return web.Response(text="Purple-msg server OK. WebSocket: /ws")

# ---------------------------
# WebSocket Handler
# ---------------------------
async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    print("Nouvelle connexion WS")

    try:
        # --- Auth serveur ---
        msg = await ws.receive_str()
        if not msg.startswith("[AUTH] "):
            await ws.send_str("ERREUR: Auth manquante.")
            await ws.close()
            return ws

        pwd = msg.split(" ", 1)[1].strip()
        if pwd != SERVER_PASSWORD:
            await ws.send_str("ERREUR: Mauvais mot de passe serveur.")
            await ws.close()
            return ws

        await ws.send_str("OK_SERVEUR")

        # --- Register ou Login ---
        msg = await ws.receive_str()

        # REGISTER
        if msg.startswith("[NEWUSER] "):
            _, new_user, new_pass = msg.split(" ", 2)
            admin_ws = next((c for c, u in clients.items() if u == admin_username), None)

            if admin_ws:
                # Envoi simple de la demande au serveur admin
                await admin_ws.send_str(f"[REQUEST] création : <{new_user}>")
                decision = await admin_ws.receive_str()
                if decision.lower() == "y":
                    USER_DB[new_user] = new_pass
                    save_users()
                    await ws.send_str("OK_NEWUSER")
                    print(f"Admin a validé {new_user}")
                else:
                    await ws.send_str("REFUSE_CREATION")
                    print(f"Admin a refusé {new_user}")
            else:
                pending_requests.append((ws, new_user, new_pass))
                await ws.send_str("OK_WAITING_ADMIN")
                print(f"Demande stockée pour {new_user}")

        # LOGIN
        elif msg.startswith("[LOGIN] "):
            _, user, upass = msg.split(" ", 2)
            if user == admin_username or (user in USER_DB and USER_DB[user] == upass):
                clients[ws] = user
                await ws.send_str("OK_LOGIN")

                # Si admin, notifier les demandes en attente
                if user == admin_username and pending_requests:
                    for req_ws, new_user, new_pass in pending_requests.copy():
                        await ws.send_str(f"[REQUEST] création : <{new_user}>")
                        decision = await ws.receive_str()
                        if decision.lower() == "y":
                            USER_DB[new_user] = new_pass
                            save_users()
                            await req_ws.send_str("OK_NEWUSER")
                        else:
                            await req_ws.send_str("REFUSE_CREATION")
                        pending_requests.remove((req_ws, new_user, new_pass))

            else:
                await ws.send_str("ERREUR: ID ou mot de passe incorrect.")
                return ws
        else:
            await ws.send_str("ERREUR: Format invalide.")
            return ws

        # --- Boucle chat ---
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                sender = clients.get(ws, "???")
                print(f"{sender}: {msg.data}")
                for client in clients.keys():
                    if client != ws:
                        await client.send_str(f"[{sender}] {msg.data}")

    finally:
        if ws in clients:
            print(f"{clients[ws]} déconnecté.")
            del clients[ws]

    return ws

# ---------------------------
# Création de l'app
# ---------------------------
def create_app():
    app = web.Application()
    app.router.add_get("/", http_root)
    app.router.add_get("/ws", ws_handler)
    return app

# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 10000))
    print(f"Serveur lancé sur port {PORT}")
    web.run_app(create_app(), host="0.0.0.0", port=PORT)
