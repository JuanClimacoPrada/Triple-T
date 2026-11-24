"""Adaptación del paquete UI Pro: presentación segura y datos reales, sin fixtures."""
from dataclasses import dataclass, field
from decimal import Decimal
from html import escape
from pathlib import Path
import ipaddress
import math
import os
import re
from urllib.parse import urlsplit
import streamlit as st
from conversacion.gestor import actual, resultado_para
from experiencia.tarjetas import estado_revision
from servicios.finanzas import cronograma
from servicios.proveedores_riesgo import SENTINEL_REFERENCIA

CSS_FILE = Path(__file__).with_name("triple_t_pro_styles.css")


@dataclass(frozen=True)
class MetricCard:
    label: str
    value: str
    subtitle: str = ""
    accent: str = "blue"
    icon: str = "wallet"


@dataclass
class TripleTViewModel:
    status_text: str = "Por comenzar"
    preliminary: bool = True
    current_step: int = 1
    request_cards: list[MetricCard] = field(default_factory=list)
    simulated: bool = False
    metrics: list = field(default_factory=list)
    indicators: list = field(default_factory=list)
    chart_bars: list = field(default_factory=list)
    income_breakdown: list = field(default_factory=list)
    income: Decimal | None = None
    distribution_note: str = "Completa ingresos, gastos y cuotas para ver su distribución."
    sentinel_url: str | None = None
    state_label: str = "Información pendiente"


def sentinel_config(secrets=None):
    url = os.environ.get("SENTINEL_URL")
    if url is None:
        try:
            url = secrets.get("SENTINEL_URL", SENTINEL_REFERENCIA) if secrets is not None else SENTINEL_REFERENCIA
        except Exception:
            url = SENTINEL_REFERENCIA
    return url_segura(url or SENTINEL_REFERENCIA)


def url_segura(url):
    """Solo una URL HTTPS externa fija, sin identidad, parámetros ni fragmentos."""
    if not isinstance(url, str) or not url or len(url) > 2048 or re.search(r'[\s<>"\'{}\\]', url):
        return None
    try:
        p = urlsplit(url)
        if p.scheme != "https" or not p.hostname or p.username or p.password or p.query or p.fragment or p.port not in (None, 443):
            return None
        host = p.hostname.lower()
        if "." not in host or host.endswith((".local", ".localhost")) or not re.fullmatch(r"[a-z0-9.-]+", host):
            return None
        try:
            ipaddress.ip_address(host)
            return None
        except ValueError:
            return url
    except ValueError:
        return None


def dinero(valor):
    if valor is None:
        return "Pendiente"
    return f"{'−' if valor < 0 else ''}S/ {abs(valor):,.2f}"


def tarjetas_solicitud(exp):
    plazo = "Sin registrar" if exp.meses is None else f"{exp.meses} {'mes' if exp.meses == 1 else 'meses'}"
    tea = "Sin registrar" if exp.tea is None else f"{exp.tea:.2f}%"
    return [
        MetricCard("Ingreso mensual declarado", "Sin registrar" if exp.ingreso is None else dinero(exp.ingreso), icon="wallet"),
        MetricCard("Monto solicitado", "Sin registrar" if exp.monto is None else dinero(exp.monto), icon="file"),
        MetricCard("TEA registrada", tea, icon="chart"),
        MetricCard("Plazo solicitado", plazo, icon="layers"),
    ]


def construir_vm(c, sentinel_url=None):
    confirmado = bool(c.flujo and c.flujo.revision_confirmada == c.revision and c.resultado is not None and not c.pendiente)
    exp, r = actual(c) if confirmado else (c.expediente, resultado_para(c, c.expediente))
    vm = TripleTViewModel(preliminary=not confirmado, sentinel_url=url_segura(sentinel_url),
                          request_cards=tarjetas_solicitud(c.expediente), simulated=bool(confirmado and c.escenario))
    etapas = {"INICIO":1, "CONDICIONES":1, "FINANZAS":1, "HISTORIAL":1, "EVIDENCIA_INGRESOS":2,
              "EVIDENCIA_PATRIMONIO":2, "REVISION_DATOS":3, "RESULTADOS":4}
    vm.current_step = 5 if confirmado and c.escenario else etapas.get(c.flujo.etapa if c.flujo else "INICIO", 1)
    vm.status_text = "Revisión confirmada" if confirmado else "Evaluación en curso" if c.flujo and c.flujo.iniciado else "Listo para comenzar"
    cifra = r.cifras
    pago = cifra.get("pago_mensual_total", cifra.get("cuota_base"))
    dti = cifra.get("dti_total")
    ingreso = cifra.get("ingresos_admisibles")
    dti_sin_ingreso = confirmado and dti is None and ingreso == 0
    detalle_pago = "Con los cargos mensuales registrados" if "pago_mensual_total" in cifra else "Capital e interés"
    if pago is None:
        detalle_pago = "Requiere monto, plazo y TEA válidos"
    saldo = cifra.get("saldo_post_cuota")
    estado_dti = "Umbral académico " + f"{c.config.umbral_dti:.0%}"
    color_dti = "blue"
    if confirmado and dti is not None:
        excede = dti > c.config.umbral_dti
        color_dti = "red" if excede else "green"
        estado_dti = (f"Sobreendeudamiento según el umbral académico de {c.config.umbral_dti:.0%}"
                      if excede else f"Dentro del umbral académico de {c.config.umbral_dti:.0%}")
    elif dti_sin_ingreso:
        color_dti = "red"
        estado_dti = "El ingreso admisible es S/ 0"
    color_saldo = "blue"
    estado_saldo = "Después de gastos y cuotas"
    if confirmado and saldo is not None:
        color_saldo = "red" if saldo < 0 else "green" if saldo > 0 else "amber"
        estado_saldo = "Déficit mensual" if saldo < 0 else "Margen mensual positivo" if saldo > 0 else "Sin margen mensual"
    capacidad = cifra.get("capacidad_neta")
    dti_texto = "No calculable" if dti_sin_ingreso else "Pendiente" if dti is None else f"{dti:.1%}"
    vm.metrics = [
        MetricCard("Cuota mensual estimada", dinero(pago), detalle_pago, "blue", "wallet"),
        MetricCard("Capacidad mensual", dinero(capacidad), "Disponible antes del nuevo pago", "cyan", "wallet"),
        MetricCard("Endeudamiento (DTI)", dti_texto, estado_dti, color_dti, "chart"),
        MetricCard("Saldo después del pago", dinero(saldo), estado_saldo, color_saldo, "layers"),
    ]
    pago_total = cifra.get("pago_mensual_total")
    uso = pago_total / capacidad if pago_total is not None and capacidad is not None and capacidad > 0 else None
    margen_dti = (c.config.umbral_dti - dti) * 100 if dti is not None else None
    if uso is None:
        texto_uso = "Sin capacidad disponible" if capacidad == 0 else "Pendiente"
        subtitulo_uso = "Pago mensual relativo a la capacidad neta"
        color_uso = "red" if capacidad == 0 and pago_total and pago_total > 0 else "blue"
    else:
        texto_uso = f"{uso:.1%}"
        subtitulo_uso = "Supera la capacidad neta" if uso > 1 else "Consume toda la capacidad neta" if uso == 1 else "Parte de la capacidad neta que consume el pago"
        color_uso = "red" if uso > 1 else "amber" if uso == 1 else "green"
    if margen_dti is None:
        texto_margen = "No calculable" if dti_sin_ingreso else "Pendiente"
        estado_margen = "El ingreso admisible es S/ 0" if dti_sin_ingreso else "Requiere un DTI calculable"
        color_margen = "red" if dti_sin_ingreso else "blue"
    elif margen_dti == 0:
        texto_margen, estado_margen, color_margen = "0.0 pp", "En el umbral", "amber"
    else:
        negativo = margen_dti < 0
        signo = "−" if negativo else "+"
        texto_margen = f"{signo}{abs(margen_dti):.1f} pp"
        estado_margen = "Por encima del umbral" if negativo else "Por debajo del umbral"
        color_margen = "red" if negativo else "green"
    vm.indicators = [MetricCard("Capacidad utilizada", texto_uso, subtitulo_uso, color_uso, "wallet"),
                     MetricCard("Margen frente al umbral DTI", texto_margen, estado_margen, color_margen, "chart")]
    vm.state_label = estado_revision(c, r)
    if "cuota_base" in cifra:
        # Comparación teórica a la misma tasa: no crea ofertas ni altera el expediente.
        for meses in sorted(set(min(360, exp.meses + incremento) for incremento in (0, 12, 24))):
            cuota, _ = cronograma(exp.monto, meses, exp.tea)
            vm.chart_bars.append((f"{meses} m", float(cuota)))
    ingreso = cifra.get("ingresos_admisibles")
    if ingreso is not None and ingreso > 0:
        partes = [("Gastos habituales", cifra.get("gastos")), ("Otras cuotas", cifra.get("otras_cuotas")),
                  ("Nuevo pago", cifra.get("pago_mensual_total")), ("Disponible", cifra.get("saldo_post_cuota"))]
        vm.income = ingreso
        if all(v is not None and v >= 0 for _,v in partes):
            vm.income_breakdown = [(k, float(v)) for k,v in partes if v > 0]
            vm.distribution_note = "Ingreso admisible calculado; distribución por destino, no por fuente laboral."
        else:
            vm.distribution_note = "Hay déficit mensual. No se representa como una distribución positiva del ingreso."
    return vm


def icon(name):
    paths = {
        "bot": '<rect x="4" y="7" width="16" height="13" rx="5"/><path d="M12 3v4M2 12v4m20-4v4M8 16h8"/><path d="M8 11h.01M16 11h.01"/>',
        "wallet": '<path d="M20 7H5a2 2 0 0 1 0-4h13v4M4 5v14h16V7M20 11h-6v5h6"/>',
        "chart": '<path d="M4 20V11h3v9m4 0V6h3v14m4 0V3h3v17"/>',
        "layers": '<path d="m12 3 10 5-10 5L2 8Zm-10 9 10 5 10-5M2 16l10 5 10-5"/>',
        "file": '<path d="M5 3h10l4 4v14H5ZM14 3v5h5M8 12h8M8 16h8"/>',
        "upload": '<path d="M8 17H5a4 4 0 0 1-1-8 7 7 0 0 1 13-3 5 5 0 0 1 2 11h-3M12 21V9m-4 4 4-4 4 4"/>',
        "user": '<circle cx="12" cy="8" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3"/>',
        "scale": '<path d="M12 3v18m-5 0h10M3 7h18M6 7l-4 8h8Zm12 0-4 8h8Z"/>',
    }
    return '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+paths.get(name,paths["file"])+"</svg>"


def load_styles():
    st.markdown("<style>" + CSS_FILE.read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)


def hero_html(vm):
    return f'<header class="tt-hero"><div class="tt-hero-title">{icon("bot")}<span>Asistente de análisis crediticio<small>Tu evaluación, paso a paso</small></span></div><span class="tt-status"><i></i>{escape(vm.status_text)}</span></header>'


def message_html(role, text):
    rol = "user" if role == "user" else "assistant"
    seguro = escape(str(text)).replace("\n", "<br>")
    seguro = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", seguro)
    return f'<div class="tt-msg {rol}"><span class="tt-avatar">{icon("user" if rol == "user" else "bot")}</span><div class="tt-bubble">{seguro}</div></div>'


def steps_html(vm):
    pasos = ["Datos de la solicitud", "Evidencias de ingresos y patrimonio", "Revisar y confirmar datos", "Resultados del análisis", "Simular y preparar informe"]
    return '<ol class="tt-steps" aria-label="Etapas de evaluación">'+''.join(f'<li class="{"current" if i == vm.current_step else "done" if i < vm.current_step else "pending"}"'+(' aria-current="step"' if i==vm.current_step else '')+f'><span>{"✓" if i < vm.current_step else i}</span>{escape(p)}</li>' for i,p in enumerate(pasos,1))+'</ol>'


def cards_html(cards, *, compactas=False):
    clases = "tt-metrics tt-metrics-compact" if compactas else "tt-metrics"
    partes = []
    for tarjeta in cards:
        color = tarjeta.accent if tarjeta.accent in ("green", "blue", "cyan", "red", "amber") else "blue"
        valor = escape(tarjeta.value).replace("S/ ", "S/&nbsp;")
        subtitulo = f"<small>{escape(tarjeta.subtitle)}</small>" if tarjeta.subtitle else ""
        partes.append(f'<article class="tt-card {color}"><div class="tt-card-label">{icon(tarjeta.icon)}'
                      f'<span>{escape(tarjeta.label)}</span></div><strong>{valor}</strong>{subtitulo}</article>')
    return f'<div class="{clases}">{"".join(partes)}</div>'


def sugerencia_html(texto):
    return ('<aside class="tt-suggestion" aria-label="Sugerencia de Triple-T">'
            f'<span class="tt-suggestion-icon">{icon("bot")}</span>'
            f'<div><strong>Sugerencia de Triple-T</strong><p>{escape(texto)}</p></div></aside>')


def bars_html(data):
    valores = [(str(k),float(v)) for k,v in data if math.isfinite(float(v)) and v >= 0]
    if not valores:
        return '<div class="tt-chart-empty">'+icon("chart")+'<p>Completa las condiciones para comparar cuotas.</p></div>'
    maximo = max(v for _,v in valores) or 1
    return '<div class="tt-bars" role="img" aria-label="Cuota base calculada por plazo">'+''.join(f'<div class="tt-bar-wrap"><strong>S/ {v:,.2f}</strong><div class="tt-bar" style="height:{max(3,round(v/maximo*120))}px"></div><span>{escape(k)}</span></div>' for k,v in valores)+'</div>'


def donut_html(vm):
    colores = ["#1257ce", "#229eed", "#52c8e7", "#ace4ef"]
    if not vm.income_breakdown:
        return '<div class="tt-chart-empty">'+icon("wallet")+'<p>'+escape(vm.distribution_note)+'</p></div>'
    total = sum(v for _,v in vm.income_breakdown)
    posicion = 0
    segmentos, leyenda = [], []
    for i,(label, valor) in enumerate(vm.income_breakdown):
        fin = posicion + valor/total*100
        segmentos.append(f"{colores[i%4]} {posicion:.4f}% {fin:.4f}%")
        leyenda.append(f'<li><i style="background:{colores[i%4]}"></i><span>{escape(label)}</span><strong>{valor/total:.1%}</strong></li>')
        posicion = fin
    return f'<div class="tt-donut" style="background:conic-gradient({",".join(segmentos)})"><div><strong>{escape(dinero(vm.income))}</strong><span>Ingreso admisible</span></div></div><ul class="tt-legend">'+''.join(leyenda)+'</ul>'


def sentinel_link_html(url):
    seguro = url_segura(url)
    return f'<a class="tt-sentinel-link" href="{escape(seguro, quote=True)}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">Consultar portal externo de Sentinel</a>' if seguro else ''


def score_html(url):
    seguro = url_segura(url)
    link = sentinel_link_html(seguro) or '<span class="tt-sentinel-link disabled" aria-disabled="true">Consultar Sentinel</span>'
    return '<div class="tt-score"><div><span>Score crediticio</span><strong>No disponible</strong></div>'+link+'<small>'+('Servicio externo. No se envía información del expediente.' if seguro else 'Consulta externa pendiente de configuración por el responsable.')+'</small></div>'


def section_title(label, name="file"):
    st.markdown('<div class="tt-mini-title">'+icon(name)+escape(label)+'</div>', unsafe_allow_html=True)


def render_dashboard_area(vm, seccion="Resumen"):
    if seccion == "Indicadores":
        section_title("Presión sobre el presupuesto", "chart")
        st.markdown(cards_html(vm.indicators), unsafe_allow_html=True)
        st.caption("La capacidad utilizada compara el nuevo pago mensual con el dinero que quedaba después de gastos y deudas vigentes. El margen DTI se expresa en puntos porcentuales (pp).")
        return
    if seccion == "Gráficos":
        section_title("Cuota por plazo", "chart")
        st.markdown(bars_html(vm.chart_bars), unsafe_allow_html=True)
        st.caption("Mismo monto y TEA. Cuotas base teóricas sin cargos; no son ofertas.")
        section_title("Uso del ingreso", "wallet")
        st.markdown(donut_html(vm), unsafe_allow_html=True)
        return
    section_title("Datos de la solicitud original" if vm.simulated else "Datos de la solicitud", "file")
    st.markdown(cards_html(vm.request_cards, compactas=True), unsafe_allow_html=True)
    section_title("Resultado de la simulación" if vm.simulated else "Resultado mensual", "chart")
    if vm.preliminary:
        st.caption("Los indicadores se completan a medida que registras los datos.")
    st.markdown(cards_html(vm.metrics), unsafe_allow_html=True)
    if not vm.preliminary:
        st.markdown('<div class="tt-review"><span>Estado de la evaluación</span><strong>'+escape(vm.state_label)+'</strong></div>', unsafe_allow_html=True)
