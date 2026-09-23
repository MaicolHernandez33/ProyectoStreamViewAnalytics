"""
Corre TODA la regresión (los cuatro scripts de verificación) y resume el resultado. Código de salida 0 = todo bien.

    python tests/correr_todo.py                      # los cuatro (≈1 minuto)
    python tests/correr_todo.py --sin-navegador      # omite verificar_pantalla.py (no necesita Chrome)
    python tests/correr_todo.py --guardar r.json     # además guarda lo renderizado por verificar_estados.py
    python tests/correr_todo.py --comparar r.json    # además lo compara con una copia guardada (útil tras un refactor)
"""
import argparse
import re
import subprocess
import sys
import time

import _comun  # fija la codificación de la consola y silencia los avisos de logging

AQUI = _comun.RAIZ / "tests"
ap = argparse.ArgumentParser()
ap.add_argument("--sin-navegador", action="store_true")
ap.add_argument("--guardar")
ap.add_argument("--comparar")
args = ap.parse_args()

guiones = [
    ("verificar_reglas.py", []), ("verificar_cifras.py", []),
    ("verificar_estados.py", [*(["--guardar", args.guardar] if args.guardar else []), *(["--comparar", args.comparar] if args.comparar else [])]),
]
if not args.sin_navegador:
    guiones.append(("verificar_pantalla.py", []))

resultados = []
for nombre, extra in guiones:
    t0 = time.time()
    proceso = subprocess.run([sys.executable, "-B", str(AQUI / nombre), *extra], capture_output=True, text=True, encoding="utf-8", errors="replace")
    salida = proceso.stdout
    print(f"\n>>> {nombre}")
    for linea in salida.splitlines():
        if linea.startswith("  ✘") or linea.startswith("      ") or linea.startswith("---") or linea.startswith("  ·"):
            print(linea)
    if proceso.returncode != 0 and "✘" not in salida:  # falló sin llegar a resumir (error del script)
        print(proceso.stdout[-1500:], proceso.stderr[-1500:])
    resumen = re.search(r"(\d+) de (\d+) comprobaciones OK", salida)
    resultados.append((nombre, proceso.returncode, int(resumen.group(1)) if resumen else 0, int(resumen.group(2)) if resumen else 0, time.time() - t0))

print("\n" + "=" * 78 + "\nRESUMEN DE LA REGRESIÓN\n" + "=" * 78)
for nombre, codigo, ok, total, segundos in resultados:
    print(f"  {'✔ OK    ' if codigo == 0 else '✘ FALLA '} {nombre:24} {ok:4} de {total:<4} comprobaciones   {segundos:5.0f} s")
print(f"  {'':9} {'TOTAL':24} {sum(r[2] for r in resultados):4} de {sum(r[3] for r in resultados):<4}")
sys.exit(1 if any(r[1] for r in resultados) else 0)
