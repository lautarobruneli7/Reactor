"""Lista curada de sustancias del catálogo (la "semilla").

Acá solo se escribe lo que decide una persona: qué sustancias entran, cómo se
llaman en español y en qué categoría van. Todo lo demás (peso molecular,
SMILES, puntos de fusión y ebullición, identificadores) lo calcula o lo trae
`construir_datos.py` de fuentes públicas, y verifica que la fórmula y el CAS
que figuran acá coincidan con esas fuentes. Si no coinciden, el script falla.

POLÍTICA DE INCLUSIÓN (ver docs/politica-de-sustancias.md)
  Entran sustancias de venta y uso legal (laboratorio, industria, farmacia).
  NO entran: estupefacientes y psicotrópicos, explosivos y sus precursores
  directos, agentes de guerra química, material radiactivo o nuclear.
  Las sustancias fiscalizadas por el RENPRE (Argentina) SÍ entran, pero con
  la marca `controlado`, porque hay rutas legítimas que las necesitan (por
  ejemplo, el anhídrido acético en la síntesis de ibuprofeno).
"""

CATEGORIAS = [
    "Principios activos",
    "Orgánicos",
    "Solventes",
    "Ácidos",
    "Bases",
    "Sales y óxidos",
    "Gases",
    "Elementos",
    "Catalizadores",
    "Excipientes",
]

# ---------------------------------------------------------------------------
# Compuestos.  (id, nombre, CAS, fórmula, categoría, tipo, rol, fase, extras)
#   tipo: función habitual: reactivo | catalizador | excipiente | solvente | principio_activo
#   fase: a 25 °C y 1 atm (se contrasta con los puntos de fusión/ebullición)
#   extras: sinonimos=[...], pm_aplicable=False (polímeros), nota="..."
# Los seis primeros conservan los ids del prototipo (ibb, aa, cat, h2, co, exc).
# ---------------------------------------------------------------------------
L, S, G = "líquido", "sólido", "gas"
RX, CAT, EXC, SOL, API = "reactivo", "catalizador", "excipiente", "solvente", "principio_activo"
POLI = {"pm_aplicable": False}

COMPUESTOS = [
    # --- los del prototipo (ids heredados)
    ("ibb", "Isobutilbenceno", "538-93-2", "C10H14", "Orgánicos", RX, "Materia prima", L, {"sinonimos": ["isobutylbenzene", "(2-metilpropil)benceno"]}),
    ("aa", "Anhídrido acético", "108-24-7", "C4H6O3", "Orgánicos", RX, "Agente acetilante", L, {"sinonimos": ["acetic anhydride", "anhídrido etanoico"]}),
    ("cat", "Cloruro de aluminio", "7446-70-0", "AlCl3", "Catalizadores", CAT, "Catalizador", S, {"sinonimos": ["AlCl3", "tricloruro de aluminio"], "sin_tm": True, "nota": "Sublima a unos 180 °C (a presión normal no funde)."}),
    ("h2", "Hidrógeno", "1333-74-0", "H2", "Gases", RX, "Reductor", G, {"sinonimos": ["dihidrógeno", "hydrogen"]}),
    ("co", "Monóxido de carbono", "630-08-0", "CO", "Gases", RX, "Carbonilación", G, {"sinonimos": ["carbon monoxide"], "nota": "Gas tóxico: solo uso en equipos y ámbitos adecuados."}),
    ("exc", "Celulosa", "9004-34-6", "(C6H10O5)n", "Excipientes", EXC, "Formulación", S, {**POLI, "sinonimos": ["cellulose", "celulosa microcristalina"], "nota": "Polímero: no tiene un peso molecular único; la masa se usa solo para el % de principio activo."}),

    # --- principios activos
    ("ibuprofeno", "Ibuprofeno", "15687-27-1", "C13H18O2", "Principios activos", API, "Principio activo", S, {"sinonimos": ["ibuprofen"]}),
    ("paracetamol", "Paracetamol", "103-90-2", "C8H9NO2", "Principios activos", API, "Principio activo", S, {"sinonimos": ["acetaminofén", "acetaminophen"]}),
    ("aspirina", "Ácido acetilsalicílico", "50-78-2", "C9H8O4", "Principios activos", API, "Principio activo", S, {"sinonimos": ["aspirina", "aspirin", "AAS"]}),
    ("naproxeno", "Naproxeno", "22204-53-1", "C14H14O3", "Principios activos", API, "Principio activo", S, {"sinonimos": ["naproxen"]}),
    ("cafeina", "Cafeína", "58-08-2", "C8H10N4O2", "Principios activos", API, "Principio activo", S, {"sinonimos": ["caffeine"]}),
    ("metformina-hcl", "Metformina clorhidrato", "1115-70-4", "C4H11N5·HCl", "Principios activos", API, "Principio activo", S, {"sinonimos": ["metformin hydrochloride"]}),
    ("diclofenac-na", "Diclofenaco sódico", "15307-79-6", "C14H10Cl2NNaO2", "Principios activos", API, "Principio activo", S, {"sinonimos": ["diclofenac sodium"]}),
    ("acido-ascorbico", "Ácido ascórbico", "50-81-7", "C6H8O6", "Principios activos", API, "Principio activo (vitamina C)", S, {"sinonimos": ["vitamina C", "ascorbic acid"]}),

    # --- orgánicos (materias primas y reactivos)
    ("acido-salicilico", "Ácido salicílico", "69-72-7", "C7H6O3", "Orgánicos", RX, "Materia prima", S, {"sinonimos": ["salicylic acid", "ácido 2-hidroxibenzoico"]}),
    ("4-aminofenol", "4-Aminofenol", "123-30-8", "C6H7NO", "Orgánicos", RX, "Materia prima", S, {"sinonimos": ["p-aminofenol", "4-aminophenol"]}),
    ("fenol", "Fenol", "108-95-2", "C6H6O", "Orgánicos", RX, "Materia prima", S, {"sinonimos": ["phenol"], "nota": "Corrosivo y tóxico."}),
    ("anilina", "Anilina", "62-53-3", "C6H7N", "Orgánicos", RX, "Materia prima", L, {"sinonimos": ["aniline", "fenilamina"], "nota": "Tóxica."}),
    ("benzaldehido", "Benzaldehído", "100-52-7", "C7H6O", "Orgánicos", RX, "Materia prima", L, {"sinonimos": ["benzaldehyde"]}),
    ("glucosa", "Glucosa", "50-99-7", "C6H12O6", "Orgánicos", RX, "Materia prima", S, {"sinonimos": ["dextrosa", "glucose"]}),
    ("urea", "Urea", "57-13-6", "CH4N2O", "Orgánicos", RX, "Materia prima", S, {"sinonimos": ["urea", "carbamida"]}),
    ("formaldehido", "Formaldehído", "50-00-0", "CH2O", "Orgánicos", RX, "Materia prima", G, {"sinonimos": ["formaldehyde", "metanal"], "nota": "Tóxico y carcinógeno; se usa en solución (formol)."}),
    ("acetaldehido", "Acetaldehído", "75-07-0", "C2H4O", "Orgánicos", RX, "Materia prima", G, {"sinonimos": ["acetaldehyde", "etanal"], "nota": "Hierve a unos 21 °C: se maneja refrigerado, como líquido."}),
    ("acetato-sodio", "Acetato de sodio", "127-09-3", "C2H3NaO2", "Orgánicos", RX, "Reactivo", S, {"sinonimos": ["sodium acetate"]}),
    ("trietilamina", "Trietilamina", "121-44-8", "C6H15N", "Orgánicos", RX, "Base orgánica", L, {"sinonimos": ["triethylamine"]}),
    ("piridina", "Piridina", "110-86-1", "C5H5N", "Orgánicos", RX, "Base orgánica", L, {"sinonimos": ["pyridine"], "nota": "Inflamable, nociva."}),

    # --- solventes
    ("agua", "Agua", "7732-18-5", "H2O", "Solventes", SOL, "Solvente", L, {"sinonimos": ["water", "H2O"]}),
    ("etanol", "Etanol", "64-17-5", "C2H6O", "Solventes", SOL, "Solvente", L, {"sinonimos": ["alcohol etílico", "ethanol", "EtOH"]}),
    ("metanol", "Metanol", "67-56-1", "CH4O", "Solventes", SOL, "Solvente", L, {"sinonimos": ["alcohol metílico", "methanol", "MeOH"], "nota": "Tóxico."}),
    ("isopropanol", "Isopropanol", "67-63-0", "C3H8O", "Solventes", SOL, "Solvente", L, {"sinonimos": ["alcohol isopropílico", "2-propanol", "IPA"]}),
    ("1-butanol", "1-Butanol", "71-36-3", "C4H10O", "Solventes", SOL, "Solvente", L, {"sinonimos": ["n-butanol", "alcohol butílico"]}),
    ("acetona", "Acetona", "67-64-1", "C3H6O", "Solventes", SOL, "Solvente", L, {"sinonimos": ["acetone", "propanona"]}),
    ("mek", "Metiletilcetona", "78-93-3", "C4H8O", "Solventes", SOL, "Solvente", L, {"sinonimos": ["MEK", "2-butanona", "butanone"]}),
    ("mibk", "Metilisobutilcetona", "108-10-1", "C6H12O", "Solventes", SOL, "Solvente", L, {"sinonimos": ["MIBK", "4-metil-2-pentanona"]}),
    ("acetato-etilo", "Acetato de etilo", "141-78-6", "C4H8O2", "Solventes", SOL, "Solvente", L, {"sinonimos": ["ethyl acetate", "etanoato de etilo"]}),
    ("hexano", "Hexano", "110-54-3", "C6H14", "Solventes", SOL, "Solvente", L, {"sinonimos": ["n-hexano", "hexane"]}),
    ("ciclohexano", "Ciclohexano", "110-82-7", "C6H12", "Solventes", SOL, "Solvente", L, {"sinonimos": ["cyclohexane"]}),
    ("tolueno", "Tolueno", "108-88-3", "C7H8", "Solventes", SOL, "Solvente", L, {"sinonimos": ["toluene", "metilbenceno"]}),
    ("p-xileno", "p-Xileno", "106-42-3", "C8H10", "Solventes", SOL, "Solvente", L, {"sinonimos": ["xileno", "xilenos", "para-xilol", "p-xylene", "1,4-dimetilbenceno"], "nota": "Los xilenos (todos los isómeros) están fiscalizados por el RENPRE."}),
    ("diclorometano", "Diclorometano", "75-09-2", "CH2Cl2", "Solventes", SOL, "Solvente", L, {"sinonimos": ["cloruro de metileno", "DCM", "methylene chloride"]}),
    ("cloroformo", "Cloroformo", "67-66-3", "CHCl3", "Solventes", SOL, "Solvente", L, {"sinonimos": ["chloroform", "triclorometano"]}),
    ("eter-etilico", "Éter etílico", "60-29-7", "C4H10O", "Solventes", SOL, "Solvente", L, {"sinonimos": ["dietil éter", "diethyl ether"], "nota": "Muy inflamable; forma peróxidos."}),
    ("thf", "Tetrahidrofurano", "109-99-9", "C4H8O", "Solventes", SOL, "Solvente", L, {"sinonimos": ["THF"], "nota": "Forma peróxidos al almacenarse."}),
    ("acetonitrilo", "Acetonitrilo", "75-05-8", "C2H3N", "Solventes", SOL, "Solvente", L, {"sinonimos": ["acetonitrile", "ACN"]}),
    ("dmso", "Dimetilsulfóxido", "67-68-5", "C2H6OS", "Solventes", SOL, "Solvente", L, {"sinonimos": ["DMSO"]}),
    ("dmf", "N,N-Dimetilformamida", "68-12-2", "C3H7NO", "Solventes", SOL, "Solvente", L, {"sinonimos": ["DMF"]}),
    ("glicerol", "Glicerol", "56-81-5", "C3H8O3", "Solventes", SOL, "Solvente / humectante", L, {"sinonimos": ["glicerina", "glycerol"]}),
    ("propilenglicol", "Propilenglicol", "57-55-6", "C3H8O2", "Solventes", SOL, "Solvente / excipiente", L, {"sinonimos": ["1,2-propanodiol", "propylene glycol"]}),

    # --- ácidos
    ("hcl", "Ácido clorhídrico", "7647-01-0", "HCl", "Ácidos", RX, "Ácido", G, {"sinonimos": ["cloruro de hidrógeno", "hydrochloric acid", "HCl"], "nota": "En la práctica se usa en solución acuosa (la 'pureza' es la concentración)."}),
    ("h2so4", "Ácido sulfúrico", "7664-93-9", "H2SO4", "Ácidos", RX, "Ácido / catalizador ácido", L, {"sinonimos": ["sulfuric acid", "H2SO4"], "nota": "Muy corrosivo.", "sin_tm": True}),
    ("h3po4", "Ácido fosfórico", "7664-38-2", "H3PO4", "Ácidos", RX, "Ácido", S, {"sinonimos": ["phosphoric acid", "H3PO4"], "nota": "Se vende en solución acuosa.", "sin_tm": True}),
    ("acido-acetico", "Ácido acético", "64-19-7", "C2H4O2", "Ácidos", RX, "Ácido", L, {"sinonimos": ["acetic acid", "ácido etanoico", "CH3COOH"]}),
    ("acido-formico", "Ácido fórmico", "64-18-6", "CH2O2", "Ácidos", RX, "Ácido", L, {"sinonimos": ["formic acid", "ácido metanoico"]}),
    ("acido-citrico", "Ácido cítrico", "77-92-9", "C6H8O7", "Ácidos", RX, "Ácido", S, {"sinonimos": ["citric acid"]}),
    ("acido-lactico", "Ácido láctico", "50-21-5", "C3H6O3", "Ácidos", RX, "Ácido", L, {"sinonimos": ["lactic acid"]}),
    ("acido-oxalico", "Ácido oxálico", "144-62-7", "C2H2O4", "Ácidos", RX, "Ácido", S, {"sinonimos": ["oxalic acid"], "nota": "Tóxico."}),
    ("acido-benzoico", "Ácido benzoico", "65-85-0", "C7H6O2", "Ácidos", RX, "Ácido", S, {"sinonimos": ["benzoic acid"]}),
    ("acido-tartarico", "Ácido tartárico", "87-69-4", "C4H6O6", "Ácidos", RX, "Ácido", S, {"sinonimos": ["tartaric acid"]}),
    ("acido-borico", "Ácido bórico", "10043-35-3", "H3BO3", "Ácidos", RX, "Ácido", S, {"sinonimos": ["boric acid"]}),

    # --- bases
    ("naoh", "Hidróxido de sodio", "1310-73-2", "NaOH", "Bases", RX, "Base", S, {"sinonimos": ["soda cáustica", "sodium hydroxide", "NaOH"], "nota": "Corrosivo."}),
    ("koh", "Hidróxido de potasio", "1310-58-3", "KOH", "Bases", RX, "Base", S, {"sinonimos": ["potassium hydroxide", "KOH"], "nota": "Corrosivo."}),
    ("nh3", "Amoníaco", "7664-41-7", "NH3", "Bases", RX, "Base", G, {"sinonimos": ["ammonia", "NH3"], "nota": "En la práctica se usa en solución acuosa (la 'pureza' es la concentración)."}),
    ("caoh2", "Hidróxido de calcio", "1305-62-0", "Ca(OH)2", "Bases", RX, "Base", S, {"sinonimos": ["cal apagada", "calcium hydroxide"], "sin_tm": True}),
    ("mgoh2", "Hidróxido de magnesio", "1309-42-8", "Mg(OH)2", "Bases", RX, "Base", S, {"sinonimos": ["leche de magnesia", "magnesium hydroxide"], "sin_tm": True}),

    # --- sales y óxidos
    ("nacl", "Cloruro de sodio", "7647-14-5", "NaCl", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["sal común", "sodium chloride"]}),
    ("kcl", "Cloruro de potasio", "7447-40-7", "KCl", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["potassium chloride"]}),
    ("cacl2", "Cloruro de calcio", "10043-52-4", "CaCl2", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["calcium chloride"]}),
    ("mgcl2", "Cloruro de magnesio", "7786-30-3", "MgCl2", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["magnesium chloride"]}),
    ("zncl2", "Cloruro de zinc", "7646-85-7", "ZnCl2", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["zinc chloride"], "nota": "Corrosivo."}),
    ("fecl3", "Cloruro férrico", "7705-08-0", "FeCl3", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["cloruro de hierro(III)", "ferric chloride"]}),
    ("na2so4", "Sulfato de sodio", "7757-82-6", "Na2SO4", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["sodium sulfate"]}),
    ("mgso4", "Sulfato de magnesio", "7487-88-9", "MgSO4", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["sal de Epsom (heptahidrato)", "magnesium sulfate"], "sin_tm": True}),
    ("k2so4", "Sulfato de potasio", "7778-80-5", "K2SO4", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["potassium sulfate"]}),
    ("cuso4-5h2o", "Sulfato de cobre(II) pentahidratado", "7758-99-8", "CuSO4·5H2O", "Sales y óxidos", RX, "Sal hidratada", S, {"sinonimos": ["vitriolo azul", "copper sulfate pentahydrate"], "sin_tm": True}),
    ("feso4-7h2o", "Sulfato de hierro(II) heptahidratado", "7782-63-0", "FeSO4·7H2O", "Sales y óxidos", RX, "Sal hidratada", S, {"sinonimos": ["sulfato ferroso", "ferrous sulfate heptahydrate"], "sin_tm": True}),
    ("nahco3", "Bicarbonato de sodio", "144-55-8", "NaHCO3", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["hidrogenocarbonato de sodio", "sodium bicarbonate"], "sin_tm": True}),
    ("na2co3", "Carbonato de sodio", "497-19-8", "Na2CO3", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["soda Solvay", "sodium carbonate"]}),
    ("k2co3", "Carbonato de potasio", "584-08-7", "K2CO3", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["potassium carbonate"]}),
    ("caco3", "Carbonato de calcio", "471-34-1", "CaCO3", "Sales y óxidos", RX, "Sal", S, {"sinonimos": ["calcium carbonate", "caliza"], "sin_tm": True}),
    ("kmno4", "Permanganato de potasio", "7722-64-7", "KMnO4", "Sales y óxidos", RX, "Oxidante", S, {"sinonimos": ["potassium permanganate"], "nota": "Oxidante fuerte.", "sin_tm": True}),
    ("h2o2", "Peróxido de hidrógeno", "7722-84-1", "H2O2", "Sales y óxidos", RX, "Oxidante", L, {"sinonimos": ["agua oxigenada", "hydrogen peroxide"], "nota": "Se usa en solución; las concentradas son oxidantes peligrosos."}),
    ("cao", "Óxido de calcio", "1305-78-8", "CaO", "Sales y óxidos", RX, "Óxido básico", S, {"sinonimos": ["cal viva", "calcium oxide"], "nota": "Reacciona con el agua desprendiendo calor."}),
    ("cuo", "Óxido de cobre(II)", "1317-38-0", "CuO", "Sales y óxidos", RX, "Óxido", S, {"sinonimos": ["copper(II) oxide"], "sin_tm": True}),
    ("zno", "Óxido de zinc", "1314-13-2", "ZnO", "Sales y óxidos", RX, "Óxido", S, {"sinonimos": ["zinc oxide"]}),
    ("fe2o3", "Óxido de hierro(III)", "1309-37-1", "Fe2O3", "Sales y óxidos", RX, "Óxido", S, {"sinonimos": ["hematita", "iron(III) oxide"]}),

    # --- gases
    ("n2", "Nitrógeno", "7727-37-9", "N2", "Gases", RX, "Gas", G, {"sinonimos": ["dinitrógeno", "nitrogen"]}),
    ("o2", "Oxígeno", "7782-44-7", "O2", "Gases", RX, "Oxidante", G, {"sinonimos": ["dioxígeno", "oxygen"]}),
    ("co2", "Dióxido de carbono", "124-38-9", "CO2", "Gases", RX, "Gas", G, {"sinonimos": ["anhídrido carbónico", "carbon dioxide"]}),
    ("cl2", "Cloro", "7782-50-5", "Cl2", "Gases", RX, "Halógeno", G, {"sinonimos": ["dicloro", "chlorine"], "nota": "Gas tóxico: solo uso en equipos y ámbitos adecuados."}),
    ("metano", "Metano", "74-82-8", "CH4", "Gases", RX, "Combustible", G, {"sinonimos": ["methane"]}),
    ("etano", "Etano", "74-84-0", "C2H6", "Gases", RX, "Combustible", G, {"sinonimos": ["ethane"]}),
    ("propano", "Propano", "74-98-6", "C3H8", "Gases", RX, "Combustible", G, {"sinonimos": ["propane"]}),
    ("butano", "Butano", "106-97-8", "C4H10", "Gases", RX, "Combustible", G, {"sinonimos": ["n-butano", "butane"]}),
    ("etileno", "Etileno", "74-85-1", "C2H4", "Gases", RX, "Materia prima", G, {"sinonimos": ["eteno", "ethylene"]}),
    ("helio", "Helio", "7440-59-7", "He", "Gases", RX, "Gas inerte", G, {"sinonimos": ["helium"]}),
    ("neon", "Neón", "7440-01-9", "Ne", "Gases", RX, "Gas inerte", G, {"sinonimos": ["neon"]}),
    ("argon", "Argón", "7440-37-1", "Ar", "Gases", RX, "Gas inerte", G, {"sinonimos": ["argon"]}),

    # --- elementos (sustancias elementales de uso común, no radiactivas)
    ("litio", "Litio", "7439-93-2", "Li", "Elementos", RX, "Metal", S, {"sinonimos": ["lithium"], "nota": "Metal alcalino: reacciona con el agua."}),
    ("sodio", "Sodio", "7440-23-5", "Na", "Elementos", RX, "Metal", S, {"sinonimos": ["sodium"], "nota": "Metal alcalino: reacciona violentamente con el agua."}),
    ("potasio", "Potasio", "7440-09-7", "K", "Elementos", RX, "Metal", S, {"sinonimos": ["potassium"], "nota": "Metal alcalino: reacciona violentamente con el agua."}),
    ("magnesio", "Magnesio", "7439-95-4", "Mg", "Elementos", RX, "Metal", S, {"sinonimos": ["magnesium"]}),
    ("calcio", "Calcio", "7440-70-2", "Ca", "Elementos", RX, "Metal", S, {"sinonimos": ["calcium"]}),
    ("aluminio", "Aluminio", "7429-90-5", "Al", "Elementos", RX, "Metal", S, {"sinonimos": ["aluminum", "aluminium"]}),
    ("silicio", "Silicio", "7440-21-3", "Si", "Elementos", RX, "Metaloide", S, {"sinonimos": ["silicon"]}),
    ("carbono", "Carbono (grafito)", "7440-44-0", "C", "Elementos", RX, "No metal", S, {"sinonimos": ["grafito", "carbon", "graphite"], "sin_tm": True, "sin_tb": True}),
    ("azufre", "Azufre", "7704-34-9", "S", "Elementos", RX, "No metal", S, {"sinonimos": ["sulfur"], "sin_tm": True}),
    ("bromo", "Bromo", "7726-95-6", "Br2", "Elementos", RX, "Halógeno", L, {"sinonimos": ["dibromo", "bromine"], "nota": "Líquido volátil, tóxico y corrosivo."}),
    ("cromo", "Cromo", "7440-47-3", "Cr", "Elementos", RX, "Metal", S, {"sinonimos": ["chromium"]}),
    ("manganeso", "Manganeso", "7439-96-5", "Mn", "Elementos", RX, "Metal", S, {"sinonimos": ["manganese"]}),
    ("hierro", "Hierro", "7439-89-6", "Fe", "Elementos", RX, "Metal", S, {"sinonimos": ["iron"]}),
    ("cobalto", "Cobalto", "7440-48-4", "Co", "Elementos", RX, "Metal", S, {"sinonimos": ["cobalt"]}),
    ("niquel", "Níquel", "7440-02-0", "Ni", "Elementos", RX, "Metal", S, {"sinonimos": ["nickel", "níquel Raney"]}),
    ("cobre", "Cobre", "7440-50-8", "Cu", "Elementos", RX, "Metal", S, {"sinonimos": ["copper"]}),
    ("zinc", "Zinc", "7440-66-6", "Zn", "Elementos", RX, "Metal", S, {"sinonimos": ["cinc", "zinc"]}),
    ("plata", "Plata", "7440-22-4", "Ag", "Elementos", RX, "Metal", S, {"sinonimos": ["silver"]}),
    ("estano", "Estaño", "7440-31-5", "Sn", "Elementos", RX, "Metal", S, {"sinonimos": ["tin"]}),
    ("oro", "Oro", "7440-57-5", "Au", "Elementos", RX, "Metal", S, {"sinonimos": ["gold"]}),
    ("titanio", "Titanio", "7440-32-6", "Ti", "Elementos", RX, "Metal", S, {"sinonimos": ["titanium"]}),

    # --- catalizadores
    ("paladio", "Paladio", "7440-05-3", "Pd", "Catalizadores", CAT, "Catalizador metálico", S, {"sinonimos": ["palladium", "Pd"]}),
    ("platino", "Platino", "7440-06-4", "Pt", "Catalizadores", CAT, "Catalizador metálico", S, {"sinonimos": ["platinum", "Pt"]}),
    ("mno2", "Dióxido de manganeso", "1313-13-9", "MnO2", "Catalizadores", CAT, "Catalizador / oxidante", S, {"sinonimos": ["óxido de manganeso(IV)", "manganese dioxide"], "sin_tm": True}),
    ("ptsoh", "Ácido p-toluensulfónico monohidratado", "6192-52-5", "C7H8O3S·H2O", "Catalizadores", CAT, "Catalizador ácido", S, {"sinonimos": ["PTSA", "tosilato ácido", "p-toluenesulfonic acid monohydrate"]}),

    # --- excipientes
    ("almidon", "Almidón", "9005-25-8", "(C6H10O5)n", "Excipientes", EXC, "Excipiente (diluyente / disgregante)", S, {**POLI, "sinonimos": ["starch"], "nota": "Polímero: sin peso molecular único."}),
    ("lactosa", "Lactosa monohidratada", "64044-51-5", "C12H22O11·H2O", "Excipientes", EXC, "Excipiente (diluyente)", S, {"sinonimos": ["lactose monohydrate"]}),
    ("sacarosa", "Sacarosa", "57-50-1", "C12H22O11", "Excipientes", EXC, "Excipiente / edulcorante", S, {"sinonimos": ["azúcar", "sucrose"]}),
    ("manitol", "Manitol", "69-65-8", "C6H14O6", "Excipientes", EXC, "Excipiente (diluyente)", S, {"sinonimos": ["mannitol"]}),
    ("sorbitol", "Sorbitol", "50-70-4", "C6H14O6", "Excipientes", EXC, "Excipiente / edulcorante", S, {"sinonimos": ["sorbitol"]}),
    ("estearato-mg", "Estearato de magnesio", "557-04-0", "C36H70MgO4", "Excipientes", EXC, "Excipiente (lubricante)", S, {"sinonimos": ["magnesium stearate"]}),
    ("sio2", "Dióxido de silicio", "7631-86-9", "SiO2", "Excipientes", EXC, "Excipiente (antiaglomerante)", S, {"sinonimos": ["sílice", "silica", "silicon dioxide"], "sin_tm": True}),
    ("tio2", "Dióxido de titanio", "13463-67-7", "TiO2", "Excipientes", EXC, "Excipiente (opacificante)", S, {"sinonimos": ["titanium dioxide"]}),
    ("talco", "Talco", "14807-96-6", "Mg3Si4O10(OH)2", "Excipientes", EXC, "Excipiente (deslizante)", S, {"sinonimos": ["talc"], "verificar": False, "nota": "La base pública lista una fórmula simplificada; se usa la del mineral (silicato de magnesio hidratado).", "sin_tm": True}),
    ("fosfato-dicalcico", "Fosfato dicálcico", "7757-93-9", "CaHPO4", "Excipientes", EXC, "Excipiente (diluyente)", S, {"sinonimos": ["hidrogenofosfato de calcio", "dibasic calcium phosphate"]}),
    ("povidona", "Povidona", "9003-39-8", "(C6H9NO)n", "Excipientes", EXC, "Excipiente (aglutinante)", S, {**POLI, "sinonimos": ["PVP", "polivinilpirrolidona"], "nota": "Polímero: sin peso molecular único."}),
]

# ---------------------------------------------------------------------------
# Sustancias fiscalizadas por el RENPRE (Argentina, Ley 26.045 y Decreto 593/2019
# y modificatorios). Solo se marcan las que se pudieron comprobar en fuentes:
#   - certificado de inscripción RENPRE publicado por INCAPE-CONICET (listas 1 y 2)
#   - Marval O'Farrell Mairal, 23/04/2026, sobre el Decreto 128/2026 (lista III)
# La ausencia de marca NO garantiza que una sustancia no esté fiscalizada:
# siempre hay que consultar el Anexo II vigente.
# ---------------------------------------------------------------------------
RENPRE_CAS = {
    "67-64-1", "7647-01-0", "7664-93-9", "108-24-7", "100-52-7", "67-66-3", "75-09-2",
    "60-29-7", "78-93-3", "7722-64-7", "108-88-3",                     # certificado, lista 1
    "141-78-6", "64-19-7", "7664-41-7", "584-08-7", "497-19-8", "110-54-3",
    "1310-58-3", "1310-73-2", "108-10-1", "7757-82-6",
    "106-42-3",                                                        # xilenos (isómero para)    # certificado, lista 2
    "110-82-7",                                                        # Decreto 128/2026 (lista III)
}
RENPRE_TEXTO = (
    "Sustancia fiscalizada por el RENPRE (Ley 26.045, Decreto 593/2019 y modificatorios): "
    "operar con ella en Argentina requiere inscripción o inventario según la lista. "
    "Verificar la lista y el umbral vigentes en el Anexo II."
)
RENPRE_NOTAS_CONCENTRACION = {
    "7647-01-0": "El ácido clorhídrico en solución acuosa se fiscaliza por encima del 20 % p/v.",
    "7664-41-7": "El amoníaco en solución acuosa se fiscaliza por encima del 20 % p/v.",
}
