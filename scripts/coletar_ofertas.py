import os
import json
import requests
from playwright.sync_api import sync_playwright

# --- Configurações (vêm dos Secrets do GitHub) ---
GREEN_API_INSTANCE_ID = os.environ.get("GREEN_API_INSTANCE_ID")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN")
WHATSAPP_PHONE = os.environ.get("WHATSAPP_PHONE")

def buscar_mercadolivre():
    """Busca ofertas no Mercado Livre usando Playwright (navegador real)."""
    ofertas = []
    print("Iniciando navegador para buscar no Mercado Livre...")
    
    with sync_playwright() as p:
        # Abre o navegador Chromium em modo headless (invisível)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Vai para a página de ofertas do Mercado Livre
            page.goto("https://www.mercadolivre.com.br/ofertas", timeout=60000)
            
            # Espera os cards de produtos carregarem na tela
            page.wait_for_selector(".promotion-item", timeout=15000)
            
            # Pega todos os cards de promoção visíveis
            cards = page.query_selector_all(".promotion-item")
            
            for card in cards[:15]:  # Pega os 15 primeiros
                try:
                    titulo_elem = card.query_selector(".promotion-item__title")
                    preco_elem = card.query_selector(".andes-money-amount__fraction")
                    link_elem = card.query_selector("a")
                    img_elem = card.query_selector("img")
                    
                    if titulo_elem and preco_elem and link_elem:
                        titulo = titulo_elem.inner_text().strip()
                        preco_texto = preco_elem.inner_text().strip().replace(".", "")
                        link = link_elem.get_attribute("href")
                        
                        # Algumas imagens usam data-src ou src dependendo do carregamento
                        img = ""
                        if img_elem:
                            img = img_elem.get_attribute("src") or img_elem.get_attribute("data-src") or ""
                        
                        ofertas.append({
                            "plataforma": "Mercado Livre",
                            "titulo": titulo,
                            "preco": float(preco_texto),
                            "link": link,
                            "imagem": img
                        })
                except Exception as e:
                    print(f"Erro ao ler um card específico: {e}")
                    continue
                    
        except Exception as e:
            print(f"Erro ao acessar o Mercado Livre: {e}")
        finally:
            browser.close()
            
    print(f"Encontradas {len(ofertas)} ofertas no Mercado Livre.")
    return ofertas

def enviar_whatsapp(ofertas):
    """Envia um resumo das ofertas para o WhatsApp via GREEN-API."""
    if not GREEN_API_INSTANCE_ID or not GREEN_API_TOKEN or not WHATSAPP_PHONE:
        print("GREEN-API não configurada. Pulando envio.")
        return
    
    if not ofertas:
        print("Nenhuma oferta para enviar hoje.")
        return

    top_ofertas = sorted(ofertas, key=lambda x: x["preco"])[:5]
    
    mensagem = "🛒 *Melhores Ofertas do Mercado Livre*\n\n"
    for of in top_ofertas:
        mensagem += f"*{of['titulo'][:60]}...*\n"
        mensagem += f"💰 R$ {of['preco']:.2f}\n"
        mensagem += f"🔗 {of['link']}\n\n"
    
    url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    chat_id = f"{WHATSAPP_PHONE}@c.us"
    payload = {"chatId": chat_id, "message": mensagem}
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("WhatsApp enviado com sucesso!")
        else:
            print(f"Erro GREEN-API: {r.text}")
    except Exception as e:
        print(f"Erro de conexão GREEN-API: {e}")

if __name__ == "__main__":
    print("Iniciando coleta de ofertas...")
    
    todas_ofertas = buscar_mercadolivre()
    
    if not todas_ofertas:
        print("Nenhuma oferta encontrada hoje.")
        # Fallback para o site não quebrar
        todas_ofertas = [{
            "plataforma": "Aviso",
            "titulo": "Nenhuma oferta encontrada hoje. Aguarde a próxima execução.",
            "preco": 0.0,
            "link": "#",
            "imagem": ""
        }]
    
    with open("ofertas.json", "w", encoding="utf-8") as f:
        json.dump(todas_ofertas, f, ensure_ascii=False, indent=2)
    
    enviar_whatsapp(todas_ofertas)
    print(f"Coleta finalizada. {len(todas_ofertas)} ofertas salvas.")
