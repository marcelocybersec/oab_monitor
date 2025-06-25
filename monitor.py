import requests
from bs4 import BeautifulSoup
import json
import os
import time
import logging
import traceback
import sys
from dotenv import load_dotenv
from urllib.parse import unquote, quote

# Configuração simples do logger sem cores
logger = logging.getLogger(__name__)

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

formatter = logging.Formatter("%(asctime)s — %(levelname)s — %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
ch.setFormatter(formatter)
logger.addHandler(ch)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
INTERVALO_SEGUNDOS = int(os.getenv("INTERVALO_SEGUNDOS", "10"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
DELAY_ENTRE_ENVIOS = float(os.getenv("DELAY_ENTRE_ENVIOS", "1.0"))
SILENCIAR_ERROS = True  # ✅ Não envia erro no grupo

if not BOT_TOKEN or not CHAT_ID:
    logger.error("❌ Variáveis TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID devem estar definidas no .env")
    sys.exit(1)

ARQUIVO_JSON = os.path.join(os.path.dirname(__file__), "publicacoes.json")

URL_OAB = "https://examedeordem.oab.org.br/Noticias"
URL_FGV = "https://oab.fgv.br/NovoSec.aspx?key=jyMaUzWUnzQ=&codSec=5138"
BASE_URL_OAB = "https://examedeordem.oab.org.br"
BASE_URL_FGV = "https://oab.fgv.br"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; BotMonitor/1.0; +https://github.com/usuario/projeto)"
})

def carregar_publicacoes():
    if os.path.exists(ARQUIVO_JSON):
        try:
            with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("⚠️ JSON corrompido ou erro ao ler. Iniciando com lista vazia.")
    return []

def salvar_publicacoes(publicacoes):
    tmp_file = ARQUIVO_JSON + ".tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(publicacoes, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, ARQUIVO_JSON)
    except Exception:
        logger.error("❌ Falha ao salvar arquivo JSON:")
        logger.error(traceback.format_exc())

def ja_publicado(publicacoes, nova):
    return any(
        p["data"] == nova["data"] and
        p["titulo"] == nova["titulo"] and
        p["fonte"] == nova["fonte"]
        for p in publicacoes
    )

def raspar_oab():
    try:
        r = session.get(URL_OAB, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        datas = soup.find_all("div", class_="noticia-data")
        resumos = soup.find_all("div", class_="noticia-resumo")

        publicacoes = []
        for data_div, resumo_div in zip(datas, resumos):
            data = data_div.get_text(strip=True)
            titulo_tag = resumo_div.find("h4")
            link_tag = titulo_tag.find("a") if titulo_tag else None

            if link_tag:
                titulo = link_tag.get_text(strip=True)
                href = link_tag.get("href", "")
                url = f"{BASE_URL_OAB}{href}" if href.startswith("/") else href

                publicacoes.append({
                    "fonte": "OAB",
                    "data": data,
                    "titulo": titulo,
                    "url": url
                })

        return publicacoes

    except Exception:
        logger.error("❌ Erro ao raspar OAB")
        logger.error(traceback.format_exc())
        return []

def raspar_fgv():
    try:
        r = session.get(URL_FGV, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        linhas = soup.find_all("tr")

        publicacoes = []
        for linha in linhas:
            colunas = linha.find_all("td")
            if len(colunas) >= 2:
                data = colunas[0].get_text(strip=True)

                link = colunas[1].find("a")
                if link and link.has_attr("href"):
                    titulo = link.get_text(strip=True)
                    href = link["href"]

                    if href.startswith("/"):
                        url = f"{BASE_URL_FGV}{href}"
                    elif href.startswith("http"):
                        url = href
                    else:
                        url = f"{BASE_URL_FGV}/{href}"
                else:
                    titulo = colunas[1].get_text(strip=True)
                    url = None

                publicacoes.append({
                    "fonte": "FGV",
                    "data": data,
                    "titulo": titulo,
                    "url": url
                })

        return publicacoes

    except Exception:
        logger.error("❌ Erro ao raspar FGV")
        logger.error(traceback.format_exc())
        return []

def enviar_telegram(msg):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        r = session.post(api_url, data=payload, timeout=10)
        r.raise_for_status()
        logger.info("📤 Telegram enviado com sucesso.")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Falha ao enviar mensagem Telegram: {e}")
        raise

def enviar_telegram_com_retries(msg):
    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            enviar_telegram(msg)
            return True
        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 429:
                retry_after = http_err.response.json().get("parameters", {}).get("retry_after", 30)
                logger.warning(f"⚠️ Rate limit Telegram. Tentativa {tentativa}/{MAX_RETRIES}. Aguardando {retry_after}s...")
                time.sleep(retry_after + 1)
            else:
                logger.error(f"❌ Erro HTTP no envio Telegram: {http_err}")
                break
        except Exception as e:
            logger.warning(f"❗ Tentativa {tentativa} falhou: {e}")
            time.sleep(2 ** tentativa)
    logger.error("❌ Falha ao enviar mensagem após várias tentativas.")
    return False

def formatar_mensagem(pub):
    titulo_legivel = unquote(pub["titulo"]).replace(".pdf", "").strip()
    url_segura = quote(pub["url"], safe=":/?=&") if pub["url"] else ""

    if pub["url"]:
        titulo_link = f'<a href="{url_segura}">{titulo_legivel}</a>'
    else:
        titulo_link = titulo_legivel

    msg = (
        f"🆕 <b>Nova publicação no monitoramento!</b>\n\n"
        f"📌 <b>Título:</b> {titulo_link}\n"
        f"📅 <b>Data:</b> {pub['data']}\n"
        f"🏛️ <b>Fonte:</b> {pub['fonte']}\n\n"
        f"🔔 Fique atento para novidades!"
    )
    return msg

def monitorar_em_tempo_real(intervalo_segundos=INTERVALO_SEGUNDOS):
    logger.info(f"📡 Monitoramento ativo. Checando a cada {intervalo_segundos}s.")
    publicacoes_salvas = carregar_publicacoes()

    qtd_oab_ultimo = None
    qtd_fgv_ultimo = None

    while True:
        try:
            logger.info("🔎 Iniciando ciclo de monitoramento...")
            novas_oab = raspar_oab()
            novas_fgv = raspar_fgv()

            if qtd_oab_ultimo != len(novas_oab):
                logger.info(f"OAB: {len(novas_oab)} publicações encontradas.")
                qtd_oab_ultimo = len(novas_oab)

            if qtd_fgv_ultimo != len(novas_fgv):
                logger.info(f"FGV: {len(novas_fgv)} publicações encontradas.")
                qtd_fgv_ultimo = len(novas_fgv)

            novidades = 0
            for pub in novas_oab + novas_fgv:
                if not ja_publicado(publicacoes_salvas, pub):
                    msg = formatar_mensagem(pub)
                    sucesso = enviar_telegram_com_retries(msg)
                    if sucesso:
                        publicacoes_salvas.append(pub)
                        novidades += 1
                        logger.info(f"✅ Nova publicação enviada e salva: [{pub['fonte']}] {pub['data']} - {pub['titulo']}")
                    else:
                        logger.warning(f"❗ Publicação NÃO salva por falha no envio: {pub['titulo']}")

                    time.sleep(DELAY_ENTRE_ENVIOS)

            if novidades == 0:
                logger.info("Nenhuma novidade neste ciclo.")
            else:
                salvar_publicacoes(publicacoes_salvas)
                logger.info(f"Total de novas publicações enviadas e salvas: {novidades}")

        except Exception:
            logger.error("❌ Erro no ciclo principal:")
            logger.error(traceback.format_exc())
            if not SILENCIAR_ERROS:
                try:
                    enviar_telegram("❌ Erro no monitoramento. Verifique os logs.")
                except Exception:
                    logger.error("❌ Falha ao enviar mensagem de erro no Telegram.")

        time.sleep(intervalo_segundos)

if __name__ == "__main__":
    monitorar_em_tempo_real()
