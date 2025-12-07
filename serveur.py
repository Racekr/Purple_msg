import asyncio
import websockets
import json
import os
from aiohttp import web

SERVER_PASSWORD = "1234"
USER_DB_FILE = "users.json"

# Render impose un port dynamique
PORT = int(os.getenv("PORT", 8765))

clients = {}

# Charger la base utilisateur
try:
    with open(USER_DB_FILE, "r") as f:
        USER_DB = json.load(f)
except FileNotFoundError:
    USER_DB = {}

def save_users():
    with open(USER_DB_FILE, "w") as f:
        json.dump(USER_DB, f)

# --- WebSocket handler ---
async def handler(ws):
    try:
        print("Nouvelle connexion.")

        # Auth serveur
        auth_msg = await ws.recv()
        if not auth_msg.startswith("[AUTH] "):
            await ws.send("ERREUR: Authentification serveur manquante.")
            await ws.close()
            return

        pwd = auth_msg.split(" ", 1)[1].strip()
        if pwd != SERVER_PASSWORD:
            await ws.send("ERREUR: Mauvais mot de passe serveur.")
            await ws.close()
            return

        await ws.send("OK_SERVEUR")
        print("Client accepté pour la suite.")

        # Auth utilisateur
        login_msg = await ws.recv()

        # Création de compte automatique si nécessaire
        if login_msg.startswith("[NEWUSER] "):
            _, new_user, new_pass = login_msg.split(" ", 2)

            if new_user in USER_DB:
                await ws.send("ERREUR: User existe déjà")
            else:
                USER_DB[new_user] = new_pass
                save_users()
                await ws.send("OK_NEWUSER")
                print(f"Nouvel utilisateur créé : {new_user}")

            # Le client envoie ensuite le login
            login_msg = await ws.recv()

        # Connexion utilisateur
        if not login_msg.startswith("[LOGIN] "):
            await ws.send("ERREUR: Format login invalide.")
            await ws.close()
            return

        _, user, upass = login_msg.split(" ", 2)

        if user not in USER_DB or USER_DB[user] != upass:
            await ws.send("ERREUR: ID ou mot de passe incorrect.")
            await ws.close()
            return

        await ws.send("OK_LOGIN")
        clients[ws] = user
        print(f"Utilisateur {user} connecté.")

        # Boucle chat
        async for msg in ws:
            print(f"{user} : {msg}")
            for client in list(clients.keys()):
                if client != ws:
                    await client.send(f"[{user}] {msg}")

    except Exception as e:
        print("Erreur serveur :", e)

    finally:
        if ws in clients:
            print(f"{clients[ws]} s'est déconnecté.")
            del clients[ws]

# --- HTTP server pour Render ---
async def http_root(request):
    return web.Response(text="Serveur WebSocket actif !")

async def start_http_server():
    app = web.Application()
    app.router.add_get("/", http_root)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"HTTP server prêt sur port {PORT}")

# --- Main ---
async def main():
    print(f"Démarrage du serveur WebSocket sur port {PORT}")
    await start_http_server()  # Démarrage HTTP
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()  # run forever

asyncio.run(main())
