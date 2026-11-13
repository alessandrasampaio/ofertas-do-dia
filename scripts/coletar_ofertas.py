import os
import json
import requests
from bs4 import BeautifulSoup
from shopee_afflib import ShopeeAffiliate

# --- Configurações (vêm dos Secrets do GitHub) ---
SHOPEE_APP_ID = os.environ.get("SHOPEE_APP_ID")
SHOPEE_SECRET = os.environ.get("SHOPEE_SECRET")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def buscar_shopee():
    """Busca ofertas na API de afiliados da Shopee."""
    ofertas = []
    if not SHOPEE_APP_ID or not SHOPEE_SECRET:
        print("Chaves da Shopee não configuradas. Pulando coleta Shopee.")
        return ofertas
        
    try:
        client = ShopeeAffiliate(app_id=SHOPEE_APP_ID, secret=SHOPEE_SECRET)
        # Busca as 20 ofertas mais vendidas
        response = client.product_offer_v2(limit=20, sort_by="sales")
        
        for item in response.get("data", {}).get("item", []):
            info = item.get("item_basic", {})
            # A API da Shopee retorna preços em centavos (multiplicado por 100000)
            preco = info.get("price", 0) / 100000
            
            ofertas.append({
                "plataforma": "Shopee",
                "titulo": info.get("name", "Oferta Shopee"),
                "preco": preco,
                "link": info.get("offer_link", "#"),
                "imagem": f"https://cf.shopee.com.br/file/{info.get('image', '')}"
            })
    except Exception as e:
        print(f"Erro na Shopee: {e}")
    return ofertas

def buscar_mercadolivre():
    """Scraping simples para o Mercado Livre (pode falhar se o site mudar)."""
    ofertas = []
    try:
        url = "https://www.mercadolivre.com.br/ofertas"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Seleciona os cards de promoção na página do Mercado Livre
        cards = soup.select(".promotion-item")[:15] 
        
        for card in cards:
            titulo = card.select_one(".promotion-item__title")
            preco = card.select_one(".andes-money-amount__fraction")
            link = card.select_one("a")
            img = card.select_one("img")
            
            if titulo and preco and link:
                preco_texto = preco.get_text(strip=True).replace(".", "")
                ofertas.append({
                    "plataforma": "Mercado Livre",
                    "titulo": titulo.get_text(strip=True),
                    "preco": float(preco_texto),
                    "link": link.get("href", "#"),
                    "imagem": img.get("src") if img else ""
                })
    except Exception as e:
        print(f"Erro no Mercado Livre: {e}")
    return ofertas

def enviar_telegram(ofertas):
    """Envia um resumo das melhores ofertas para o Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram não configurado. Pulando envio.")
        return
    
    if not ofertas:
        print("Nenhuma oferta para enviar hoje.")
        return

    # Ordena do mais barato para o mais caro e pega as 5 primeiras
    top_ofertas = sorted(ofertas, key=lambda x: x["preco"])[:5]
    
    mensagem = "🛒 *Melhores Ofertas de Hoje*\n\n"
    for of in top_ofertas:
        mensagem += f"*{of['plataforma']}*: {of['titulo'][:50]}...\n"
        mensagem += f"💰 R$ {of['preco']:.2f}\n"
        mensagem += f"[Ver oferta]({of['link']})\n\n"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("Telegram enviado com sucesso!")
        else:
            print(f"Erro Telegram: {r.text}")
    except Exception as e:
        print(f"Erro de conexão Telegram: {e}")

if __name__ == "__main__":
    print("Iniciando coleta de ofertas...")
    
    ofertas_shopee = buscar_shopee()
    ofertas_ml = buscar_mercadolivre()
    
    todas_ofertas = ofertas_shopee + ofertas_ml
    
    # Se por algum motivo as APIs falharem e a lista ficar vazia, 
    # criamos uma oferta de teste para o site não quebrar.
    if not todas_ofertas:
        print("Nenhuma oferta encontrada hoje. Criando fallback de teste.")
        todas_ofertas = [{
            "plataforma": "Aviso",
            "titulo": "Nenhuma oferta encontrada hoje. Aguarde a próxima execução.",
            "preco": 0.0,
            "link": "#",
            "imagem": ""
        }]
    
    # Salva o JSON que o site vai ler
    with open("ofertas.json", "w", encoding="utf-8") as f:
        json.dump(todas_ofertas, f, ensure_ascii=False, indent=2)
    
    enviar_telegram(todas_ofertas)
    print(f"Coleta finalizada. {len(todas_ofertas)} ofertas salvas em ofertas.json.")
