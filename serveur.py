import asyncio
from aiohttp import web
import os
from motor.motor_asyncio import AsyncIOMotorClient

SERVER_PASSWORD = os.getenv("SERVER_PASSWORD")
MONGO_URI = os.getenv("MONGO_URI")  # À configurer sur Render

admin_username = "Purple_key"

# MongoDB setup
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.purple_msg
users_collection = db.users

clients = {}
pending_requests = []
admin_queues = {}
admin_waiting = {}


async def get_user(username):
    """Récupérer un utilisateur de MongoDB"""
    return await users_collection.find_one({"username": username})


async def create_user(username, password):
    """Créer un utilisateur dans MongoDB"""
    await users_collection.insert_one({
        "username": username,
        "password": password
    })


async def user_exists(username):
    """Vérifier si un utilisateur existe"""
    return await users_collection.count_documents({"username": username}) > 0


# -------------------------------------------------
# WS HANDLER
# -------------------------------------------------
async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    print("Nouvelle connexion WS")

    try:
        # AUTH SERVEUR
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

        # REGISTER OU LOGIN
        msg = await ws.receive_str()

        # REGISTER
        if msg.startswith("[NEWUSER] "):
            _, new_user, new_pass = msg.split(" ", 2)

            if await user_exists(new_user) or new_user == admin_username:
                await ws.send_str("ERREUR: Ce nom d'utilisateur existe déjà.")
                await ws.close()
                return ws

            admin_ws = next((c for c, u in clients.items() if u == admin_username), None)

            if admin_ws:
                print(f"Demande de création reçue pour: {new_user}")
                await admin_ws.send_str(f"[REQUEST] {new_user}")
                
                admin_waiting[admin_ws] = asyncio.Event()
                decision = await admin_queues[admin_ws].get()
                admin_waiting[admin_ws] = None
                
                print(f"Admin a répondu: {decision} pour {new_user}")

                if decision == "y":
                    await create_user(new_user, new_pass)
                    clients[ws] = new_user
                    await ws.send_str("OK_NEWUSER")
                    print(f"✓ Utilisateur {new_user} créé et connecté")
                else:
                    await ws.send_str("REFUSE_CREATION")
                    print(f"✗ Création refusée pour {new_user}")
                    await ws.close()
                    return ws
            else:
                print(f"Aucun admin connecté. {new_user} mis en attente.")
                pending_requests.append((ws, new_user, new_pass))
                await ws.send_str("OK_WAITING_ADMIN")

        # LOGIN
        elif msg.startswith("[LOGIN] "):
            _, user, upass = msg.split(" ", 2)

            user_data = await get_user(user)
            is_valid = (user == admin_username) or (user_data and user_data["password"] == upass)

            if is_valid:
                clients[ws] = user
                await ws.send_str("OK_LOGIN")
                print(f"✓ {user} connecté")

                if user == admin_username:
                    admin_queues[ws] = asyncio.Queue()
                    print("🔑 Admin Purple_key connecté")

                    if pending_requests:
                        print(f"{len(pending_requests)} demande(s) en attente")
                    
                    for req_ws, u, p in pending_requests.copy():
                        if req_ws.closed:
                            pending_requests.remove((req_ws, u, p))
                            print(f"Client {u} déconnecté, demande ignorée")
                            continue
                        
                        await ws.send_str(f"[REQUEST] {u}")
                        admin_waiting[ws] = asyncio.Event()
                        
                        decision = await admin_queues[ws].get()
                        admin_waiting[ws] = None

                        if decision == "y":
                            await create_user(u, p)
                            await req_ws.send_str("OK_NEWUSER")
                            clients[req_ws] = u
                            print(f"✓ Utilisateur {u} créé (demande en attente)")
                        else:
                            await req_ws.send_str("REFUSE_CREATION")
                            await req_ws.close()
                            print(f"✗ Création refusée pour {u} (demande en attente)")

                        pending_requests.remove((req_ws, u, p))
            else:
                await ws.send_str("ERREUR: ID ou mot de passe incorrect.")
                await ws.close()
                return ws
        else:
            await ws.send_str("ERREUR: Format invalide.")
            await ws.close()
            return ws

        # BOUCLE PRINCIPALE
        async for message in ws:
            if message.type != web.WSMsgType.TEXT:
                continue

            txt = message.data.strip()
            username = clients.get(ws, "???")

            if ws in admin_waiting and admin_waiting[ws] is not None:
                response = txt.lower().strip()
                if response in ["y", "n"]:
                    await admin_queues[ws].put(response)
                    continue
                else:
                    await ws.send_str("[SYSTEM] Répondez par 'y' (oui) ou 'n' (non)")
                    continue

            print(f"{username}: {txt}")

            for cli in clients:
                if cli != ws and not cli.closed:
                    await cli.send_str(f"[{username}] {txt}")

    except Exception as e:
        print(f"Erreur dans ws_handler: {e}")
    finally:
        username = clients.get(ws, "inconnu")
        if ws in clients:
            print(f"{username} déconnecté.")
            del clients[ws]
        if ws in admin_queues:
            del admin_queues[ws]
        if ws in admin_waiting:
            del admin_waiting[ws]
        
        pending_requests[:] = [(w, u, p) for w, u, p in pending_requests if w != ws]

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
    print(f"🟣 Serveur Purple-msg lancé sur port {PORT}")
    web.run_app(create_app(), host="0.0.0.0", port=PORT)