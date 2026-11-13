import os
import json
import requests
from playwright.sync_api import sync_playwright

# --- Configurações (vêm dos Secrets do GitHub) ---
GREEN_API_INSTANCE_ID = os.environ.get("GREEN_API_INSTANCE_ID")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN")
WHATSAPP_PHONE = os.environ.get("WHATSAPP_PHONE")

def buscar_mercadolivre():
    """Busca ofertas no Mercado Livre usando Playwright (disfarçado de humano)."""
    ofertas = []
    print("Iniciando navegador para buscar no Mercado Livre...")
    
    with sync_playwright() as p:
        # Abre o navegador
        browser = p.chromium.launch(headless=True)
        
        # DISFARCE: Criamos um contexto fingindo ser um Google Chrome real no Windows
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        context = browser.new_context(user_agent=user_agent, viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            # Vai para a página de ofertas
            print("Acessando o site...")
            page.goto("https://www.mercadolivre.com.br/ofertas", timeout=60000)
            
            # Espera um pouco para a página carregar
            page.wait_for_timeout(3000)
            
            # Rola a página para baixo para forçar o carregamento das imagens e produtos
            print("Rolando a página...")
            page.evaluate("window.scrollBy(0, 1000)")
            page.wait_for_timeout(2000)
            
            # O Mercado Livre usa a classe 'poly-card' ou 'promotion-item' dependendo do layout
            # Vamos buscar por ambos
            cards = page.locator('.poly-card, .promotion-item').all()
            print(f"Encontrados {len(cards)} cards na tela.")
            
            for card in cards[:15]:  # Pega os 15 primeiros
                try:
                    # Tenta pegar os elementos
                    titulo_elem = card.locator('.poly-component__title, .promotion-item__title').first
                    preco_elem = card.locator('.andes-money-amount__fraction').first
                    link_elem = card.locator('a').first
                    
                    if titulo_elem.count() > 0 and preco_elem.count() > 0:
                        titulo = titulo_elem.inner_text().strip()
                        preco_texto = preco_elem.inner_text().strip().replace(".", "")
                        link = link_elem.get_attribute("href")
                        
                        # Tenta pegar a imagem
                        img_elem = card.locator('img').first
                        img = ""
                        if img_elem.count() > 0:
                            img = img_elem.get_attribute("src") or img_elem.get_attribute("data-src") or ""
                        
                        ofertas.append({
                            "plataforma": "Mercado Livre",
                            "titulo": titulo,
                            "preco": float(preco_texto),
                            "link": link,
                            "imagem": img
                        })
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Erro ao acessar o Mercado Livre: {e}")
        finally:
            browser.close()
            
    print(f"Total de ofertas capturadas: {len(ofertas)}")
    return ofertas

def enviar_whatsapp(ofertas):
    """Envia um resumo das ofertas para o WhatsApp via GREEN-API."""
    if not GREEN_API_INSTANCE_ID or not GREEN_API_TOKEN or not WHATSAPP_PHONE:
        print("GREEN-API não configurada. Pulando envio.")
        return
    
    # Se não achar nada, envia um aviso
    if len(ofertas) <= 1 and ofertas[0]['plataforma'] == 'Aviso':
        mensagem = "⚠️ O robô não conseguiu encontrar ofertas hoje. O Mercado Livre pode ter bloqueado o acesso."
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
            print("WhatsApp enviado com sucesso!")
    except Exception as e:
        print(f"Erro de conexão GREEN-API: {e}")

if __name__ == "__main__":
    print("Iniciando coleta de ofertas...")
    
    todas_ofertas = buscar_mercadolivre()
    
    if not todas_ofertas:
        print("Nenhuma oferta encontrada hoje.")
        todas_ofertas = [{
            "plataforma": "Aviso",
            "titulo": "O Mercado Livre bloqueou o robô hoje. Aguarde a próxima execução.",
            "preco": 0.0,
            "link": "#",
            "imagem": ""
        }]
    
    with open("ofertas.json", "w", encoding="utf-8") as f:
        json.dump(todas_ofertas, f, ensure_ascii=False, indent=2)
    
    enviar_whatsapp(todas_ofertas)
    print(f"Coleta finalizada. {len(todas_ofertas)} ofertas salvas.")
