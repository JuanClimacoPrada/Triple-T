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
from experiencia.evidencia import pendientes_documentales
from experiencia.flujo import faltan
from servicios.finanzas import cronograma

CSS_FILE = Path(__file__).with_name("triple_t_pro_styles.css")


@dataclass(frozen=True)
class MetricCard:
    label: str
    value: str
    subtitle: str = ""
    accent: str = "blue"
    icon: str = "wallet"


@dataclass(frozen=True)
class ComparisonOption:
    opcion: str
    tea: str
    plazo: str
    cuota: str
    selected: bool = False


@dataclass
class TripleTViewModel:
    status_text: str = "Por comenzar"
    preliminary: bool = True
    current_step: int = 1
    metrics: list = field(default_factory=list)
    comparison_rows: list = field(default_factory=list)
    chart_bars: list = field(default_factory=list)
    income_breakdown: list = field(default_factory=list)
    income: Decimal | None = None
    distribution_note: str = "Completa ingresos, gastos y cuotas para ver su distribución."
    documents_note: str = "Respaldo de ingresos pendiente"
    score: str = "No disponible"
    sentinel_url: str | None = None
    state_label: str = "Información pendiente"
    next_fields: list = field(default_factory=list)
    alert: dict | None = None


def sentinel_config(secrets=None):
    url = os.environ.get("SENTINEL_URL")
    if url is None:
        try:
            url = secrets.get("SENTINEL_URL", "") if secrets is not None else ""
        except Exception:
            url = ""
    return url_segura(url)


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
    return "Pendiente" if valor is None else f"S/ {valor:,.2f}"


def construir_vm(c, sentinel_url=None):
    confirmado = bool(c.flujo and c.flujo.revision_confirmada == c.revision and c.resultado is not None)
    exp, r = actual(c) if confirmado else (c.expediente, resultado_para(c, c.expediente))
    vm = TripleTViewModel(preliminary=not confirmado, sentinel_url=url_segura(sentinel_url))
    etapas = {"INICIO":1, "CONDICIONES":1, "FINANZAS":1, "HISTORIAL":1, "EVIDENCIA_INGRESOS":2,
              "EVIDENCIA_PATRIMONIO":2, "REVISION_DATOS":3, "RESULTADOS":4}
    vm.current_step = 5 if confirmado and c.escenario else etapas.get(c.flujo.etapa if c.flujo else "INICIO", 1)
    vm.status_text = "Revisión confirmada" if confirmado else "Evaluación en curso" if c.flujo and c.flujo.iniciado else "Listo para comenzar"
    cifra = r.cifras
    pago = cifra.get("pago_mensual_total", cifra.get("cuota_base"))
    dti = cifra.get("dti_total")
    vm.metrics = [MetricCard("Cuota mensual estimada", dinero(pago), "Incluye cargos declarados" if "pago_mensual_total" in cifra else "Teórica, sin cargos", "green", "wallet"),
        MetricCard("Endeudamiento total", "Pendiente" if dti is None else f"{dti:.1%}", "Cuotas / ingreso admisible", "blue", "chart"),
        MetricCard("Saldo disponible mensual", dinero(cifra.get("saldo_post_cuota")), "Después de gastos y cuotas", "cyan", "layers")]
    vm.documents_note = "; ".join(pendientes_documentales(c)) or "Transcripciones confirmadas · autenticidad no verificada"
    vm.state_label = estado_revision(c, r)
    vm.next_fields = faltan(c) if c.flujo else []
    vm.alert = next((a for a in sorted(r.reglas, key=lambda a: {"discrepancia":0,"relevante":1,"pendiente":2}.get(a["nivel"],3))), None)
    if "cuota_base" in cifra:
        base_r = c.resultado if confirmado else r
        vm.comparison_rows.append(ComparisonOption("Base", f"{c.expediente.tea}%", f"{c.expediente.meses} m", dinero(base_r.cifras.get("cuota_base")), not bool(c.escenario and confirmado)))
        if confirmado and c.escenario:
            vm.comparison_rows.append(ComparisonOption("Escenario", f"{exp.tea}%", f"{exp.meses} m", dinero(cifra.get("cuota_base")), True))
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


def cards_html(cards):
    return '<div class="tt-metrics">'+''.join(f'<article class="tt-card {c.accent if c.accent in ("green","blue","cyan") else "blue"}"><div class="tt-card-label">{icon(c.icon)}<span>{escape(c.label)}</span></div><strong>{escape(c.value)}</strong><small>{escape(c.subtitle)}</small></article>' for c in cards)+'</div>'


def comparison_html(rows):
    if not rows:
        return '<p class="tt-empty">Las condiciones aparecerán al indicar monto, plazo y TEA.</p>'
    return '<table class="tt-table"><thead><tr><th>Opción</th><th>TEA</th><th>Plazo</th><th>Cuota base</th></tr></thead><tbody>'+''.join('<tr'+(' class="selected"' if r.selected else '')+'>'+''.join('<td>'+escape(v)+'</td>' for v in (r.opcion,r.tea,r.plazo,r.cuota))+'</tr>' for r in rows)+'</tbody></table>'


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


def score_html(url):
    seguro = url_segura(url)
    link = f'<a class="tt-sentinel-link" href="{escape(seguro, quote=True)}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">Consultar Sentinel ↗</a>' if seguro else '<span class="tt-sentinel-link disabled" aria-disabled="true">Consultar Sentinel ↗</span>'
    return '<div class="tt-score"><div><span>Score crediticio</span><strong>No disponible</strong></div>'+link+'<small>'+('Servicio externo. No se envía información del expediente.' if seguro else 'Consulta externa pendiente de configuración por el responsable.')+'</small></div>'


def section_title(label, name="file"):
    st.markdown('<div class="tt-mini-title">'+icon(name)+escape(label)+'</div>', unsafe_allow_html=True)


def render_dashboard_area(vm):
    section_title("Resumen del análisis")
    st.caption("Vista preliminar · confirma los datos antes de emitir el análisis" if vm.preliminary else "Resultados del motor · para revisión humana")
    st.markdown(cards_html(vm.metrics), unsafe_allow_html=True)
    st.markdown('<div class="tt-review"><span>Estado de la evaluación</span><strong>'+escape(vm.state_label)+'</strong></div>', unsafe_allow_html=True)
    left,right = st.columns([1.2,1],gap="small")
    with left:
        with st.container(border=True):
            section_title("Comparación de condiciones", "scale")
            st.markdown(comparison_html(vm.comparison_rows), unsafe_allow_html=True)
        with st.container(border=True):
            section_title("Cuota por plazo", "chart")
            st.markdown(bars_html(vm.chart_bars), unsafe_allow_html=True)
            st.caption("Mismo monto y TEA. Cuotas base teóricas sin cargos; no son ofertas.")
    with right:
        with st.container(border=True):
            section_title("Indicadores clave", "chart")
            st.markdown(score_html(vm.sentinel_url), unsafe_allow_html=True)
        with st.container(border=True):
            section_title("Uso del ingreso", "wallet")
            st.markdown(donut_html(vm), unsafe_allow_html=True)
    with st.expander("Documentación pendiente", expanded=False):
        st.write(vm.documents_note)
        st.caption("Presentar o transcribir no verifica autenticidad ni titularidad.")
