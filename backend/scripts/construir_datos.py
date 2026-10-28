"""Construye los datos del catálogo: elementos.json y compuestos.json.

Uso (desde backend/):
    pip install periodictable chemicals
    python -m scripts.construir_datos

Qué hace:
  1. Elementos: toma las 118 masas atómicas de la librería `periodictable`
     (datos NIST) y les agrega nombre en español, grupo, período y categoría.
  2. Compuestos: toma la lista curada de `semilla_catalogo.py` y, para cada
     sustancia, VERIFICA contra la librería `chemicals` (identificadores de
     PubChem y otras bases públicas) que el CAS corresponda a la fórmula
     escrita y que el peso molecular calculado coincida. Si algo no cierra,
     el script se detiene en lugar de guardar un dato dudoso.
  3. Completa SMILES, InChIKey, CID de PubChem y puntos de fusión/ebullición,
     deduce la fase a 25 °C y la contrasta con la que figura en la semilla.

Estas dos librerías solo hacen falta para REGENERAR los datos; la aplicación
corre solo con los JSON ya generados.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import periodictable as pt  # noqa: E402
from chemicals import Tb, Tm  # noqa: E402
from chemicals.identifiers import search_chemical  # noqa: E402

from app.core import formulas  # noqa: E402
from scripts import semilla_catalogo as semilla  # noqa: E402

DATA = ROOT / "app" / "data"

# ---------------------------------------------------------------------------
# 1. Elementos
# ---------------------------------------------------------------------------
NOMBRES_ES = (
    "hidrógeno helio litio berilio boro carbono nitrógeno oxígeno flúor neón sodio magnesio aluminio silicio "
    "fósforo azufre cloro argón potasio calcio escandio titanio vanadio cromo manganeso hierro cobalto níquel "
    "cobre zinc galio germanio arsénico selenio bromo criptón rubidio estroncio itrio circonio niobio molibdeno "
    "tecnecio rutenio rodio paladio plata cadmio indio estaño antimonio telurio yodo xenón cesio bario lantano "
    "cerio praseodimio neodimio prometio samario europio gadolinio terbio disprosio holmio erbio tulio iterbio "
    "lutecio hafnio tantalio wolframio renio osmio iridio platino oro mercurio talio plomo bismuto polonio astato "
    "radón francio radio actinio torio protactinio uranio neptunio plutonio americio curio berkelio californio "
    "einstenio fermio mendelevio nobelio lawrencio rutherfordio dubnio seaborgio bohrio hassio meitnerio "
    "darmstatio roentgenio copernicio nihonio flerovio moscovio livermorio teneso oganesón"
).split()

ALCALINOS = {3, 11, 19, 37, 55, 87}
ALCALINOTERREOS = {4, 12, 20, 38, 56, 88}
METALOIDES = {5, 14, 32, 33, 51, 52}
NO_METALES = {1, 6, 7, 8, 15, 16, 34}
HALOGENOS = {9, 17, 35, 53, 85}
GASES_NOBLES = {2, 10, 18, 36, 54, 86, 118}
POSTRANSICION = {13, 31, 49, 50, 81, 82, 83, 84, 113, 114, 115, 116}
GASES_25C = {1, 2, 7, 8, 9, 10, 17, 18, 36, 54, 86}
LIQUIDOS_25C = {35, 80}
RADIACTIVOS = {43, 61} | set(range(84, 119))


def categoria_elemento(z: int) -> str:
    if z in ALCALINOS:
        return "metal alcalino"
    if z in ALCALINOTERREOS:
        return "metal alcalinotérreo"
    if z in METALOIDES:
        return "metaloide"
    if z in NO_METALES:
        return "no metal"
    if z in HALOGENOS:
        return "halógeno"
    if z in GASES_NOBLES:
        return "gas noble"
    if 57 <= z <= 71:
        return "lantánido"
    if 89 <= z <= 103:
        return "actínido"
    if z in POSTRANSICION:
        return "metal postransicional"
    return "metal de transición"


def periodo(z: int) -> int:
    for p, tope in enumerate((2, 10, 18, 36, 54, 86, 118), start=1):
        if z <= tope:
            return p
    raise ValueError(z)


def grupo(z: int) -> int | None:
    """Grupo IUPAC 1-18 (None en lantánidos y actínidos)."""
    if z == 1:
        return 1
    if z == 2:
        return 18
    if 3 <= z <= 4:
        return z - 2
    if 5 <= z <= 10:
        return z + 8
    if 11 <= z <= 12:
        return z - 10
    if 13 <= z <= 18:
        return z
    if 19 <= z <= 36:
        return z - 18
    if 37 <= z <= 54:
        return z - 36
    if 55 <= z <= 56:
        return z - 54
    if 72 <= z <= 86:
        return z - 68
    if 87 <= z <= 88:
        return z - 86
    if 104 <= z <= 118:
        return z - 100
    return None  # lantánidos (57-71) y actínidos (89-103)


def construir_elementos() -> list[dict]:
    elementos = []
    for z in range(1, 119):
        e = pt.elements[z]
        fase = "gas" if z in GASES_25C else "líquido" if z in LIQUIDOS_25C else ("sólido" if z < 104 else None)
        elementos.append({
            "numero": z,
            "simbolo": e.symbol,
            "nombre": NOMBRES_ES[z - 1].capitalize(),
            "nombre_en": e.name,
            "masa_atomica": float(e.mass),
            "grupo": grupo(z),
            "periodo": periodo(z),
            "categoria": categoria_elemento(z),
            "fase_25c": fase,
            "radiactivo": z in RADIACTIVOS,
            "fuente": "NIST (librería periodictable). En elementos sin isótopo estable es la masa del isótopo más estable conocido.",
        })
    return elementos


# ---------------------------------------------------------------------------
# 2. Compuestos
# ---------------------------------------------------------------------------
def cas_texto(n: int) -> str:
    """La librería guarda el CAS como entero (64175); lo llevamos a '64-17-5'."""
    t = str(n)
    return f"{t[:-3]}-{t[-3:-1]}-{t[-1]}"


def fase_calculada(tm_c: float | None, tb_c: float | None) -> str | None:
    if tm_c is not None and tm_c > 25:
        return "sólido"
    if tb_c is not None and tb_c < 25:
        return "gas"
    if tm_c is not None and tb_c is not None:
        return "líquido"
    return None


def construir_compuestos() -> tuple[list[dict], list[str]]:
    registros, problemas = [], []
    ids, cas_vistos = set(), set()
    for id_, nombre, cas, formula, categoria, tipo, rol, fase, extras in semilla.COMPUESTOS:
        if id_ in ids:
            problemas.append(f"{id_}: id repetido")
        if cas in cas_vistos:
            problemas.append(f"{id_}: CAS repetido ({cas})")
        ids.add(id_)
        cas_vistos.add(cas)
        if categoria not in semilla.CATEGORIAS:
            problemas.append(f"{id_}: categoría desconocida {categoria!r}")

        polimero = extras.get("pm_aplicable") is False
        meta = None
        if not polimero:  # los polímeros no tienen un registro único que verificar
            try:
                meta = search_chemical(cas)
            except ValueError:
                meta = None
            if meta is None or cas_texto(meta.CAS) != cas:
                problemas.append(f"{id_}: el CAS {cas} no se encontró en la base pública")
                continue

        pm = None
        verificar = extras.get("verificar", True) and not polimero
        if not polimero:
            pm = round(formulas.peso_molecular(formula), 2)
        if verificar:
            if formulas.composicion(formula) != formulas.composicion(meta.formula):
                problemas.append(
                    f"{id_}: la fórmula {formula} no coincide con la de la base pública ({meta.formula}) para el CAS {cas}"
                )
            if abs(pm - meta.MW) > max(0.06, meta.MW * 4e-4):
                problemas.append(f"{id_}: PM calculado {pm} vs base pública {meta.MW:.2f}")

        tm = None if (polimero or extras.get("sin_tm")) else Tm(cas)
        tb = None if (polimero or extras.get("sin_tb")) else Tb(cas)
        tm_c = None if tm is None else round(tm - 273.15, 1)
        tb_c = None if tb is None else round(tb - 273.15, 1)
        # Limpieza de datos dudosos de la fuente pública:
        #  - si Tb no supera a Tm por un margen razonable, es sublimación o descomposición, no ebullición
        #  - en sólidos orgánicos y en excipientes la "ebullición" casi siempre es descomposición
        if tm_c is not None and tb_c is not None and tb_c - tm_c < 20:
            tb_c = None
        if fase == "sólido" and categoria in ("Principios activos", "Orgánicos", "Excipientes", "Ácidos"):
            tb_c = None
        fase_auto = fase_calculada(tm_c, tb_c)
        if fase_auto and fase_auto != fase and not polimero:
            problemas.append(f"{id_}: fase en la semilla {fase!r} pero Tm={tm_c} °C / Tb={tb_c} °C sugieren {fase_auto!r}")

        regulado = cas in semilla.RENPRE_CAS
        notas = [extras["nota"]] if extras.get("nota") else []
        if cas in semilla.RENPRE_NOTAS_CONCENTRACION:
            notas.append(semilla.RENPRE_NOTAS_CONCENTRACION[cas])
        cid = None if polimero else meta.pubchemid
        fuente = (
            f"CAS {cas}; PubChem CID {cid} (vía librería chemicals); peso molecular calculado con masas atómicas NIST"
            if verificar
            else f"CAS {cas}; polímero sin peso molecular único" if polimero
            else f"CAS {cas}; fórmula y peso molecular calculados, SIN contrastar con la base pública (ver nota)"
        )
        registros.append({
            "id": id_,
            "nombre": nombre,
            "cas": cas,
            "formula": formula,
            "formula_hill": None if polimero else formulas.formula_hill(formulas.composicion(formula)),
            "pm": pm,
            "pm_aplicable": not polimero,
            "verificado": bool(verificar),
            "smiles": None if polimero else (meta.smiles or None),
            "inchikey": None if polimero else (meta.InChI_key or None),
            "pubchem_cid": cid,
            "categoria": categoria,
            "tipo": tipo,
            "rol": rol,
            "fase": fase,
            "tm_c": tm_c,
            "tb_c": tb_c,
            "sinonimos": extras.get("sinonimos", []),
            "nota": " ".join(notas),
            "acceso": "controlado" if regulado else "libre",
            "regulacion": semilla.RENPRE_TEXTO if regulado else None,
            "fuente": fuente,
        })
    return registros, problemas


def main() -> int:
    elementos = construir_elementos()
    with open(DATA / "elementos.json", "w", encoding="utf-8") as f:
        json.dump(elementos, f, ensure_ascii=False, indent=1)
    print(f"elementos.json: {len(elementos)} elementos")

    with open(DATA / "categorias.json", "w", encoding="utf-8") as f:
        json.dump(semilla.CATEGORIAS, f, ensure_ascii=False, indent=1)

    # formulas.py lee elementos.json: hay que invalidar su caché después de escribirlo
    formulas.masas_atomicas.cache_clear()

    compuestos, problemas = construir_compuestos()
    if problemas:
        print("\nPROBLEMAS (no se escribió compuestos.json):")
        for p in problemas:
            print("  -", p)
        return 1
    with open(DATA / "compuestos.json", "w", encoding="utf-8") as f:
        json.dump(compuestos, f, ensure_ascii=False, indent=1)
    controlados = sum(1 for c in compuestos if c["acceso"] == "controlado")
    print(f"compuestos.json: {len(compuestos)} compuestos ({controlados} fiscalizados por el RENPRE)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
