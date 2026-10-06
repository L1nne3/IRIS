"""Aplicação Streamlit futurista da I.R.I.S. (Intelligent Resource & Interface System)."""

__name__ = "iris_app"

import os
import re
from pathlib import Path
from typing import Any

import streamlit as st

try:
    from google import genai
except ImportError:
    genai = None

try:
    from importlib import import_module

    pygame = import_module("pygame")
except (ImportError, ModuleNotFoundError):
    pygame = None

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    spotipy = None
    SpotifyOAuth = None

st.set_page_config(page_title="I.R.I.S. — IA", page_icon="◈", layout="wide")

SYSTEM_PROMPT = (
    "Você é a I.R.I.S., um assistente virtual inteligente, eficiente, formal, "
    "leal e sucinta. Responda em português brasileiro. Seja direto, não invente "
    "informações e confirme ações sensíveis antes de executá-las."
)
API_KEY = os.getenv("GENAI_API_KEY") or st.session_state.get("AQ.Ab8RN6Jl10iSSNehw2BEz7jK7y76fIg1QNXrJQbHz0ZuUEz8uA", "")
AUDIO_DIRECTORY = Path(os.getenv("AUDIO_DIRECTORY", "audios"))
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
if "spotify_status" not in st.session_state:
    st.session_state.spotify_status = "Spotify não conectado."

CSS = """
:root { --iris:#22d3ee; --iris-bright:#67e8f9; --panel:rgba(5,14,25,.88); --line:rgba(103,232,249,.22); }
html, body, [class*="stApp"] { background:#02060c; color:#e9faff; font-family:Inter,ui-sans-serif,system-ui,sans-serif; }
[data-testid="stAppViewContainer"] {
    background-image:radial-gradient(circle at 50% 28%,rgba(34,211,238,.1),transparent 34%),
        linear-gradient(rgba(34,211,238,.025) 1px,transparent 1px),
        linear-gradient(90deg,rgba(34,211,238,.025) 1px,transparent 1px);
    background-size:auto,32px 32px,32px 32px;
}
[data-testid="stSidebar"] { background:#030911; border-right:1px solid var(--line); }
.iris-title { color:#e9faff; font-size:2.1rem; font-weight:800; letter-spacing:.16em; text-shadow:0 0 24px rgba(34,211,238,.35); }
.iris-subtitle { color:#83a8b7; font-size:.78rem; letter-spacing:.25em; text-transform:uppercase; }
.iris-panel { background:linear-gradient(145deg,rgba(8,24,37,.92),rgba(3,10,18,.95)); border:1px solid var(--line); border-radius:18px; box-shadow:inset 0 0 30px rgba(34,211,238,.035),0 12px 45px rgba(0,0,0,.35); }
.orb-shell { position:relative; width:180px; height:180px; display:grid; place-items:center; margin:8px auto; }
.orb { width:112px; height:112px; border-radius:50%; background:radial-gradient(circle at 35% 30%,#e9ffff 0%,#67e8f9 8%,#22d3ee 30%,#075985 65%,#03131e 100%); box-shadow:0 0 25px rgba(34,211,238,.75),0 0 80px rgba(34,211,238,.3),inset -18px -20px 35px rgba(0,0,0,.45); animation:pulse 3s ease-in-out infinite; }
.orb::after { content:""; display:block; width:100%; height:100%; border-radius:50%; background:conic-gradient(from 30deg,transparent,rgba(255,255,255,.8),transparent 28%,rgba(34,211,238,.8),transparent 70%); animation:spin 5s linear infinite; mix-blend-mode:screen; }
.orb-ring { position:absolute; inset:14px; border:1px solid rgba(103,232,249,.42); border-radius:50%; animation:ring 4s linear infinite; }
.orb-ring::before,.orb-ring::after { content:""; position:absolute; width:10px; height:10px; border-radius:50%; background:#a5f3fc; box-shadow:0 0 15px #22d3ee; }
.orb-ring::before { top:20px; left:18px; }.orb-ring::after { right:6px; bottom:37px; }
.orb.processing .orb { animation:processing .7s ease-in-out infinite alternate; }
.orb.processing .orb-ring { animation:ring .9s linear infinite; }
@keyframes pulse { 0%,100%{transform:scale(.96);filter:brightness(.9)}50%{transform:scale(1.05);filter:brightness(1.15)} }
@keyframes processing { 0%{transform:scale(.9);filter:brightness(.85)}100%{transform:scale(1.13);filter:brightness(1.35)} }
@keyframes ring { to{transform:rotate(360deg)} } @keyframes spin { to{transform:rotate(360deg)} }
.chat-bubble { padding:12px 14px; border-radius:15px 15px 15px 4px; background:linear-gradient(135deg,rgba(34,211,238,.15),rgba(6,24,38,.7)); border:1px solid rgba(103,232,249,.2); }
.chat-bubble.user { margin-left:24%; background:linear-gradient(135deg,rgba(24,63,88,.7),rgba(7,19,32,.85)); border-radius:15px 15px 4px 15px; }
.stButton>button,[data-testid="stChatInputSubmitButton"] { background:linear-gradient(135deg,#0ea5e9,#0891b2); color:white; border:1px solid #67e8f9; border-radius:10px; box-shadow:0 0 18px rgba(34,211,238,.18); }
[data-testid="stTextArea"] { background:#07111d; border:1px solid rgba(103,232,249,.25); color:#e9faff; }
"""
st.markdown(CSS, unsafe_allow_html=True)


def _client_gemini() -> Any:
    """Cria o cliente Gemini sem falhar quando a configuração não existe."""
    try:
        api_key = st.session_state.get("genai_api_key") or os.getenv("GENAI_API_KEY", "")
        if not genai or not api_key:
            return None
        return genai.Client(api_key=api_key)
    except Exception as exc:
        st.warning(f"Erro ao configurar o Gemini: {exc}")
        return None


def _ask_gemini(pergunta: str, cliente: Any) -> str:
    """Pergunta ao Gemini modelo 2.5 Flash."""
    try:
        if not cliente:
            return "Configure GENAI_API_KEY ou informe a chave na barra lateral."
        response = cliente.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{SYSTEM_PROMPT}\n\nUsuário: {pergunta}",
        )
        return response.text or "I.R.I.S. não recebeu uma resposta válida."
    except Exception as exc:
        return f"Erro do Gemini: {exc}"


def _spotify_client() -> Any:
    """Cria o cliente Spotipy com OAuth no redirect local."""
    try:
        if not spotipy or not SpotifyOAuth:
            raise RuntimeError("O pacote spotipy não está instalado.")
        if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
            raise RuntimeError("Credenciais do Spotify ausentes.")
        auth = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope="user-library-read user-playlists-read user-playlists-modify user-read-currently-playing user-modify-currently-playing",
        )
        return spotipy.Spotify(auth_manager=auth)
    except Exception as exc:
        return None, str(exc)


def _spotify_action(comando: str) -> str:
    """Executa operações básicas do Spotify com tratamento de erro."""
    try:
        result = _spotify_client()
        if isinstance(result, tuple):
            client, error = result
            return f"Spotify indisponível: {error}"
        client = result
        normal = comando.lower()
        if "pausar" in normal:
            client.pause(); return "Spotify pausado."
        if "retomar" in normal or "continuar" in normal:
            client.resume(); return "Spotify retomado."
        if "próximo" in normal or "proximo" in normal:
            client.next(); return "Música seguinte."
        if "anterior" in normal or "voltar" in normal:
            client.previous(); return "Música anterior."
        if "agora" in normal or "tocando" in normal:
            current = client.current_user_playing() or {}
            item = current.get("item", {})
            return f"Tocando '{item.get('name', 'uma música')}'."
        if "volume" in normal:
            value = re.search(r"(\d{1,3})", comando)
            if not value:
                return "Informe um volume entre 0 e 100."
            level = max(0, min(100, int(value.group(1))))
            client.volume(level)
            return f"Volume do Spotify: {level}%"
        return "Pedido de Spotify identificado, mas não houve ação válida."
    except Exception as exc:
        return f"Não foi possível usar o Spotify: {exc}"


def _reproduzir_audio(nome_arquivo: str) -> None:
    """Reproduz MP3/WAV local e ignora falhas opcionais."""
    try:
        if not pygame or not AUDIO_DIRECTORY.exists():
            return
        caminho = AUDIO_DIRECTORY / nome_arquivo
        if not caminho.is_file() or caminho.suffix.lower() not in {".mp3", ".wav"}:
            return
        pygame.mixer.init()
        pygame.mixer.music.load(str(caminho))
        pygame.mixer.music.play()
    except Exception:
        pass


def _route_command(comando: str) -> tuple[str, str | None]:
    """Roteia o comando entre Gemini, Spotify e áudio."""
    normal = comando.lower()
    if any(word in normal for word in ("spotify", "música", "musica", "track", "playlist")):
        return _spotify_action(comando), None
    match = re.search(r"(?:arquivo|som|música|audio)\s*[:\-]?\s*([a-z0-9_.-]+)", comando, re.I)
    if re.search(r"\b(play|reproduzir|audio|som)\b", normal) and match:
        return "Áudio solicitado.", match.group(1)
    return _ask_gemini(comando, _client_gemini()), None


def _render_header() -> None:
    """Renderiza o cabeçalho e o orb de interface."""
    st.markdown("<div class='iris-title'>I.R.I.S.</div><div class='iris-subtitle'>Intelligent Resource & Interface System</div>", unsafe_allow_html=True)
    orb_col, status_col = st.columns([1, 1.15])
    with orb_col:
        processing_class = " processing" if st.session_state.is_processing else ""
        st.markdown(f"<div class='orb-shell'><div class='orb-ring'></div><div class='orb{processing_class}'></div></div>", unsafe_allow_html=True)
    with status_col:
        st.markdown("<div class='iris-panel' style='padding:16px'>", unsafe_allow_html=True)
        st.write("**Estado:**")
        st.write(f"IA: {'processando' if st.session_state.is_processing else 'em descanso'}")
        st.write(f"Spotify: {st.session_state.spotify_status}")
        st.markdown("</div>", unsafe_allow_html=True)


def _render_messages() -> None:
    """Exibe o histórico recebido na sessão atual."""
    st.subheader("Histórico de conversa")
    if not st.session_state.messages:
        st.info("A conversa está vazia. Envie uma mensagem para iniciar.")
        return
    for message in st.session_state.messages:
        nome = "I.R.I.S." if message["role"] == "assistant" else "Você"
        bubble_class = "chat-bubble" if message["role"] == "assistant" else "chat-bubble user"
        st.markdown(f"<div class='{bubble_class}'><strong style='color:#67e8f9'>{nome}</strong><br>{message['content']}</div>", unsafe_allow_html=True)


def _main() -> None:
    """Fluxo principal da interface."""
    st.markdown("<div class='iris-panel' style='padding:20px;margin-bottom:14px'><div class='iris-title'>I.R.I.S.</div><div class='iris-subtitle'>Intelligent Resource & Interface System</div></div>", unsafe_allow_html=True)
    sidebar = st.sidebar
    sidebar.header("Configuração")
    sidebar.markdown("**Gemini**")
    key = sidebar.text_input("GENAI_API_KEY", type="password", placeholder="Insira a chave do Google AI")
    if key:
        st.session_state.genai_api_key = key
    sidebar.markdown("**Áudio local**")
    sidebar.caption("Arquivos .mp3 ou .wav em " + str(AUDIO_DIRECTORY))
    sidebar.markdown("**Spotify OAuth**")
    sidebar.caption(f"Redirect: {SPOTIFY_REDIRECT_URI}")
    sidebar.caption("Configure as credenciais do Spotify no ambiente.")

    _render_header()
    _render_messages()
    prompt = st.chat_input("Fale com I.R.I.S.")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.is_processing = True
        try:
            with st.spinner("I.R.I.S. está processando...", text="I.R.I.S. está processando..."):
                resposta, audio_nome = _route_command(prompt)
            st.session_state.messages.append({"role": "assistant", "content": resposta})
            if audio_nome:
                _reproduzir_audio(audio_nome)
            if "spotify" in prompt.lower() or "música" in prompt.lower() or "musica" in prompt.lower():
                st.session_state.spotify_status = "Spotify processado."
        except Exception as exc:
            st.session_state.messages.append({"role": "assistant", "content": f"Erro inesperado: {exc}"})
        finally:
            st.session_state.is_processing = False
            st.rerun()


try:
    _main()
except Exception as exc:
    st.error(f"Falha da aplicação: {exc}")

# -----------------------------------------------------------
# 1) IMPORTAÇÕES
# As importações trazem funções e bibliotecas que o programa usa.
# import os -> permite ler variáveis de ambiente e caminhos do sistema.
# import re -> permite procurar padrões em texto, como "tocar música".
# from typing import Any -> ajuda a definir tipos de dados em Python.
# -----------------------------------------------------------
import os
import re
from typing import Any

# -----------------------------------------------------------
# 2) BIBLIOTECAS OPCIONAIS
# Essas partes são "tentativas" de importar ferramentas extras.
# Se o pacote não estiver instalado, a variável fica em None.
# Isso deixa o programa funcionando mesmo sem alguns recursos.
# -----------------------------------------------------------
try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    from google import genai
except ImportError:
    genai = None

# -----------------------------------------------------------
# 3) CONFIGURAÇÃO BÁSICA DA IA
# NOME_IA -> nome que aparece na conversa.
# API_KEY -> chave para usar o Gemini, lida das variáveis do sistema.
# client -> objeto que conecta com a API do Google AI.
# -----------------------------------------------------------
NOME_IA = "IRIS"
API_KEY = (os.getenv("GENAI_API_KEY") or "").strip()

# O cliente é criado somente quando necessário. Isso evita falhas de
# configuração durante a importação e permite tratar a chave com melhor
# clareamento quando o usuário não defini-la no ambiente.
client = genai.Client(api_key=API_KEY) if genai and API_KEY else None

# -----------------------------------------------------------
# 4) VOZ (TTS)
# A voz do Google fica ativa por padrão. Para usar outra engine,
# altere TTS_ENGINE para "pyttsx3" no ambiente.
# -----------------------------------------------------------
TTS_ENGINE = os.getenv("TTS_ENGINE", "google").lower()
GOOGLE_TTS_MODEL = os.getenv("GOOGLE_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GOOGLE_TTS_VOICE = os.getenv("GOOGLE_TTS_VOICE", "Kore")
engine = pyttsx3.init() if pyttsx3 and TTS_ENGINE == "pyttsx3" else None
if engine:
    engine.setProperty("rate", 185)
    for voice in engine.getProperty("voices") or []:
        if "brazil" in voice.name.lower() or "portuguese" in voice.name.lower():
            engine.setProperty("voice", voice.id)
            break


def _google_tts(text: str) -> bytes | None:
    """Gera áudio em voz com o Gemini e retorna os dados digitais."""
    if not client:
        return None
    response = client.models.generate_content(
        model=GOOGLE_TTS_MODEL,
        contents=text,
        config={
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": GOOGLE_TTS_VOICE,
                    }
                }
            },
        },
    )
    for candidate in response.candidates or []:
        for part in candidate.content.parts or []:
            inline_data = getattr(part, "inline_data", None)
            data = getattr(inline_data, "data", None)
            if data:
                import base64
                return base64.b64decode(data)
    return None


def _play_google_audio(audio_data: bytes) -> bool:
    """Reproduz o áudio gerado pelo Google no Windows."""
    import tempfile
    import wave

    mime_type = "audio/pcm"
    try:
        import winsound

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
            temporary_path = audio_file.name
        if mime_type == "audio/pcm":
            with wave.open(temporary_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(24000)
                wav_file.writeframes(audio_data)
        else:
            with open(temporary_path, "wb") as audio_file:
                audio_file.write(audio_data)
        winsound.PlaySound(temporary_path, winsound.SND_FILENAME)
        return True
    except Exception as exc:
        print(f"Erro ao reproduzir a voz do Google: {exc}")
        return False


# -----------------------------------------------------------
# 5) FUNÇÃO DE FALAR
# Esta função usa a voz do Google primeiro e mantém pyttsx3
# como fallback quando a voz do Google não estiver disponível.
# -----------------------------------------------------------
def falar(text: str) -> None:
    """Fala o texto com a voz configurada."""
    text = str(text or "").strip()
    if not text:
        return
    print(f"{NOME_IA}: {text}")
    if TTS_ENGINE == "google":
        try:
            audio_data = _google_tts(text)
            if audio_data and _play_google_audio(audio_data):
                return
        except Exception as exc:
            print(f"Erro do TTS do Google: {exc}")
    if engine:
        engine.say(text)
        engine.runAndWait()


# -----------------------------------------------------------
# 6) FUNÇÃO COM O GEMINI
# Aqui a IA manda a pergunta para o Gemini (modelo de IA do Google).
# Se não tiver chave configurada, a função manda uma mensagem avisando.
# -----------------------------------------------------------
def perguntar_gemini(pergunta: str) -> str:
    """Resposta do Gemini, com pesquisa na internet quando disponível."""
    if not client:
        return "Configure GENAI_API_KEY no painel de variáveis de ambiente."
    try:
        tools = []
        try:
            from google.genai import types
            tools.append(types.GoogleSearch())
        except Exception:
            pass
        config = {"tools": tools} if tools else None
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                "Você é a IRIS, uma assistente virtual amigável, direta e concisa. "
                "Responda em português brasileiro. Não invente informações. "
                "Se pedir ação no Spotify, luzes ou chamadas, confirme o usuário. "
                f"\n\nUtilizador: {pergunta}"
            ),
            config=config,
        )
        return response.text or "Não recebi uma resposta."
    except Exception as exc:
        print(f"Erro do Gemini: {exc}")
        return "Ocorreu um erro ao conectar aos servidores de inteligência."


# -----------------------------------------------------------
# 7) SPOTIFY
# Essa parte conecta com a conta do Spotify do usuário.
# Ela consegue tocar música, pausar, avançar, mudar volume e abrir playlists.
# Para funcionar, precisa das chaves do Spotify no ambiente.
# -----------------------------------------------------------
def _spotify_client():
    """Cria o cliente Spotipy com credenciais de ambiente."""
    try:
        import importlib

        spotipy = importlib.import_module("spotipy")
        SpotifyOAuth = importlib.import_module("spotipy.oauth2").SpotifyOAuth
    except ModuleNotFoundError as exc:
        raise RuntimeError("Instale o pacote spotipy.") from exc

    client_id = (os.getenv("SPOTIFY_CLIENT_ID") or "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
    if not client_id or not client_secret:
        raise RuntimeError("Configure SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET.")
    auth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="user-library-read user-playlists-read user-playlists-modify user-read-currently-playing user-modify-currently-playing",
    )
    return spotipy.Spotify(auth_manager=auth)


def _spotify_action(comando: str) -> str:
    """Executa tocar, pausar, próximo, playlist e volume no Spotify."""
    try:
        sp = _spotify_client()
        normal = comando.lower()
        if "pausa" in normal:
            sp.pause()
            return "Spotify pausado."
        if "próximo" in normal or "proximo" in normal:
            sp.next()
            return "Música seguinte."
        if "anterior" in normal or "voltar" in normal:
            sp.previous()
            return "Música anterior."
        if "volume" in normal:
            number = re.search(r"(\d{1,3})", comando)
            if not number:
                return "Informe um volume, por exemplo: 30%."
            sp.volume(min(100, max(0, int(number.group(1)))))
            return f"Volume do Spotify definido em {number.group(1)}%."
        if "playlist" in normal or "lista" in normal:
            playlist_name = re.sub(
                r"^(?:tocar|reproduzir|abre|abra|carregar|que|encontre|ache)\s+", "", comando, flags=re.I
            ).strip()
            for playlist in sp.current_user_playlists(limit=100):
                if playlist["name"].lower() == playlist_name.lower():
                    sp.playlist(playlist["uri"])
                    return f"Playlist '{playlist['name']}' iniciada."
            return f"Playlist '{playlist_name}' não encontrada."

        query = re.sub(
            r"^(?:tocar|reproduzir|play|que|encontre|ache|busque|busque\s+uma|encontre\s+uma)\s+", "", comando, flags=re.I
        ).strip()
        results = sp.search(q=query, type="track", limit=1)
        items = results.get("tracks", {}).get("items", [])
        if not items:
            return f"Não encontrei '{query}'."
        track = items[0]
        sp.play(uris=[track["uri"]])
        return f"Tocando '{track['name']}' de '{track['artists'][0]['name']}'."
    except Exception as exc:
        return f"Não foi possível usar o Spotify: {exc}"


# -----------------------------------------------------------
# 8) PARTE DA LÂMPADA (DESATIVADA)
# Esta parte foi separada porque você ainda não tem a lâmpada/bridge.
# Enquanto isso, ela fica pronta para quando você comprar o hardware.
# Só precisa configurar HUE_BRIDGE_IP, HUE_USERNAME e HUE_LIGHT_IDS.
# -----------------------------------------------------------
def _hue_action(comando: str) -> str:
    """Liga, desliga ou altera o brilho de luzes Philips Hue."""
    bridge_ip = os.getenv("HUE_BRIDGE_IP")
    username = os.getenv("HUE_USERNAME")
    light_ids = [item.strip() for item in os.getenv("HUE_LIGHT_IDS", "").split(",") if item.strip()]
    if not bridge_ip or not username or not light_ids:
        return "Configure HUE_BRIDGE_IP, HUE_USERNAME e HUE_LIGHT_IDS."

    payload: dict[str, Any] = {}
    if re.search(r"\b(liga|acenda|acender|on)\b", comando, flags=re.I):
        payload["on"] = True
    elif re.search(r"\b(desliga|apague|apaga|off)\b", comando, flags=re.I):
        payload["on"] = False
    elif re.search(r"\b(brilho|intensidade|brightness)\b", comando, flags=re.I):
        match = re.search(r"(\d{1,3})", comando)
        if match:
            payload["bri"] = min(254, max(1, int(match.group(1))))
    else:
        return "Exemplo: 'liga as luzes', 'desliga as luzes' ou 'defina o brilho para 50'."

    import requests
    failures = []
    for light_id in light_ids:
        try:
            response = requests.put(
                f"http://{bridge_ip}/api/{username}/lights/{light_id}/state",
                json=payload,
                timeout=5,
            )
            response.raise_for_status()
            if response.json().get("error"):
                failures.append(str(response.json()["error"]))
        except Exception as exc:
            failures.append(str(exc))
    if failures:
        return f"Não foi possível controlar as luzes: {', '.join(failures)}"
    return f"Luzes controladas: {', '.join(light_ids)}."


# -----------------------------------------------------------
# 9) CHAMADAS
# Essa parte faz uma ligação telefônica com confirmação do usuário.
# É importante porque a IA não pode ligar sem pedir autorização.
# -----------------------------------------------------------
def _call_action(comando: str) -> str:
    """Faz uma chamada somente quando o usuário confirmar."""
    number = os.getenv("CALL_NUMBER")
    if not number:
        return "Configure CALL_NUMBER com o número de destino."
    if not re.search(r"\b(ligar|chamar|chame|call|telefone)\b", comando, flags=re.I):
        return "Não identifiquei um pedido de chamada."
    confirmed = input(f"Confirmar chamada para {number}? [s/N]: ").strip().lower()
    if confirmed not in {"s", "sim", "yes", "y"}:
        return "Chamada cancelada."

    try:
        TwilioClient = __import__("twilio.rest", fromlist=["Client"]).Client
    except ImportError as exc:
        raise RuntimeError("Instale o pacote twilio.") from exc
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    if not all((account_sid, auth_token, from_number)):
        return "Configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN e TWILIO_FROM_NUMBER."
    twilio = TwilioClient(account_sid, auth_token)
    twilio.calls.create(
        to=number,
        from_=from_number,
        twiml="<Response><Say>Olá! Eu sou a IRIS, assistente virtual.</Say></Response>",
    )
    return f"Chamada enviada para {number}."


# -----------------------------------------------------------
# 10) ROTEADOR DE COMANDOS
# Esta função decide qual parte do programa vai usar.
# - Spotify: música
# - Lâmpada: desativada por enquanto
# - Chamada: liga o telefone com confirmação
# - Se não for nada disso, pergunta ao Gemini
# -----------------------------------------------------------
def executar_comando(comando: str) -> str:
    """Roteia mensagens para o sistema correspondente."""
    text = comando.strip()
    normal = text.lower()
    if any(word in normal for word in ("spotify", "música", "musica", "track", "playlist", "lista")):
        return _spotify_action(text)
    # Parte da lâmpada: desativada enquanto você não tiver a lâmpada.
    # if any(word in normal for word in ("luz", "light", "hue", "iluminação", "iluminacao")):
    #     return _hue_action(text)
    if any(word in normal for word in ("ligar", "chamar", "telefone", "call")):
        return _call_action(text)
    return perguntar_gemini(text)


# -----------------------------------------------------------
# 11) MICROFONE
# Reconhece a voz da pessoa usando o microfone.
# Depois transforma o áudio em texto para a IA entender.
# -----------------------------------------------------------
def ouvir_microfone() -> str | None:
    """Reconhece uma expressão de voz usando o microfone."""
    if not sr:
        return None
    rec = sr.Recognizer()
    try:
        with sr.Microphone() as mic:
            rec.adjust_for_ambient_noise(mic, duration=0.8)
            print("\nA ouvir...")
            audio = rec.listen(mic, timeout=5)
            texto = rec.recognize_google(audio, language="pt-BR")
            print(f"Você falou: {texto}")
            return texto
    except sr.UnknownValueError:
        print("Não consegui perceber o áudio.")
        return None
    except Exception as exc:
        print(f"Erro no microfone: {exc}")
        return None


# -----------------------------------------------------------
# 12) MENU PRINCIPAL
# É a interface: o usuário escolhe digitar ou falar.
# Depois a IA responde de acordo com o comando.
# -----------------------------------------------------------
def main() -> None:
    """Interface simples de texto ou voz."""
    falar("Sistemas online. Como posso ajudar?")
    while True:
        print("\n-------------------------------------------")
        print("1. Digitar mensagem")
        print("2. Falar ao microfone")
        print("3. Sair")
        opcao = input("Opção (1/2/3): ").strip()
        if opcao == "1":
            comando = input("\nVocê: ")
        elif opcao == "2":
            comando = ouvir_microfone()
        elif opcao == "3":
            falar("A desligar sistemas. Até logo!")
            break
        else:
            print("Opção inválida.")
            continue
        if not comando:
            continue
        if comando.lower() in {"sair", "desligar", "fechar", "sair agora"}:
            falar("Até breve!")
            break
        falar(executar_comando(comando))


# -----------------------------------------------------------
# 13) EXECUÇÃO DO PROGRAMA
# Este bloco garante que o programa só rode quando for executado diretamente.
# -----------------------------------------------------------
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nIRIS encerrada.")
