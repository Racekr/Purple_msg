import asyncio
import websockets
import json
import os

SERVER_PASSWORD = "1234"
USER_DB_FILE = "users.json"
PORT = int(os.getenv("PORT", 8765))

clients = {}  # ws -> username
pending_requests = []  # liste des tuples (ws_client, new_user, new_pass)
admin_username = "Purple_key"  # admin qui valide les créations

try:
    with open(USER_DB_FILE, "r") as f:
        USER_DB = json.load(f)
except FileNotFoundError:
    USER_DB = {}

def save_users():
    with open(USER_DB_FILE, "w") as f:
        json.dump(USER_DB, f)

async def handler(ws):
    try:
        print("Nouvelle connexion.")
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

        # Auth utilisateur ou création
        login_msg = await ws.recv()
        if not login_msg.startswith("[LOGIN] "):
            await ws.send("ERREUR: Format login invalide.")
            await ws.close()
            return

        _, user, upass = login_msg.split(" ", 2)

        # Admin connecté ?
        if user == admin_username:
            clients[ws] = user
            await ws.send("OK_LOGIN")
            print(f"Admin {user} connecté.")
            # notifier les demandes en attente
            for req_ws, new_user, new_pass in pending_requests.copy():
                await ws.send(f"[REQUEST] {new_user}")
                decision = await ws.recv()  # attend "y" ou "n"
                if decision.lower() == "y":
                    USER_DB[new_user] = new_pass
                    save_users()
                    await req_ws.send("OK_NEWUSER")
                else:
                    await req_ws.send("REFUSE_CREATION")
                pending_requests.remove((req_ws, new_user, new_pass))

        # Utilisateur existant ?
        elif user in USER_DB and USER_DB[user] == upass:
            clients[ws] = user
            await ws.send("OK_LOGIN")
            print(f"Utilisateur {user} connecté.")

        # Sinon, nouvelle création
        else:
            admin_ws = next((c for c, u in clients.items() if u == admin_username), None)
            pending_requests.append((ws, user, upass))
            print(f"Nouvelle demande de création stockée : {user}")
            if admin_ws:
                await admin_ws.send(f"[REQUEST] {user}")
                decision = await admin_ws.recv()
                if decision.lower() == "y":
                    USER_DB[user] = upass
                    save_users()
                    await ws.send("OK_NEWUSER")
                    print(f"Admin a validé {user}")
                else:
                    await ws.send("REFUSE_CREATION")
                    print(f"Admin a refusé {user}")

        # Boucle chat
        async for msg in ws:
            for client in list(clients.keys()):
                if client != ws:
                    await client.send(f"[{clients[ws]}] {msg}")

    except Exception as e:
        print("Erreur serveur :", e)
    finally:
        if ws in clients:
            print(f"{clients[ws]} s'est déconnecté.")
            del clients[ws]

async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"Serveur lancé sur PORT {PORT}")
        await asyncio.Future()

asyncio.run(main())
