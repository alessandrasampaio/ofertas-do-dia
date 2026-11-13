import os
import json
import requests # Para o WhatsApp (Green API)
from curl_cffi import requests as curl_requests # A arma secreta contra o bloqueio
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# --- Configurações ---
GREEN_API_INSTANCE_ID = os.environ.get("GREEN_API_INSTANCE_ID")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN")
WHATSAPP_PHONE = os.environ.get("WHATSAPP_PHONE")
MERCADO_LIVRE_AFFILIATE_ID = os.environ.get("MERCADO_LIVRE_AFFILIATE_ID")

def adicionar_id_afiliado(url_produto):
    if not MERCADO_LIVRE_AFFILIATE_ID or not url_produto:
        return url_produto
    try:
        parsed_url = urlparse(url_produto)
        query_params = parse_qs(parsed_url.query)
        query_params['matt_tool'] = [MERCADO_LIVRE_AFFILIATE_ID]
        new_query = urlencode(query_params, doseq=True)
        return urlunparse(parsed_url._replace(query=new_query))
    except:
        return url_produto

def buscar_mercadolivre():
    ofertas = []
    print("Acessando o Mercado Livre com disfarce Chrome (curl_cffi)...")
    
    url = "https://www.mercadolivre.com.br/ofertas"
    
    try:
        # AQUI ESTÁ A MÁGICA: impersonate="chrome110" engana o Cloudflare
        response = curl_requests.get(url, impersonate="chrome110", timeout=20)
        
        print(f"Status da resposta: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Busca os cards de produto
            cards = soup.select(".poly-card, .promotion-item")
            print(f"Encontrados {len(cards)} cards na página.")
            
            for card in cards[:15]:
                try:
                    titulo_elem = card.select_one(".poly-component__title, .promotion-item__title")
                    preco_elem = card.select_one(".andes-money-amount__fraction")
                    link_elem = card.select_one("a")
                    
                    if titulo_elem and preco_elem and link_elem:
                        titulo = titulo_elem.get_text(strip=True)
                        preco_texto = preco_elem.get_text(strip=True).replace(".", "")
                        link = link_elem.get("href", "")
                        
                        img_elem = card.select_one("img")
                        img = ""
                        if img_elem:
                            img = img_elem.get("data-src") or img_elem.get("src") or ""
                            
                        link_com_afiliado = adicionar_id_afiliado(link)
                        
                        ofertas.append({
                            "plataforma": "Mercado Livre",
                            "titulo": titulo,
                            "preco": float(preco_texto),
                            "link": link_com_afiliado,
                            "imagem": img
                        })
                except Exception:
                    continue
        else:
            print("Bloqueado mesmo com curl_cffi.")
            
    except Exception as e:
        print(f"Erro na requisição: {e}")
        
    return ofertas

def enviar_whatsapp(ofertas):
    if not GREEN_API_INSTANCE_ID or not GREEN_API_TOKEN or not WHATSAPP_PHONE:
        print("GREEN-API não configurada.")
        return
    
    if not ofertas:
        mensagem = "⚠️ O Mercado Livre bloqueou o acesso hoje. (Status diferente de 200)."
    else:
        top_ofertas = sorted(ofertas, key=lambda x: x["preco"])[:5]
        mensagem = "🛒 *Melhores Ofertas do Mercado Livre*\n\n"
        for of in top_ofertas:
            mensagem += f"*{of['titulo'][:50]}...*\n"
            mensagem += f"💰 R$ {of['preco']:.2f}\n"
            mensagem += f"🔗 {of['link']}\n\n"
    
    url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    chat_id = f"{WHATSAPP_PHONE}@c.us"
    payload = {"chatId": chat_id, "message": mensagem}
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("WhatsApp enviado!")
    except Exception as e:
        print(f"Erro WhatsApp: {e}")

if __name__ == "__main__":
    print("Iniciando coleta...")
    todas_ofertas = buscar_mercadolivre()
    
    if not todas_ofertas:
        todas_ofertas = [{
            "plataforma": "Aviso",
            "titulo": "O Mercado Livre bloqueou o acesso hoje.",
            "preco": 0.0,
            "link": "#",
            "imagem": ""
        }]
    
    with open("ofertas.json", "w", encoding="utf-8") as f:
        json.dump(todas_ofertas, f, ensure_ascii=False, indent=2)
    
    enviar_whatsapp(todas_ofertas)
    print(f"Coleta finalizada. {len(todas_ofertas)} itens.")
