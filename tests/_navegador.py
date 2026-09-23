"""
Utilidades para las pruebas que abren el dashboard en un Chrome real, sin ventana (headless), y lo miden por dentro.

- `Servidor`: levanta `streamlit run dashboard/app.py` en un puerto libre y lo cierra al salir.
- `Chrome`: lanza Chrome con el protocolo de depuración (CDP), navega, evalúa JavaScript y saca capturas. El cliente
  WebSocket es el de `tornado`, que Streamlit ya instala: no hace falta Selenium ni Playwright.

Chrome se busca en las rutas habituales; se puede fijar con la variable de entorno CHROME_PATH.
La fuente Inter se descarga de Google Fonts al cargar la página: sin internet el navegador usa Arial y las medidas cambian un poco.
"""
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from tornado.websocket import websocket_connect

RAIZ = Path(__file__).resolve().parent.parent

_RUTAS_CHROME = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def buscar_chrome():
    """Ruta del ejecutable de Chrome/Chromium, o None si no hay uno instalado."""
    if os.environ.get("CHROME_PATH"):
        return os.environ["CHROME_PATH"]
    for ruta in _RUTAS_CHROME:
        if os.path.exists(ruta):
            return ruta
    return shutil.which("chrome") or shutil.which("chromium") or shutil.which("google-chrome")


def cerrar(proceso):
    """Termina un proceso y todos sus hijos. En Windows `terminate()` deja vivos los procesos hijos de Chrome (renderizadores, GPU, red),
    así que se usa `taskkill /T`."""
    if proceso.poll() is None:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proceso.pid)], capture_output=True)
        else:
            proceso.terminate()
    try:
        proceso.wait(10)
    except subprocess.TimeoutExpired:
        proceso.kill()


def puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Servidor:
    """Contexto que deja el dashboard corriendo (puerto propio, sin abrir el navegador) y lo termina al salir."""

    def __init__(self):
        self.puerto = puerto_libre()
        self.url = f"http://localhost:{self.puerto}"
        self._proceso = None

    def __enter__(self):
        self._proceso = subprocess.Popen(
            [sys.executable, "-B", "-m", "streamlit", "run", "dashboard/app.py", "--server.port", str(self.puerto),
             "--server.headless", "true", "--browser.gatherUsageStats", "false"],
            cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        limite = time.time() + 60
        while time.time() < limite:
            try:
                if urllib.request.urlopen(f"{self.url}/_stcore/health", timeout=2).read() == b"ok":
                    return self
            except OSError:
                time.sleep(0.5)
        self.__exit__()
        raise RuntimeError("El servidor de Streamlit no respondió en 60 s.")

    def __exit__(self, *args):
        if self._proceso:
            cerrar(self._proceso)


class Chrome:
    """Contexto con un Chrome headless controlado por CDP. `ancho` y `alto` fijan el viewport (px)."""

    def __init__(self, ancho=1920, alto=1080):
        self.ancho, self.alto = ancho, alto
        self._proceso = self._ws = None
        self._id = 0
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)  # tornado abre el WebSocket en el loop «actual»
        self._perfil = tempfile.mkdtemp(prefix="chrome_pruebas_")

    def __enter__(self):
        ruta = buscar_chrome()
        if not ruta:
            raise RuntimeError("No se encontró Chrome/Chromium (define CHROME_PATH).")
        puerto = puerto_libre()
        self._proceso = subprocess.Popen(
            [ruta, "--headless=new", f"--remote-debugging-port={puerto}", f"--user-data-dir={self._perfil}", "--remote-allow-origins=*",
             "--no-first-run", "--disable-gpu", "--hide-scrollbars", f"--window-size={self.ancho},{self.alto}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        limite, destino = time.time() + 30, None
        while time.time() < limite and not destino:
            try:
                paginas = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{puerto}/json", timeout=2).read())
                destino = next((p["webSocketDebuggerUrl"] for p in paginas if p.get("type") == "page"), None)
            except OSError:
                time.sleep(0.3)
        if not destino:
            self.__exit__()
            raise RuntimeError("Chrome no abrió el puerto de depuración en 30 s.")
        self._ws = self._loop.run_until_complete(websocket_connect(destino, max_message_size=64 * 1024 * 1024))
        self.enviar("Emulation.setDeviceMetricsOverride", width=self.ancho, height=self.alto, deviceScaleFactor=1, mobile=False)
        return self

    def __exit__(self, *args):
        if self._ws:
            self._ws.close()
        if self._proceso:
            cerrar(self._proceso)
        self._loop.close()
        shutil.rmtree(self._perfil, ignore_errors=True)

    def enviar(self, metodo, **parametros):
        """Llama a un método de CDP y devuelve su resultado (ignora los eventos que lleguen en el intertanto)."""
        self._id += 1
        mensaje_id = self._id
        self._loop.run_until_complete(self._ws.write_message(json.dumps({"id": mensaje_id, "method": metodo, "params": parametros})))
        while True:
            crudo = self._loop.run_until_complete(self._ws.read_message())
            if crudo is None:
                raise RuntimeError("Chrome cerró la conexión.")
            respuesta = json.loads(crudo)
            if respuesta.get("id") == mensaje_id:
                if "error" in respuesta:
                    raise RuntimeError(f"{metodo}: {respuesta['error']}")
                return respuesta.get("result", {})

    def navegar(self, url):
        self.enviar("Page.navigate", url=url)

    def evaluar(self, expresion):
        """Evalúa JavaScript en la página y devuelve el valor (serializable a JSON)."""
        r = self.enviar("Runtime.evaluate", expression=expresion, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(f"JavaScript: {r['exceptionDetails'].get('text')} {r['exceptionDetails'].get('exception', {}).get('description', '')}")
        return r["result"].get("value")

    def esperar(self, condicion_js, segundos=60):
        """Espera hasta que la expresión JavaScript sea verdadera; falla con un TimeoutError si no ocurre."""
        limite = time.time() + segundos
        while time.time() < limite:
            if self.evaluar(f"Boolean({condicion_js})"):
                return
            time.sleep(0.4)
        raise TimeoutError(f"No se cumplió en {segundos} s: {condicion_js}")

    def capturar(self, ruta):
        """Guarda una captura PNG del viewport."""
        import base64
        Path(ruta).write_bytes(base64.b64decode(self.enviar("Page.captureScreenshot", format="png")["data"]))


def abrir_dashboard(chrome, url):
    """Navega al dashboard y espera a que estén dibujados los 4 KPIs y el riel de navegación (st.navigation), más un
    instante para que cargue la fuente."""
    chrome.navegar(url)
    chrome.esperar("document.querySelectorAll('.kpi-celda').length === 4 && document.querySelector('[data-testid=\"stSidebarNav\"]')")
    chrome.evaluar("document.fonts.ready.then(() => true)")
    time.sleep(1.0)
