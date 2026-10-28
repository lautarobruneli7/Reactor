"""Propiedades fisicoquímicas estimadas a partir de la estructura (RDKit).

RDKit es opcional: si no está instalado, las funciones devuelven None y el
resto del motor sigue funcionando. Los valores son ESTIMACIONES calculadas,
no mediciones de laboratorio.
"""
try:
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors

    RDKIT_DISPONIBLE = True
except ImportError:  # pragma: no cover - depende del entorno
    RDKIT_DISPONIBLE = False


def rdkit_disponible() -> bool:
    return RDKIT_DISPONIBLE


def propiedades_moleculares(smiles: str | None) -> dict | None:
    """PM, fórmula, logP (Crippen), TPSA y donantes/aceptores de H."""
    if not RDKIT_DISPONIBLE or not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return {
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "pm": round(Descriptors.MolWt(mol), 2),
        "logp_estimado": round(Crippen.MolLogP(mol), 2),
        "tpsa": round(rdMolDescriptors.CalcTPSA(mol), 2),
        "donantes_h": rdMolDescriptors.CalcNumHBD(mol),
        "aceptores_h": rdMolDescriptors.CalcNumHBA(mol),
        "metodo": "RDKit (estimación por contribución de grupos)",
    }
