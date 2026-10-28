"""Genera backend/app/data/densidades.json: densidad de los LÍQUIDOS PUROS del catálogo a 20 °C.

Cada valor sale de correlaciones y tablas publicadas que trae la librería `chemicals`, y solo se
guarda si hay AL MENOS DOS fuentes independientes que coinciden:

1. Perry's Chemical Engineers' Handbook, 8.ª ed., tabla 2-105 (líquidos saturados, a 20 °C).
2. VDI Heat Atlas / PPDS (ecuación 2 de densidad de líquidos saturados, a 20 °C).
3. CRC Handbook, densidades de líquidos inorgánicos (un valor constante, a la temperatura de
   la tabla, que ronda los 20-25 °C: por eso la tolerancia es de 1,5 %).

Si una sustancia tiene menos de dos fuentes, o difieren más de TOLERANCIA_REL, NO se guarda:
queda en `sin_datos` y el usuario tiene que informar la densidad en la simulación. No se
completa ningún valor de memoria. Se usa el valor de la primera fuente en el orden de arriba.

Solo líquidos puros. Las soluciones (HCl 37 %, NaOH 50 %...) cambian de densidad con la
concentración: su densidad la informa quien la conoce (etiqueta del frasco, certificado).

Uso (desde backend/):  pip install -e ".[datos]" && python scripts/construir_densidades.py
"""
import json
import sys
from pathlib import Path

from chemicals import volume

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "app" / "data"
T_REF_C = 20.0
TOLERANCIA_REL = 0.015  # 1,5 %


def mol_m3_perry(cas: str, t_k: float) -> float | None:
    """mol/m³ según Perry 2-105: rho = C1 / C2^(1 + (1 - T/C3)^C4) (parámetros de `chemicals`, en mol/m³)."""
    d = volume.rho_data_Perry_8E_105_l
    if cas not in d.index:
        return None
    f = d.loc[cas]
    if not (f["Tmin"] <= t_k <= f["Tmax"]):
        return None
    return float(f["C1"] / f["C2"] ** (1.0 + (1.0 - t_k / f["C3"]) ** f["C4"]))  # el PM se aplica afuera, con el del catálogo


def kg_m3_vdi(cas: str, t_k: float) -> float | None:
    """kg/m³ según VDI PPDS 2."""
    d = volume.rho_data_VDI_PPDS_2
    if cas not in d.index:
        return None
    f = d.loc[cas]
    if t_k >= f["Tc"]:
        return None
    tau = 1.0 - t_k / f["Tc"]
    return float(f["rhoc"] + f["A"] * tau**0.35 + f["B"] * tau ** (2 / 3) + f["C"] * tau + f["D"] * tau ** (4 / 3))


def g_ml_crc(cas: str, pm: float) -> float | None:
    """g/mL a partir del volumen molar constante de la tabla CRC de líquidos inorgánicos."""
    d = volume.rho_data_CRC_inorg_l_const
    if cas not in d.index:
        return None
    return pm / (float(d.loc[cas]["Vm"]) * 1e6)  # Vm en m³/mol -> cm³/mol


def main() -> int:
    volume._load_rho_data()
    with open(DATA / "compuestos.json", encoding="utf-8") as f:
        compuestos = json.load(f)
    t_k = T_REF_C + 273.15
    out: dict[str, dict] = {}
    sin_datos: dict[str, str] = {}
    for c in compuestos:
        if c["fase"] != "líquido" or not c.get("cas") or not c.get("pm_aplicable"):
            continue
        candidatos: dict[str, float] = {}
        mol_m3 = mol_m3_perry(c["cas"], t_k)
        if mol_m3 is not None:
            candidatos["Perry 2-105"] = mol_m3 * c["pm"] / 1e6
        vdi = kg_m3_vdi(c["cas"], t_k)
        if vdi is not None:
            candidatos["VDI PPDS"] = vdi / 1000.0
        crc = g_ml_crc(c["cas"], c["pm"])
        if crc is not None:
            candidatos["CRC (líquidos inorgánicos)"] = crc
        if len(candidatos) < 2:
            sin_datos[c["id"]] = f"menos de dos fuentes ({', '.join(candidatos) or 'ninguna'})"
            continue
        valores = list(candidatos.values())
        dif = (max(valores) - min(valores)) / min(valores)
        if dif > TOLERANCIA_REL:
            detalle = "; ".join(f"{k} {v:.4f}" for k, v in candidatos.items())
            sin_datos[c["id"]] = f"las fuentes no coinciden ({detalle} g/mL; diferencia {dif * 100:.1f} %)"
            continue
        principal, valor = next(iter(candidatos.items()))
        out[c["id"]] = {
            "densidad_g_ml": round(valor, 3),  # las fuentes coinciden a ~0,2 %: más decimales serían falsa precisión
            "temperatura_c": T_REF_C,
            "fuente": f"{principal} (vía librería chemicals)",
            "verificacion_cruzada": "; ".join(f"{k}: {v:.4f} g/mL" for k, v in candidatos.items()) + f" (diferencia máxima {dif * 100:.2f} %)",
        }
    salida = {
        "descripcion": "Densidad de líquidos puros a 20 °C. Soluciones: informar la densidad de la solución.",
        "tolerancia_relativa": TOLERANCIA_REL,
        "densidades": dict(sorted(out.items(), key=lambda kv: kv[0])),
        "sin_datos": sin_datos,
    }
    with open(DATA / "densidades.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"{len(out)} densidades guardadas; {len(sin_datos)} sin datos confiables")
    for k, v in sin_datos.items():
        print(f"  - {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
