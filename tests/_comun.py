"""
Utilidades compartidas por los scripts de tests/: ruta del proyecto, silencio de los avisos de Streamlit fuera de `streamlit run`
y un contador de comprobaciones que imprime ✔ / ✘ y devuelve el código de salida (0 = todo bien, 1 = alguna falló).
"""
import logging
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows usa cp1252 y no imprime ✔ ni ×


# Fuera de `streamlit run`, Streamlit avisa «No runtime found» y «missing ScriptRunContext»: no es un problema, es ruido. AppTest vuelve a
# configurar esos loggers en cada corrida, así que se apagan los avisos de logging en todo el proceso (estos scripts informan con print).
logging.disable(logging.WARNING)


class Verificador:
    """Acumula comprobaciones: `comprobar(nombre, cumple, detalle)` imprime el resultado; `terminar()` resume y da el código de salida."""

    def __init__(self, titulo):
        self.titulo = titulo
        self.filas = []
        print(f"\n=== {titulo} ===")

    def comprobar(self, nombre, cumple, detalle=""):
        cumple = bool(cumple)
        self.filas.append((cumple, nombre))
        extra = f" — {detalle}" if detalle and (not cumple or self._verboso) else ""
        print(f"  {'✔' if cumple else '✘'} {nombre}{extra}")
        return cumple

    _verboso = False

    def info(self, texto):
        print(f"  · {texto}")

    def terminar(self):
        fallas = [n for ok, n in self.filas if not ok]
        print(f"--- {self.titulo}: {len(self.filas) - len(fallas)} de {len(self.filas)} comprobaciones OK" + (f"; FALLAN {len(fallas)}" if fallas else ""))
        return 1 if fallas else 0
