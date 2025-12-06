import asyncio
import websockets
import getpass

SERVER = "ws://192.168.1.69:8765"

async def main():
    print("Connexion au serveur...\n")

    server_pass = getpass.getpass("Mot de passe serveur : ")

    async with websockets.connect(SERVER) as ws:
        await ws.send(f"[AUTH] {server_pass}")
        resp = await ws.recv()
        if resp != "OK_SERVEUR":
            print("ÉCHEC :", resp)
            return

        # Choix login ou création compte
        user = input("ID (ou tape 'login' pour créer un compte) : ")

        if user.lower() == "login":
            new_user = input("Nouvel ID : ")
            new_pass = getpass.getpass("Nouveau mot de passe : ")
            await ws.send(f"[NEWUSER] {new_user} {new_pass}")
            resp = await ws.recv()
            if resp == "OK_NEWUSER":
                print("✓ Compte créé ! Connecte-toi maintenant.\n")
            else:
                print("ÉCHEC :", resp)
            return  # fin de session après création

        upass = getpass.getpass("Mot de passe utilisateur : ")
        await ws.send(f"[LOGIN] {user} {upass}")
        resp = await ws.recv()
        if resp != "OK_LOGIN":
            print("ÉCHEC :", resp)
            return

        print("✓ Connecté au canal. Tape tes messages.\n")

        async def recv():
            while True:
                print(await ws.recv())

        async def send():
            while True:
                msg = await asyncio.to_thread(input)
                await ws.send(msg)

        await asyncio.gather(recv(), send())

asyncio.run(main())
