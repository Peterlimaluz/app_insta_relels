import time
import requests
from typing import Optional

class MetaPublisher:
    def __init__(self, instagram_account_id: str, access_token: str, facebook_page_id: Optional[str] = None):
        self.ig_id = instagram_account_id
        self.fb_page_id = facebook_page_id
        self.token = access_token
        self.base_url = "https://graph.facebook.com/v18.0"

    def publicar_reels_instagram(self, video_url: str, caption: str) -> str:
        """Publica o Reels na conta do Instagram."""
        create_url = f"{self.base_url}/{self.ig_id}/media"
        payload = {
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'access_token': self.token
        }
        res = requests.post(create_url, data=payload).json()
        if 'id' not in res:
            raise Exception(f"[Instagram] Erro ao criar container: {res}")

        container_id = res['id']
        status_url = f"{self.base_url}/{container_id}"
        params = {'fields': 'status_code', 'access_token': self.token}
        
        for _ in range(30):
            time.sleep(5)
            status_res = requests.get(status_url, params=params).json()
            status_code = status_res.get('status_code')
            
            if status_code == 'FINISHED':
                break
            elif status_code == 'ERROR':
                raise Exception("[Instagram] Falha no processamento do vídeo pela Meta.")

        publish_url = f"{self.base_url}/{self.ig_id}/media_publish"
        pub_payload = {
            'creation_id': container_id,
            'access_token': self.token
        }
        pub_res = requests.post(publish_url, data=pub_payload).json()
        
        if 'id' not in pub_res:
            raise Exception(f"[Instagram] Erro ao publicar mídia: {pub_res}")

        return pub_res['id']

    def publicar_facebook_pagina(self, video_url: str, caption: str) -> str | None:
        """Publica o vídeo/Reels na Página do Facebook."""
        if not self.fb_page_id:
            return None

        # Se o token já é da Página, 'me/videos' publica de forma direta e segura
        alvo = self.fb_page_id if self.fb_page_id != "122315092208059749" else "me"
        fb_url = f"{self.base_url}/{alvo}/videos"
        payload = {
            'file_url': video_url,
            'description': caption,
            'access_token': self.token
        }
        res = requests.post(fb_url, data=payload).json()
        if 'id' not in res:
            raise Exception(f"[Facebook] Erro ao publicar na Página: {res}")

        return res['id']

    def publicar_reels(self, video_url: str, caption: str) -> dict:
        """Executa a publicação no Instagram e, se o FB_PAGE_ID estiver presente, também no Facebook."""
        resultados = {}

        # 1. Publica no Instagram
        ig_post_id = self.publicar_reels_instagram(video_url, caption)
        resultados['instagram'] = ig_post_id

        # 2. Publica no Facebook (opcional / se configurado)
        if self.fb_page_id:
            try:
                fb_post_id = self.publicar_facebook_pagina(video_url, caption)
                resultados['facebook'] = fb_post_id
            except Exception as e:
                print(f"⚠️ Alerta Facebook: Falha ao postar no Facebook, mas Instagram foi publicado com sucesso (IG ID: {ig_post_id}). Erro: {e}")
                resultados['facebook_error'] = str(e)

        return resultados