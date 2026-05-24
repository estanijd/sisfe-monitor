"""
Generador de licencias SISFE Monitor.
USO EXCLUSIVO DEL DESARROLLADOR — no distribuir este archivo.

Uso:
    python generator.py "Juan Perez" "juan@gmail.com"
    python generator.py "Juan Perez" "juan@gmail.com" --vence 2027-12-31
    python generator.py --lista        # ver todas las licencias generadas
"""
import sys
import json
import argparse
from datetime import date
from pathlib import Path

# Asegurar que el modulo validator sea accesible
sys.path.insert(0, str(Path(__file__).parent.parent))
from license.validator import encode_license, validate_license

REGISTRO = Path(__file__).parent / "licencias_emitidas.json"


def cargar_registro() -> list:
    if REGISTRO.exists():
        return json.loads(REGISTRO.read_text(encoding="utf-8"))
    return []


def guardar_registro(registro: list):
    REGISTRO.write_text(
        json.dumps(registro, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def generar(nombre: str, email: str, vencimiento=None) -> str:
    datos = {
        "producto":    "SISFE_MONITOR",
        "nombre":      nombre,
        "email":       email,
        "emitida":     date.today().isoformat(),
    }
    if vencimiento:
        datos["vencimiento"] = vencimiento

    code = encode_license(datos)

    # Registrar
    registro = cargar_registro()
    registro.append({**datos, "codigo": code})
    guardar_registro(registro)

    return code


def main():
    parser = argparse.ArgumentParser(description="Generador de licencias SISFE Monitor")
    parser.add_argument("nombre", nargs="?", help="Nombre del cliente")
    parser.add_argument("email",  nargs="?", help="Email del cliente")
    parser.add_argument("--vence", metavar="YYYY-MM-DD", help="Fecha de vencimiento (opcional)")
    parser.add_argument("--lista", action="store_true", help="Ver licencias emitidas")
    parser.add_argument("--validar", metavar="CODIGO", help="Validar un codigo existente")
    args = parser.parse_args()

    if args.lista:
        registro = cargar_registro()
        if not registro:
            print("No hay licencias emitidas.")
            return
        print(f"\n{'─'*70}")
        print(f"{'NOMBRE':<25} {'EMAIL':<30} {'VENCE':<12} {'EMITIDA'}")
        print(f"{'─'*70}")
        for lic in registro:
            vence = lic.get('vencimiento', 'Perpetua')
            print(f"{lic['nombre']:<25} {lic['email']:<30} {vence:<12} {lic['emitida']}")
        print(f"{'─'*70}")
        print(f"Total: {len(registro)} licencia(s)\n")
        return

    if args.validar:
        valido, msg = validate_license(args.validar)
        status = "✅ VALIDA" if valido else "❌ INVALIDA"
        print(f"\n{status}: {msg}\n")
        return

    if not args.nombre or not args.email:
        parser.print_help()
        return

    code = generar(args.nombre, args.email, args.vence)

    print(f"""
{'='*60}
  LICENCIA GENERADA — SISFE Monitor
{'='*60}
  Cliente  : {args.nombre}
  Email    : {args.email}
  Vence    : {args.vence or 'Perpetua'}
  Emitida  : {date.today().strftime('%d/%m/%Y')}

  CODIGO:
  {code}
{'='*60}
Guardado en: {REGISTRO}
""")


if __name__ == "__main__":
    main()
