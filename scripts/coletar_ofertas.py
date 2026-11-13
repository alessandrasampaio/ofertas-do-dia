import os
import json
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
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
    print("Iniciando navegador MODO STEALTH...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Configurando um contexto que parece um navegador real
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="pt-BR"
        )
        page = context.new_page()
        
        # Aplica o disfarce Stealth
        stealth_sync(page)
        
        try:
            # Tenta acessar a página de busca de ofertas (às vezes é mais fácil que a home)
            print("Acessando o site...")
            page.goto("https://lista.mercadolivre.com.br/ofertas", timeout=60000)
            
            # Espera um tempo maior para parecer humano e dar tempo de carregar
            page.wait_for_timeout(5000)
            
            # Verifica se fomos bloqueados
            if "Just a moment" in page.title() or "Acesso negado" in page.title():
                print("Bloqueado pelo Cloudflare do Mercado Livre.")
                return []

            print(f"Página carregada: {page.title()}")
            
            # Rola a página
            page.evaluate("window.scrollBy(0, 1500)")
            page.wait_for_timeout(3000)
            
            # Novos seletores do Mercado Livre (baseados no layout atual)
            cards = page.locator('.poly-card, .ui-search-result').all()
            print(f"Encontrados {len(cards)} cards na tela.")
            
            for card in cards[:15]:
                try:
                    titulo_elem = card.locator('.poly-component__title, .ui-search-item__title').first
                    preco_elem = card.locator('.andes-money-amount__fraction').first
                    link_elem = card.locator('a').first
                    
                    if titulo_elem.count() > 0 and preco_elem.count() > 0:
                        titulo = titulo_elem.inner_text().strip()
                        preco_texto = preco_elem.inner_text().strip().replace(".", "")
                        link_original = link_elem.get_attribute("href")
                        
                        link_com_afiliado = adicionar_id_afiliado(link_original)
                        
                        img_elem = card.locator('img').first
                        img = ""
                        if img_elem.count() > 0:
                            img = img_elem.get_attribute("src") or img_elem.get_attribute("data-src") or ""
                        
                        ofertas.append({
                            "plataforma": "Mercado Livre",
                            "titulo": titulo,
                            "preco": float(preco_texto),
                            "link": link_com_afiliado,
                            "imagem": img
                        })
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"Erro ao acessar o Mercado Livre: {e}")
        finally:
            browser.close()
            
    print(f"Total de ofertas capturadas: {len(ofertas)}")
    return ofertas

def enviar_whatsapp(ofertas):
    if not GREEN_API_INSTANCE_ID or not GREEN_API_TOKEN or not WHATSAPP_PHONE:
        print("GREEN-API não configurada.")
        return
    
    if not ofertas or (len(ofertas) == 1 and ofertas[0]['plataforma'] == 'Aviso'):
        mensagem = "⚠️ O Mercado Livre bloqueou o acesso do robô hoje. (Cloudflare)"
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
        requests.post(url, json=payload, timeout=10)
        print("WhatsApp enviado!")
    except Exception as e:
        print(f"Erro WhatsApp: {e}")

if __name__ == "__main__":
    print("Iniciando coleta...")
    todas_ofertas = buscar_mercadolivre()
    
    if not todas_ofertas:
        todas_ofertas = [{
            "plataforma": "Aviso",
            "titulo": "O Mercado Livre bloqueou o acesso (Cloudflare).",
            "preco": 0.0,
            "link": "#",
            "imagem": ""
        }]
    
    with open("ofertas.json", "w", encoding="utf-8") as f:
        json.dump(todas_ofertas, f, ensure_ascii=False, indent=2)
    
    enviar_whatsapp(todas_ofertas)
    print(f"Finalizado. {len(todas_ofertas)} itens.")
