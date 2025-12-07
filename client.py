import asyncio
import websockets
import getpass

SERVER = "wss://purple-msg.onrender.com/ws"

async def main():
    print("Connexion au serveur...\n")
    server_pass = getpass.getpass("Mot de passe serveur : ")

    async with websockets.connect(SERVER) as ws:
        await ws.send(f"[AUTH] {server_pass}")
        resp = await ws.recv()
        if resp != "OK_SERVEUR":
            print("ÉCHEC :", resp)
            return

        user = input("ID : ")
        upass = getpass.getpass("Mot de passe : ")

        await ws.send(f"[LOGIN] {user} {upass}")
        resp = await ws.recv()

        if resp == "OK_LOGIN":
            print(f"Connecté en tant que {user}")
        elif resp == "OK_NEWUSER":
            print(f"Compte {user} créé et validé automatiquement")
        elif resp == "REFUSE_CREATION":
            print("Le serveur a refusé la création du compte.")
            return
        else:
            print("ÉCHEC :", resp)
            return

        async def recv():
            while True:
                print(await ws.recv())

        async def send():
            while True:
                msg = await asyncio.to_thread(input)
                await ws.send(msg)

        await asyncio.gather(recv(), send())

asyncio.run(main())
