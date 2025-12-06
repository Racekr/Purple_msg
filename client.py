import asyncio
import websockets
import getpass

SERVER = "ws://192.168.1.69:8765"

async def main():
    print("Connexion au serveur...\n")

    server_pass = getpass.getpass("Mot de passe serveur : ")

    async with websockets.connect(SERVER) as ws:
        # Auth serveur
        await ws.send(f"[AUTH] {server_pass}")
        resp = await ws.recv()
        if resp != "OK_SERVEUR":
            print("ÉCHEC :", resp)
            return

        # Choix mode
        user = input("ID (ou tape 'login' pour créer un compte) : ")

        if user.lower() == "login":
            new_user = input("Nouvel ID : ")
            new_pass = getpass.getpass("Nouveau mot de passe : ")

            # Envoi création
            await ws.send(f"[NEWUSER] {new_user} {new_pass}")
            resp = await ws.recv()

            if resp == "OK_NEWUSER":
                print("✓ Compte créé, connexion automatique...\n")
                # Auto-login
                user = new_user
                upass = new_pass
            elif resp == "REFUSE_CREATION":
                print("Le serveur a refusé la création du compte.")
                return
            else:
                print("ÉCHEC :", resp)
                return

        else:
            upass = getpass.getpass("Mot de passe utilisateur : ")

        # Login
        await ws.send(f"[LOGIN] {user} {upass}")
        resp = await ws.recv()

        if resp != "OK_LOGIN":
            print("ÉCHEC :", resp)
            return

        print(f"✓ Connecté en tant que {user}. Tape tes messages.\n")

        async def recv():
            while True:
                print(await ws.recv())

        async def send():
            while True:
                msg = await asyncio.to_thread(input)
                await ws.send(msg)

        await asyncio.gather(recv(), send())

asyncio.run(main())
