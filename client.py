# client.py
import asyncio
import getpass
from aiohttp import ClientSession, ClientConnectorError, WSMsgType

SERVER = "https://purple-msg.onrender.com/ws"
ADMIN_USERNAME = "Purple_key"

async def main():
    print("🟣 Connexion au serveur Purple-msg...\n")
    server_pass = getpass.getpass("Mot de passe serveur : ")

    async with ClientSession() as session:
        try:
            async with session.ws_connect(SERVER) as ws:
                # Auth serveur
                await ws.send_str(f"[AUTH] {server_pass}")

                # Attendre OK_SERVEUR
                while True:
                    m = await ws.receive()
                    if m.type == WSMsgType.TEXT:
                        if m.data == "OK_SERVEUR":
                            break
                        else:
                            print("❌ ÉCHEC :", m.data)
                            return
                    elif m.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                        print("❌ Connexion fermée ou erreur.")
                        return

                # Register ou login
                mode = input("Tapez 'register' ou 'login' : ").strip().lower()
                
                if mode == "register":
                    new_user = input("Nouvel ID : ")
                    new_pass = getpass.getpass("Nouveau mot de passe : ")
                    await ws.send_str(f"[NEWUSER] {new_user} {new_pass}")
                    user = new_user  # pour référence
                    
                elif mode == "login":
                    user = input("ID : ")
                    upass = getpass.getpass("Mot de passe : ")
                    await ws.send_str(f"[LOGIN] {user} {upass}")
                    
                else:
                    print("❌ Mode invalide. Utilisez 'register' ou 'login'.")
                    return

                # Attendre la réponse initiale
                m = await ws.receive()
                if m.type != WSMsgType.TEXT:
                    print("❌ Erreur de communication")
                    return
                resp = m.data

                # Gérer les différentes réponses
                if resp == "OK_LOGIN":
                    print(f"✓ Connecté en tant que {user}\n")
                    
                elif resp == "OK_NEWUSER":
                    print(f"✓ Compte créé ! Connecté en tant que {user}\n")
                    
                elif resp == "OK_WAITING_ADMIN":
                    print("⏳ Demande envoyée, en attente de validation admin...")
                    print("   (Restez connecté, la réponse arrivera dès qu'un admin se connectera)\n")
                    
                    # ATTENDRE la réponse de l'admin
                    while True:
                        m = await ws.receive()
                        if m.type != WSMsgType.TEXT:
                            print("❌ Connexion perdue")
                            return
                        
                        if m.data == "OK_NEWUSER":
                            print(f"\n✓ Compte validé par l'admin ! Vous êtes connecté en tant que {user}\n")
                            break
                        elif m.data == "REFUSE_CREATION":
                            print("\n❌ L'admin a refusé la création de votre compte.")
                            return
                        else:
                            # Autres messages pendant l'attente
                            print(m.data)
                    
                elif resp.startswith("ERREUR"):
                    print(f"❌ {resp}")
                    return
                    
                else:
                    print(f"❌ Réponse inattendue : {resp}")
                    return

                # Si on arrive ici, on est connecté avec succès
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print("🟣 PURPLE-MSG CHAT")
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
                
                if user == ADMIN_USERNAME:
                    print("🔑 MODE ADMIN ACTIVÉ")
                    print("   Pour valider une demande : tapez 'y'")
                    print("   Pour refuser une demande : tapez 'n'\n")

                # Boucles de réception et envoi
                async def recv():
                    async for msg in ws:
                        if msg.type == WSMsgType.TEXT:
                            data = msg.data
                            
                            # Affichage spécial pour l'admin
                            if data.startswith("[REQUEST] "):
                                username_req = data.replace("[REQUEST] ", "").strip()
                                print(f"\n🔔 DEMANDE DE CRÉATION : {username_req}")
                                print("   Accepter ? (y/n) : ", end="", flush=True)
                            else:
                                print(data)
                                
                        elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                            print("\n❌ Connexion fermée ou erreur.")
                            break

                async def send():
                    while True:
                        try:
                            s = await asyncio.to_thread(input)
                            if s.strip():  # Envoyer seulement si non vide
                                await ws.send_str(s)
                        except EOFError:
                            break

                await asyncio.gather(recv(), send())

        except ClientConnectorError:
            print("❌ Impossible de se connecter au serveur.")
            print("   Vérifiez votre connexion internet et l'adresse du serveur.")
        except Exception as e:
            print(f"❌ Erreur client : {e}")

if __name__ == "__main__":
    asyncio.run(main())