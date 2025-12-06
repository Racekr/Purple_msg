import asyncio
import websockets
import getpass

SERVER = "ws://192.168.1.69:8765"

async def main():
    print("Connexion au serveur...\n")

    # Demande mot de passe serveur obligatoire
    while True:
        server_pass = getpass.getpass("Mot de passe serveur : ").strip()
        if server_pass:
            break
        print("⚠ Le mot de passe serveur ne peut pas être vide.")

    async with websockets.connect(SERVER) as ws:
        # Envoi authentification serveur
        await ws.send(f"[AUTH] {server_pass}")
        resp = await ws.recv()
        if resp != "OK_SERVEUR":
            print("ÉCHEC :", resp)
            return

        print("✓ Mot de passe serveur accepté.\n")

        # Choix login / création compte
        while True:
            user = input("ID (ou tape 'login' pour créer un compte) : ").strip()
            if user:
                break
            print("⚠ L'ID ne peut pas être vide.")

        # Création d’un compte
        if user.lower() == "login":
            while True:
                new_user = input("Nouvel ID : ").strip()
                if new_user:
                    break
                print("⚠ L'ID ne peut pas être vide.")

            while True:
                new_pass = getpass.getpass("Nouveau mot de passe : ").strip()
                if new_pass:
                    break
                print("⚠ Le mot de passe ne peut pas être vide.")

            await ws.send(f"[NEWUSER] {new_user} {new_pass}")
            resp = await ws.recv()
            if resp == "OK_NEWUSER":
                print("✓ Compte créé ! Connecte-toi maintenant.\n")
            else:
                print("ÉCHEC :", resp)
            return

        # Login normal
        while True:
            upass = getpass.getpass("Mot de passe utilisateur : ").strip()
            if upass:
                break
            print("⚠ Le mot de passe ne peut pas être vide.")

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
                if msg.strip():     # ignore les messages vides
                    await ws.send(msg)

        await asyncio.gather(recv(), send())

asyncio.run(main())

