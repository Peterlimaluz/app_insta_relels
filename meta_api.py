import time
import requests

class MetaPublisher:
    def __init__(self, instagram_account_id: str, access_token: str):
        self.ig_id = instagram_account_id
        self.token = access_token
        self.base_url = "https://graph.facebook.com/v18.0"

    def publicar_reels(self, video_url: str, caption: str) -> dict:
        """Inicia o upload do Reels via URL pública e aguarda a publicação."""
        # Step 1: Criar Container de Mídia
        create_url = f"{self.base_url}/{self.ig_id}/media"
        payload = {
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'access_token': self.token
        }
        res = requests.post(create_url, data=payload).json()
        if 'id' not in res:
            raise Exception(f"Erro ao criar container: {res}")

        container_id = res['id']

        # Step 2: Aguardar o processamento do vídeo no Instagram
        status_url = f"{self.base_url}/{container_id}"
        params = {'fields': 'status_code', 'access_token': self.token}
        
        for _ in range(30):  # Timeout de ~2.5 minutos
            time.sleep(5)
            status_res = requests.get(status_url, params=params).json()
            status_code = status_res.get('status_code')
            
            if status_code == 'FINISHED':
                break
            elif status_code == 'ERROR':
                raise Exception("Falha no processamento do vídeo pela Meta.")

        # Step 3: Publicar Mídia
        publish_url = f"{self.base_url}/{self.ig_id}/media_publish"
        pub_payload = {
            'creation_id': container_id,
            'access_token': self.token
        }
        pub_res = requests.post(publish_url, data=pub_payload).json()
        
        if 'id' not in pub_res:
            raise Exception(f"Erro ao publicar mídias: {pub_res}")

        return pub_res
