import os
import json
import requests
import feedparser
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup

# --- Configurações ---
GREEN_API_INSTANCE_ID = os.environ.get("GREEN_API_INSTANCE_ID")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN")
WHATSAPP_PHONE = os.environ.get("WHATSAPP_PHONE")
MERCADO_LIVRE_AFFILIATE_ID = os.environ.get("MERCADO_LIVRE_AFFILIATE_ID")

def adicionar_id_afiliado(url_produto):
    """Adiciona o seu ID de afiliado (matt_tool) no link."""
    if not MERCADO_LIVRE_AFFILIATE_ID or "mercadolivre" not in url_produto:
        return url_produto
    
    # Limpa a URL para evitar links duplicados quebrados
    parsed_url = urlparse(url_produto)
    query_params = parse_qs(parsed_url.query)
    query_params['matt_tool'] = [MERCADO_LIVRE_AFFILIATE_ID]
    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed_url._replace(query=new_query))

def buscar_ofertas_promobit():
    ofertas = []
    print("Buscando ofertas no agregador Promobit (RSS)...")
    
    # Lendo o Feed RSS do Promobit
    url_rss = "https://www.promobit.com.br/rss/"
    feed = feedparser.parse(url_rss)
    
    print(f"Encontradas {len(feed.entries)} ofertas no feed.")
    
    for entry in feed.entries:
        titulo = entry.title
        descricao = entry.description
        
        # Tenta achar um link do Mercado Livre dentro da descrição da oferta
        ml_link = None
        soup = BeautifulSoup(descricao, "html.parser")
        links = soup.find_all("a", href=True)
        
        for a in links:
            href = a['href']
            if "mercadolivre.com.br" in href or "mercadolivre.com" in href:
                ml_link = href
                break
                
        # Se a oferta tiver um link do Mercado Livre, nós a processamos
        if ml_link:
            # Tenta extrair o preço do título (ex: R$ 1.999,00)
            preco = 0.0
            match_preco = re.search(r'R\$\s*([\d\.]+,\d{2})', titulo)
            if match_preco:
                preco_str = match_preco.group(1).replace('.', '').replace(',', '.')
                try:
                    preco = float(preco_str)
                except:
                    pass
            
            link_com_afiliado = adicionar_id_afiliado(ml_link)
            
            # Tenta pegar a imagem se existir no feed
            imagem = ""
            if 'media_content' in entry:
                imagem = entry.media_content[0]['url']
            elif 'links' in entry:
                for link in entry.links:
                    if link.get('type', '').startswith('image'):
                        imagem = link.get('href')
                        break

            ofertas.append({
                "plataforma": "Mercado Livre",
                "titulo": titulo,
                "preco": preco,
                "link": link_com_afiliado,
                "imagem": imagem
            })
            
            # Se já achamos 15 ofertas boas, paramos para não sobrecarregar
            if len(ofertas) >= 15:
                break

    return ofertas

def enviar_whatsapp(ofertas):
    if not GREEN_API_INSTANCE_ID or not GREEN_API_TOKEN or not WHATSAPP_PHONE:
        print("GREEN-API não configurada.")
        return
    
    if not ofertas:
        mensagem = "⚠️ Não encontramos ofertas do Mercado Livre no agregador hoje."
    else:
        # Ordena pelo preço (se tiver) ou pega as primeiras
        top_ofertas = ofertas[:5]
        mensagem = "🛒 *Melhores Ofertas do Mercado Livre (via Promobit)*\n\n"
        for of in top_ofertas:
            mensagem += f"*{of['titulo'][:60]}...*\n"
            if of['preco'] > 0:
                mensagem += f"💰 R$ {of['preco']:.2f}\n"
            mensagem += f"🔗 {of['link']}\n\n"
    
    url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    chat_id = f"{WHATSAPP_PHONE}@c.us"
    payload = {"chatId": chat_id, "message": mensagem}
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("WhatsApp enviado com sucesso!")
    except Exception as e:
        print(f"Erro de conexão WhatsApp: {e}")

if __name__ == "__main__":
    print("Iniciando coleta via Promobit...")
    todas_ofertas = buscar_ofertas_promobit()
    
    if not todas_ofertas:
        todas_ofertas = [{
            "plataforma": "Aviso",
            "titulo": "Nenhuma oferta do Mercado Livre encontrada no Promobit hoje.",
            "preco": 0.0,
            "link": "#",
            "imagem": ""
        }]
    
    with open("ofertas.json", "w", encoding="utf-8") as f:
        json.dump(todas_ofertas, f, ensure_ascii=False, indent=2)
    
    enviar_whatsapp(todas_ofertas)
    print(f"Coleta finalizada. {len(todas_ofertas)} ofertas salvas.")
