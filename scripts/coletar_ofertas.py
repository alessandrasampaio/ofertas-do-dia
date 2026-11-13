import os
import json
import requests
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# --- Configurações ---
GREEN_API_INSTANCE_ID = os.environ.get("GREEN_API_INSTANCE_ID")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN")
WHATSAPP_PHONE = os.environ.get("WHATSAPP_PHONE")
MERCADO_LIVRE_AFFILIATE_ID = os.environ.get("MERCADO_LIVRE_AFFILIATE_ID")

def adicionar_id_afiliado(url_produto):
    if not MERCADO_LIVRE_AFFILIATE_ID:
        return url_produto
    parsed_url = urlparse(url_produto)
    query_params = parse_qs(parsed_url.query)
    query_params['matt_tool'] = [MERCADO_LIVRE_AFFILIATE_ID]
    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed_url._replace(query=new_query))

def buscar_mercadolivre():
    ofertas = []
    print("Buscando ofertas na API do Mercado Livre...")
    
    url = "https://api.mercadolibre.com/sites/MLB/search?q=promocao&limit=20"
    
    # DISFARCE: Fingindo ser o Chrome do Windows
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        print(f"Status da resposta do Mercado Livre: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            resultados = data.get("results", [])
            print(f"API retornou {len(resultados)} produtos com sucesso.")
            
            for item in resultados:
                titulo = item.get("title", "Produto sem título")
                preco = float(item.get("price", 0))
                link_original = item.get("permalink", "")
                imagem = item.get("thumbnail", "").replace("http://", "https://")
                
                if link_original and preco > 0:
                    link_com_afiliado = adicionar_id_afiliado(link_original)
                    ofertas.append({
                        "plataforma": "Mercado Livre",
                        "titulo": titulo,
                        "preco": preco,
                        "link": link_com_afiliado,
                        "imagem": imagem
                    })
        else:
            print(f"Bloqueio detectado! Resposta do site: {response.text[:200]}...")
            
    except Exception as e:
        print(f"Erro ao acessar a API: {e}")
        
    return ofertas

def enviar_whatsapp(ofertas):
    if not GREEN_API_INSTANCE_ID or not GREEN_API_TOKEN or not WHATSAPP_PHONE:
        print("GREEN-API não configurada.")
        return
    
    if not ofertas:
        mensagem = "⚠️ O Mercado Livre bloqueou o acesso do robô. Vou tentar outra estratégia na próxima."
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
        print(f"Erro de conexão WhatsApp: {e}")

if __name__ == "__main__":
    print("Iniciando coleta...")
    todas_ofertas = buscar_mercadolivre()
    
    if not todas_ofertas:
        todas_ofertas = [{
            "plataforma": "Aviso",
            "titulo": "O Mercado Livre bloqueou o acesso. Aguardando nova tentativa.",
            "preco": 0.0,
            "link": "#",
            "imagem": ""
        }]
    
    with open("ofertas.json", "w", encoding="utf-8") as f:
        json.dump(todas_ofertas, f, ensure_ascii=False, indent=2)
    
    enviar_whatsapp(todas_ofertas)
    print(f"Coleta finalizada. {len(todas_ofertas)} itens.")
