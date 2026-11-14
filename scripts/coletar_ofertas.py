import os
import json
import requests
import re
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

def buscar_ofertas_telegram():
    ofertas = []
    print("Buscando ofertas no canal do Telegram (Promobit)...")
    
    # Acessando a versão web do canal oficial do Promobit no Telegram
    url = "https://t.me/s/promobit"
    
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Pega todas as mensagens do canal
        mensagens = soup.select(".tgme_widget_message")
        print(f"Encontradas {len(mensagens)} mensagens recentes no canal.")
        
        for msg in mensagens:
            texto_elem = msg.select_one(".tgme_widget_message_text")
            if not texto_elem:
                continue
                
            texto = texto_elem.get_text(separator="\n").strip()
            
            # Procura links do Mercado Livre dentro da mensagem
            links = texto_elem.find_all("a", href=True)
            ml_link = None
            for a in links:
                href = a['href']
                if "mercadolivre.com.br" in href or "mercadolivre.com" in href:
                    ml_link = href
                    break
                    
            if ml_link:
                # Tenta achar o preço no texto
                preco = 0.0
                match_preco = re.search(r'R\$\s*([\d\.]+,\d{2})', texto)
                if match_preco:
                    preco_str = match_preco.group(1).replace('.', '').replace(',', '.')
                    try:
                        preco = float(preco_str)
                    except:
                        pass
                
                # Pega as primeiras 3 linhas do texto para ser o "título"
                titulo = " ".join(texto.split('\n')[:3])
                if len(titulo) > 80: 
                    titulo = titulo[:77] + "..."
                    
                link_com_afiliado = adicionar_id_afiliado(ml_link)
                
                # Tenta pegar a imagem se houver
                img_elem = msg.select_one(".tgme_widget_message_photo_wrap")
                img_url = ""
                if img_elem:
                    style = img_elem.get("style", "")
                    match_img = re.search(r'url\([\'"]?(.*?)[\'"]?\)', style)
                    if match_img:
                        img_url = match_img.group(1)

                ofertas.append({
                    "plataforma": "Mercado Livre (Telegram)",
                    "titulo": titulo,
                    "preco": preco,
                    "link": link_com_afiliado,
                    "imagem": img_url
                })
                
                # Se acharmos 10 ofertas, já é o suficiente
                if len(ofertas) >= 10:
                    break
                    
    except Exception as e:
        print(f"Erro ao acessar o Telegram: {e}")
        
    return ofertas

def enviar_whatsapp(ofertas):
    if not GREEN_API_INSTANCE_ID or not GREEN_API_TOKEN or not WHATSAPP_PHONE:
        print("GREEN-API não configurada.")
        return
    
    if not ofertas:
        mensagem = "⚠️ Não encontramos ofertas do Mercado Livre no canal hoje."
    else:
        # Pega as 5 mais recentes
        top_ofertas = ofertas[:5]
        mensagem = "🛒 *Melhores Ofertas do Mercado Livre*\n\n"
        for of in top_ofertas:
            mensagem += f"*{of['titulo']}*\n"
            if of['preco'] > 0:
                mensagem += f"💰 R$ {of['preco']:.2f}\n"
            mensagem += f"🔗 {of['link']}\n\n"
    
    url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    chat_id = f"{WHATSAPP_PHONE}@c.us"
    payload = {"chatId": chat_id, "message": mensagem}
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("WhatsApp enviado!")
        else:
            print(f"Erro na Green-API: {r.text}")
    except Exception as e:
        print(f"Erro WhatsApp: {e}")

if __name__ == "__main__":
    print("Iniciando coleta via Telegram...")
    todas_ofertas = buscar_ofertas_telegram()
    
    if not todas_ofertas:
        todas_ofertas = [{
            "plataforma": "Aviso",
            "titulo": "Nenhuma oferta encontrada no Telegram hoje.",
            "preco": 0.0,
            "link": "#",
            "imagem": ""
        }]
    
    with open("ofertas.json", "w", encoding="utf-8") as f:
        json.dump(todas_ofertas, f, ensure_ascii=False, indent=2)
    
    enviar_whatsapp(todas_ofertas)
    print(f"Coleta finalizada. {len(todas_ofertas)} itens.")
