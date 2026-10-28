"""Esquemas Pydantic: entrada/salida de la API y datos del catálogo."""
from typing import Literal

from pydantic import BaseModel, Field, model_validator

TipoCompuesto = Literal["reactivo", "catalizador", "excipiente", "solvente", "principio_activo"]
FaseCompuesto = Literal["líquido", "sólido", "gas"]
TipoAlerta = Literal["ok", "warn", "bad", "info"]
AccesoCompuesto = Literal["libre", "controlado"]
UnidadCantidad = Literal["g", "kg", "mg", "mL", "L", "mol", "mmol"]
TipoConcentracion = Literal["p/p", "p/v", "molar"]


# ---------- Tabla periódica ----------
class Elemento(BaseModel):
    numero: int
    simbolo: str
    nombre: str
    nombre_en: str
    masa_atomica: float
    grupo: int | None = None
    periodo: int
    categoria: str
    fase_25c: FaseCompuesto | None = None
    radiactivo: bool = False
    fuente: str = ""


# ---------- Catálogo ----------
class Compuesto(BaseModel):
    id: str
    nombre: str
    rol: str
    tipo: TipoCompuesto
    categoria: str
    fase: FaseCompuesto
    formula: str | None = None
    formula_hill: str | None = None
    cas: str | None = None
    pm: float = Field(ge=0, description="Peso molecular en g/mol (0 si no aplica, p. ej. polímeros)")
    pm_aplicable: bool = True
    smiles: str | None = None
    inchikey: str | None = None
    pubchem_cid: int | None = None
    tm_c: float | None = Field(default=None, description="Punto de fusión en °C")
    tb_c: float | None = Field(default=None, description="Punto de ebullición en °C")
    sinonimos: list[str] = Field(default_factory=list)
    nota: str = ""
    acceso: AccesoCompuesto = "libre"
    regulacion: str | None = None
    verificado: bool = True
    fuente: str = ""


class Especificacion(BaseModel):
    """Un parámetro de una especificación de calidad (p. ej. una línea de una monografía).

    Si `minimo` y `maximo` son nulos, el parámetro existe pero NO tiene límite cargado:
    el programa lo informa como «sin límite» y no lo da por cumplido.
    """

    id: str
    producto: str
    parametro: str
    minimo: float | None = None
    maximo: float | None = None
    unidad: str = ""
    fuente: str = ""
    estado: str = ""
    modelado: bool = Field(default=False, description="True si el modelo lo estima (hoy solo la pureza); el resto se carga como medición")
    tipo: str = ""
    farmacopea: str = ""


# ---------- Reacción y parámetros del modelo ----------
class PesosPuntaje(BaseModel):
    rendimiento: float = 0.35
    pureza: float = 0.45
    balance: float = 0.20


class ParametrosModelo(BaseModel):
    """Parámetros del modelo de rendimiento y calidad.

    Los valores por defecto son los GENÉRICOS del prototipo (sin validar). Una
    reacción puede sobreescribir solo los que tenga fundamentados. Si no define
    `catalizador_ratio_optimo`, el catalizador no penaliza por cantidad.
    """

    catalizador_requerido: bool = False
    catalizador_ratio_optimo: float | None = None
    catalizador_ratio_minimo: float = 0.08
    catalizador_ratio_maximo: float = 0.30
    pendiente_catalizador: float = 0.35
    factor_catalizador_minimo: float = 0.4
    factor_catalizador_ausente: float = 0.5
    rendimiento_base: float = 0.85
    rendimiento_maximo: float = 0.95
    exceso_tolerado: float = 0.1
    exceso_alerta: float = 0.25
    pendiente_exceso: float = 0.3
    factor_exceso_minimo: float = 0.6
    penalizacion_impureza: float = 1.6
    penalizacion_catalizador_pureza: float = 4.0
    pureza_producto_minima: float = 80
    pureza_producto_maxima: float = 99.9
    pureza_especificada_minima: float = 98.5
    pesos_puntaje: PesosPuntaje = Field(default_factory=PesosPuntaje)


class Participante(BaseModel):
    id: str
    coef: int = Field(ge=1, description="Coeficiente estequiométrico")


class ProductoReaccion(Participante):
    principal: bool = False


class Reaccion(BaseModel):
    id: str
    nombre: str
    descripcion: str = ""
    categoria: str = ""
    reactivos: list[Participante]
    productos: list[ProductoReaccion]
    catalizador: str | None = None
    excipiente: str | None = None
    parametros: ParametrosModelo = Field(default_factory=ParametrosModelo)
    fuente: str = ""
    estado_validacion: str = ""

    @model_validator(mode="after")
    def _un_principal(self):
        if sum(1 for p in self.productos if p.principal) != 1:
            raise ValueError(f"La reacción {self.id} debe tener exactamente un producto principal")
        if not self.reactivos:
            raise ValueError(f"La reacción {self.id} no tiene reactivos")
        return self

    @property
    def principal(self) -> ProductoReaccion:
        return next(p for p in self.productos if p.principal)


class ReaccionDetalle(Reaccion):
    """Reacción con datos calculados para mostrarla (ecuación y comprobación de balance)."""

    ecuacion: str = ""
    balanceada: bool = True
    producto: dict | None = None  # producto principal (compatibilidad con la versión anterior de la API)


# ---------- Simulación ----------
class Concentracion(BaseModel):
    """Concentración de una solución del compuesto (el compuesto es el soluto).

    - `p/p`: % en masa (g de soluto cada 100 g de solución). Ej.: HCl 37 %.
    - `p/v`: % masa/volumen (g de soluto cada 100 mL de solución). Necesita la densidad de la solución.
    - `molar`: mol de soluto por litro de solución. Necesita la densidad de la solución.
    """

    tipo: TipoConcentracion
    valor: float = Field(gt=0, le=100_000)


class ComponenteEntrada(BaseModel):
    """Un insumo de la mezcla.

    La cantidad se informa de UNA de dos maneras:
    - `gramos`: masa del material tal como se pesa (forma original de la API).
    - `cantidad` + `unidad`: g, kg, mg, mL, L, mol o mmol. Con mL/L hace falta la densidad
      (la del catálogo para líquidos puros o `densidad_g_ml`). Con mol/mmol se interpretan como
      moles NETOS del compuesto (ya descontadas pureza y concentración).

    `pureza` es la pureza del soluto/compuesto (%). `concentracion` es aparte: describe cuánto
    de la masa del material es el compuesto cuando viene en solución. Son dos datos distintos.
    """

    id: str
    gramos: float | None = Field(default=None, ge=0, le=1_000_000)
    cantidad: float | None = Field(default=None, ge=0, le=1_000_000)
    unidad: UnidadCantidad = "g"
    pureza: float = Field(default=100, ge=0, le=100, description="Pureza del insumo en %")
    concentracion: Concentracion | None = None
    densidad_g_ml: float | None = Field(
        default=None, gt=0, le=25, description="Densidad del material tal como se carga (solución o líquido puro), en g/mL"
    )

    @model_validator(mode="after")
    def _una_sola_cantidad(self):
        if (self.gramos is None) == (self.cantidad is None):
            raise ValueError("Informá la cantidad con `gramos` o con `cantidad` + `unidad` (una sola de las dos)")
        return self


class ParametrosIncertidumbre(BaseModel):
    """Cómo se propaga la incertidumbre de las entradas (simulación de Monte Carlo).

    Los valores por defecto son SUPUESTOS del analista, no datos: reemplazarlos por la
    incertidumbre de la balanza y del certificado de análisis de cada insumo.
    """

    n: int = Field(default=1000, ge=200, le=20_000, description="Cantidad de corridas")
    semilla: int = Field(default=12345, description="Semilla del generador aleatorio (misma semilla, mismo resultado)")
    sd_masa_rel_pct: float = Field(default=0.5, ge=0, le=20, description="Desvío estándar relativo de cada pesada, en %")
    sd_pureza_pts: float = Field(default=0.5, ge=0, le=20, description="Desvío estándar de la pureza de cada insumo, en puntos porcentuales")
    sd_rendimiento_pts: float | None = Field(
        default=None, ge=0, le=50,
        description="Desvío del rendimiento en puntos porcentuales. Si hay réplicas se usa el de las réplicas; si no, y no se informa, queda sin cuantificar.",
    )
    sd_pureza_producto_pts: float | None = Field(
        default=None, ge=0, le=20, description="Desvío de la pureza del producto (puntos porcentuales): error del ensayo o del modelo"
    )


class SimulacionEntrada(BaseModel):
    componentes: list[ComponenteEntrada] = Field(default_factory=list)
    reaccion_id: str = "ibuprofeno-simplificada"
    rendimiento_real_pct: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Rendimiento medido en un ensayo real; si se informa, reemplaza al estimado por el modelo.",
    )
    rendimiento_replicas_pct: list[float] | None = Field(
        default=None, min_length=2, max_length=50,
        description="Rendimientos medidos en varias réplicas: se usa el promedio y el desvío entra en la incertidumbre.",
    )
    pureza_real_pct: float | None = Field(
        default=None, ge=0, le=100, description="Pureza del producto medida (p. ej. por HPLC); reemplaza a la estimada."
    )
    mediciones: dict[str, float] = Field(
        default_factory=dict,
        description="Resultados medidos por id de especificación (p. ej. pérdida por secado). El modelo no estima estos parámetros.",
    )
    incertidumbre: ParametrosIncertidumbre | None = Field(
        default=None, description="Si se informa, la respuesta incluye intervalos (p5–p95) por simulación de Monte Carlo."
    )

    @model_validator(mode="after")
    def _replicas(self):
        if self.rendimiento_replicas_pct is not None:
            if self.rendimiento_real_pct is not None:
                raise ValueError("Informá `rendimiento_real_pct` o `rendimiento_replicas_pct`, no los dos")
            if any(not 0 <= x <= 100 for x in self.rendimiento_replicas_pct):
                raise ValueError("Cada rendimiento de las réplicas tiene que estar entre 0 y 100")
        return self


class Alerta(BaseModel):
    tipo: TipoAlerta
    mensaje: str


class ReactivoResultado(BaseModel):
    id: str
    nombre: str
    coef: int
    gramos_cargados: float
    moles_utiles: float
    exceso_pct: float
    gramos_consumidos: float
    gramos_sobrantes: float
    limitante: bool
    fraccion_soluto: float = 1.0  # fracción de la masa cargada que es el compuesto (1 = sin solvente)


class CargaResuelta(BaseModel):
    """Cómo quedó cada insumo que participa, ya convertido a masa de material (útil para dibujar y auditar)."""

    id: str
    gramos_material: float
    fraccion_soluto: float = 1.0
    moles_netos: float | None = None


class ProductoResultado(BaseModel):
    id: str
    nombre: str
    coef: int
    principal: bool
    pm: float
    gramos_teoricos: float
    gramos_estimados: float


class EvaluacionEspecificacion(BaseModel):
    id: str
    parametro: str
    unidad: str = ""
    minimo: float | None = None
    maximo: float | None = None
    valor: float | None = None
    origen: Literal["modelo", "medido"] | None = None
    estado: Literal["cumple", "no_cumple", "sin_dato", "sin_limite"]
    modelado: bool = False
    fuente: str = ""
    estado_limite: str = ""


class IntervaloMetrica(BaseModel):
    media: float
    sd: float
    p5: float
    p50: float
    p95: float


class Incertidumbre(BaseModel):
    metodo: str
    n: int
    corridas_validas: int
    semilla: int
    supuestos: dict
    incluye_incertidumbre_del_modelo: bool
    rendimiento_pct: IntervaloMetrica
    pureza_producto_pct: IntervaloMetrica
    gramos_estimados: IntervaloMetrica
    puntaje: IntervaloMetrica
    prob_cumple_pureza: float
    notas: list[str] = Field(default_factory=list)


class Resultado(BaseModel):
    puntaje: int = Field(ge=0, le=100)
    categoria: str
    rendimiento_pct: float
    pureza_producto_pct: float
    balance_pct: float
    reactivo_limitante: str
    gramos_teoricos: float
    gramos_estimados: float
    pm_producto: float
    pct_principio_activo: float | None = None
    cumple_pureza: bool
    # --- ampliaciones (la versión anterior de la API no las traía)
    reaccion_id: str = ""
    reaccion_nombre: str = ""
    ecuacion: str = ""
    economia_atomica_pct: float | None = None
    moles_reaccion: float | None = None
    rendimiento_origen: Literal["modelo", "experimental"] = "modelo"
    pureza_origen: Literal["modelo", "experimental"] = "modelo"
    origen: Literal["estimacion", "mixto", "medido"] = "estimacion"
    estado_validacion: str = ""
    reactivos: list[ReactivoResultado] = Field(default_factory=list)
    productos: list[ProductoResultado] = Field(default_factory=list)
    cargas: list[CargaResuelta] = Field(default_factory=list)
    especificaciones: list[EvaluacionEspecificacion] = Field(default_factory=list)
    cumplimiento_especificaciones: Literal["cumple", "no_cumple", "incompleto", "sin_especificaciones"] = "sin_especificaciones"
    incertidumbre: Incertidumbre | None = None


class SimulacionSalida(BaseModel):
    resultado: Resultado | None
    alertas: list[Alerta]


# ---------- Utilidades de cálculo ----------
class EntradaBalanceo(BaseModel):
    reactivos: list[str] = Field(min_length=1, max_length=12)
    productos: list[str] = Field(min_length=1, max_length=12)


class EntradaConversion(BaseModel):
    """Convierte una cantidad de un compuesto entre unidades (masa, volumen, moles)."""

    compuesto_id: str
    cantidad: float = Field(ge=0, le=1_000_000)
    unidad: UnidadCantidad
    a_unidad: UnidadCantidad
    pureza: float = Field(default=100, ge=0, le=100)
    concentracion: Concentracion | None = None
    densidad_g_ml: float | None = Field(default=None, gt=0, le=25)


class EntradaConcentracion(BaseModel):
    """Convierte una concentración entre %p/p, %p/v y molar (hace falta el PM y, salvo desde p/p, la densidad)."""

    concentracion: Concentracion
    compuesto_id: str | None = None
    formula: str | None = Field(default=None, max_length=200)
    densidad_g_ml: float | None = Field(default=None, gt=0, le=25)

    @model_validator(mode="after")
    def _pm(self):
        if (self.compuesto_id is None) == (self.formula is None):
            raise ValueError("Informá `compuesto_id` o `formula` (uno solo)")
        return self
