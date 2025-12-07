# serveur.py
import asyncio
from aiohttp import web
import json
import os

SERVER_PASSWORD = "1234"
USER_DB_FILE = "users.json"
admin_username = "Purple_key"

clients = {}           # ws -> username
pending_requests = []  # list of tuples (req_ws, new_user, new_pass)

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
# WebSocket Handler
# ---------------------------
async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print("Nouvelle connexion WS")

    try:
        # --- Auth serveur ---
        msg = await ws.receive()
        if msg.type != web.WSMsgType.TEXT:
            await ws.send_str("ERREUR: Auth manquante.")
            await ws.close()
            return ws
        text = msg.data.strip()
        if not text.startswith("[AUTH] "):
            await ws.send_str("ERREUR: Auth manquante.")
            await ws.close()
            return ws

        pwd = text.split(" ", 1)[1].strip()
        if pwd != SERVER_PASSWORD:
            await ws.send_str("ERREUR: Mauvais mot de passe serveur.")
            await ws.close()
            return ws

        await ws.send_str("OK_SERVEUR")

        # --- Register ou Login ---
        msg = await ws.receive()
        if msg.type != web.WSMsgType.TEXT:
            await ws.send_str("ERREUR: Format invalide.")
            await ws.close()
            return ws
        text = msg.data.strip()

        # REGISTER request
        if text.startswith("[NEWUSER] "):
            _, new_user, new_pass = text.split(" ", 2)
            admin_ws = next((s for s, u in clients.items() if u == admin_username), None)

            if admin_ws:
                # send request to admin(s) (no walls)
                await admin_ws.send_str(f"[REQUEST] création : <{new_user}>")
                # store pending request so admin can decide later
                pending_requests.append((ws, new_user, new_pass))
                await ws.send_str("OK_WAITING_ADMIN")
                print(f"Demande stockée et envoyée à admin pour {new_user}")
            else:
                pending_requests.append((ws, new_user, new_pass))
                await ws.send_str("OK_WAITING_ADMIN")
                print(f"Demande stockée (admin absent) pour {new_user}")

        # LOGIN
        elif text.startswith("[LOGIN] "):
            _, user, upass = text.split(" ", 2)

            # validate credentials
            if user == admin_username or (user in USER_DB and USER_DB[user] == upass):
                # register the client BEFORE sending OK_LOGIN to avoid racing
                clients[ws] = user
                await ws.send_str("OK_LOGIN")
                print(f"Utilisateur {user} connecté.")

                # If this is the admin, notify them of any pending requests
                if user == admin_username and pending_requests:
                    # send all pending requests (do not wait)
                    for req_ws, pending_user, _ in pending_requests:
                        await ws.send_str(f"[REQUEST] création : <{pending_user}>")
            else:
                await ws.send_str("ERREUR: ID ou mot de passe incorrect.")
                await ws.close()
                return ws
        else:
            await ws.send_str("ERREUR: Format invalide.")
            await ws.close()
            return ws

        # --- Boucle principale (reception de messages) ---
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue
            content = msg.data.strip()

            sender = clients.get(ws, "???")

            # If sender is admin and sends a decision like "y username" or "n username"
            if sender == admin_username:
                # accept: "y username"  or "Y username"
                if content.startswith("y ") or content.startswith("Y "):
                    parts = content.split(" ", 1)
                    if len(parts) == 2:
                        uname = parts[1].strip()
                        # find pending
                        for req_ws, pending_user, pending_pass in pending_requests.copy():
                            if pending_user == uname:
                                USER_DB[uname] = pending_pass
                                save_users()
                                await req_ws.send_str("OK_NEWUSER")
                                pending_requests.remove((req_ws, pending_user, pending_pass))
                                print(f"Admin a validé {uname}")
                                break
                        continue
                # refuse: "n username"
                if content.startswith("n ") or content.startswith("N "):
                    parts = content.split(" ", 1)
                    if len(parts) == 2:
                        uname = parts[1].strip()
                        for req_ws, pending_user, pending_pass in pending_requests.copy():
                            if pending_user == uname:
                                await req_ws.send_str("REFUSE_CREATION")
                                pending_requests.remove((req_ws, pending_user, pending_pass))
                                print(f"Admin a refusé {uname}")
                                break
                        continue

            # Normal chat message: broadcast to other clients
            print(f"{sender}: {content}")
            for client_ws in list(clients.keys()):
                if client_ws != ws:
                    try:
                        await client_ws.send_str(f"[{sender}] {content}")
                    except Exception:
                        pass

    finally:
        # cleanup
        if ws in clients:
            print(f"{clients[ws]} déconnecté.")
            del clients[ws]
        # if this ws had any pending requests as requester, remove them
        pending_requests[:] = [(r,u,p) for (r,u,p) in pending_requests if r != ws]

    return ws

# ---------------------------
# HTTP Handler
# ---------------------------
async def http_root(request):
    return web.Response(text="Purple-msg server OK. WebSocket: /ws")

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
