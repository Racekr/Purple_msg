# client.py
import asyncio
import getpass
from aiohttp import ClientSession, ClientConnectorError, WSMsgType

SERVER = "https://purple-msg.onrender.com/ws"
ADMIN_USERNAME = "Purple_key"

async def main():
    print("Connexion au serveur...\n")
    server_pass = getpass.getpass("Mot de passe serveur : ")

    async with ClientSession() as session:
        try:
            async with session.ws_connect(SERVER) as ws:
                # Auth serveur
                await ws.send_str(f"[AUTH] {server_pass}")

                # wait OK_SERVEUR robustly
                while True:
                    m = await ws.receive()
                    if m.type == WSMsgType.TEXT:
                        if m.data == "OK_SERVEUR":
                            break
                        else:
                            print("ÉCHEC :", m.data)
                            return
                    elif m.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                        print("Connexion fermée ou erreur.")
                        return

                # register or login
                mode = input("tapez register/login : ").strip().lower()
                if mode == "register":
                    new_user = input("Nouvel ID : ")
                    new_pass = getpass.getpass("Nouveau mot de passe : ")
                    await ws.send_str(f"[NEWUSER] {new_user} {new_pass}")
                elif mode == "login":
                    user = input("ID : ")
                    upass = getpass.getpass("Mot de passe : ")
                    await ws.send_str(f"[LOGIN] {user} {upass}")
                else:
                    print("Mode invalide.")
                    return

                # wait initial response
                m = await ws.receive()
                if m.type != WSMsgType.TEXT:
                    print("Erreur de communication")
                    return
                resp = m.data

                if resp in ("OK_LOGIN", "OK_NEWUSER"):
                    who = user if mode == "login" else new_user
                    print(f"✓ Connecté en tant que {who}")
                    if mode == "register":
                        user, upass = new_user, new_pass
                elif resp == "REFUSE_CREATION":
                    print("Le serveur a refusé la création du compte.")
                    return
                elif resp == "OK_WAITING_ADMIN":
                    print("Demande envoyée, en attente de validation admin...")
                    return
                else:
                    print("ÉCHEC :", resp)
                    return

                # loops
                async def recv():
                    async for msg in ws:
                        if msg.type == WSMsgType.TEXT:
                            # Print exactly what the server sent (including [REQUEST]...)
                            print(msg.data)
                        elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                            print("Connexion fermée ou erreur.")
                            break

                async def send():
                    while True:
                        s = await asyncio.to_thread(input)
                        # send whatever admin types; admin can type "y username" or "n username"
                        await ws.send_str(s)

                await asyncio.gather(recv(), send())

        except ClientConnectorError:
            print("Impossible de se connecter au serveur. Vérifie l'adresse et ton internet.")
        except Exception as e:
            print("Erreur client :", e)

asyncio.run(main())
