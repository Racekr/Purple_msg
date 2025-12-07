import asyncio
import getpass
from aiohttp import ClientSession, ClientConnectorError, WSMsgType

SERVER = "https://purple-msg.onrender.com/ws"

async def main():
    print("Connexion au serveur...\n")
    server_pass = getpass.getpass("Mot de passe serveur : ")

    async with ClientSession() as session:
        try:
            async with session.ws_connect(SERVER) as ws:
                # Auth serveur
                await ws.send_str(f"[AUTH] {server_pass}")
                resp = await ws.receive_str()
                if resp != "OK_SERVEUR":
                    print("ÉCHEC :", resp)
                    return

                # Choix register/login
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

                # Réception réponse initiale
                resp = await ws.receive_str()
                if resp in ("OK_LOGIN", "OK_NEWUSER"):
                    print(f"✓ Connecté en tant que {user if mode=='login' else new_user}")
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

                # Boucle réception
                async def recv():
                    async for msg in ws:
                        if msg.type == WSMsgType.TEXT:
                            # Affiche simplement ce que le serveur envoie
                            print(msg.data)
                        elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                            break

                # Boucle envoi
                async def send():
                    while True:
                        msg = await asyncio.to_thread(input)
                        await ws.send_str(msg)

                await asyncio.gather(recv(), send())

        except ClientConnectorError:
            print("Impossible de se connecter au serveur. Vérifie l'adresse et ton internet.")

asyncio.run(main())
