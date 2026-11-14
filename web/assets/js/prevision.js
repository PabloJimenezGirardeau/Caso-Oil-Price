// Panel de la previsión: pestañas por plazo, cifras, gráfico de abanico y la tarjeta de la
// previsión en vivo. Regla de la web: ninguna previsión sin su rango del 80 % y sin el ingenuo.
// Lo que aún no existe (la previsión de la red, la previsión en vivo) se muestra como pendiente.

import { nodo, vaciar, medir, escala, linea, banda, marcas, extremos, idUnico, alRedimensionar } from './graficos.js';
import { numero, dolares, porcentaje, fecha, mesAño } from './formato.js';

const ORDEN = ['corto', 'medio', 'largo'];
const NOMBRE = { corto: '1 semana', medio: '3 meses', largo: '1 año' };
const PASADO = { corto: 45, medio: 150, largo: 380 };   // sesiones de historia que se enseñan
const AMBAR = '#f2921d';
const HUESO = '#f4efe6';

/** «10/11» a partir de una fecha ISO */
const diaMes = (iso) => fecha(iso).split('/').slice(0, 2).join('/');

/** Margen de la cobertura en puntos: «1,6» o «16» */
const puntos = (margen) => numero(100 * margen, 100 * margen < 10 ? 1 : 0);

export function iniciarPrevision(d, { reducido }) {
  const pv = d.prevision;
  const { precios } = d.historico;
  const panel = document.getElementById('pv-panel');
  const svg = document.getElementById('pv-grafico');
  const pestañas = [...document.querySelectorAll('#pv-pestanas [role="tab"]')];
  const el = (id) => document.getElementById(id);
  let plazo = 'corto';

  // ---------------------------------------------------------------- cifras
  function cifras() {
    const p = pv.plazos[plazo];
    const medido = d.rango.plazos[plazo];
    el('pv-cuando').textContent = (p.fecha_aproximada ? `hacia ${mesAño(p.fecha_objetivo)}` : `para el ${fecha(p.fecha_objetivo)}`)
      + ` · ${p.sesiones} sesiones`;
    el('pv-orientativo').hidden = !p.orientativo;
    el('pv-bajo').textContent = numero(p.bajo, 2);
    el('pv-alto').textContent = numero(p.alto, 2);
    const abajo = 100 * (p.bajo / pv.precio - 1);
    const arriba = 100 * (p.alto / pv.precio - 1);
    el('pv-ancho').textContent = `De ${numero(abajo, 1)} % a +${numero(arriba, 1)} % sobre el precio de hoy.`;
    el('pv-ingenuo').textContent = dolares(p.ingenuo);
    el('pv-red-nombre').textContent = `${p.red}, la elegida para este plazo`;
    const red = el('pv-red');
    red.classList.toggle('pendiente', p.prevision_red === null);
    red.textContent = p.prevision_red === null ? 'Pendiente · tras el examen final' : dolares(p.prevision_red);
    el('pv-cob-periodo').textContent = `${medido.años[0]}-${medido.años.at(-1)} · debería ser el 80 %`;
    el('pv-cobertura').textContent = `${porcentaje(p.cobertura)} ± ${puntos(p.margen)}`;

    const avisos = [];
    if (p.orientativo) {
      avisos.push(`A ${NOMBRE[plazo]}, el rango ha cubierto el ${porcentaje(p.cobertura)} de las veces, no el 80 %: es orientativo.`);
    }
    if (pv.estado === 'provisional') {
      avisos.push(`Rango provisional: su anchura está ajustada solo con datos hasta el ${fecha(pv.ajuste_hasta)}, para no usar nada del periodo del examen final. El definitivo se publicará junto a la previsión de la red.`);
    }
    const aviso = el('pv-provisional');
    aviso.hidden = avisos.length === 0;
    aviso.textContent = avisos.join(' ');
  }

  // ---------------------------------------------------------------- gráfico
  /** Límite del abanico en la sesión s: pasa por los rangos calculados (5, 63 y 252 sesiones)
      y, entre ellos, se interpola con la raíz del tiempo. Devuelve log(límite / precio). */
  function limite(nudos, s, lado) {
    let a = { s: 0, v: 0 };
    for (const nudo of nudos) {
      const b = { s: nudo.sesiones, v: Math.log(nudo[lado] / pv.precio) };
      if (s <= b.s) return a.v + ((b.v - a.v) * (Math.sqrt(s) - Math.sqrt(a.s))) / (Math.sqrt(b.s) - Math.sqrt(a.s));
      a = b;
    }
    return a.v;
  }

  function grafico() {
    vaciar(svg);
    const { ancho: W, alto: H } = medir(svg);
    if (W < 40) return;
    const p = pv.plazos[plazo];
    const nudos = ORDEN.slice(0, ORDEN.indexOf(plazo) + 1).map((c) => pv.plazos[c]);
    const m = { izq: 6, der: 70, arriba: 18, abajo: 28 };
    const n = precios.length;
    const pasado = precios.slice(n - PASADO[plazo]);
    const xHoy = m.izq + (W - m.izq - m.der) * 0.58;
    const xFin = W - m.der;
    const xPasado = escala(0, pasado.length - 1, m.izq, xHoy);
    const xFuturo = escala(0, p.sesiones, xHoy, xFin);
    let [yMin, yMax] = extremos(pasado, [p.bajo, p.alto]);
    const holgura = (yMax - yMin) * 0.08;
    yMin -= holgura;
    yMax += holgura;
    const y = escala(yMin, yMax, H - m.abajo, m.arriba);

    const idAbanico = idUnico('pv-ab');
    const defs = nodo('defs', {}, svg);
    const g = nodo('linearGradient', { id: idAbanico, gradientUnits: 'userSpaceOnUse', x1: xHoy, x2: xFin, y1: 0, y2: 0 }, defs);
    nodo('stop', { offset: 0, 'stop-color': AMBAR, 'stop-opacity': 0.42 }, g);
    nodo('stop', { offset: 1, 'stop-color': AMBAR, 'stop-opacity': 0.12 }, g);
    const rotulos = nodo('g', {});   // rótulos de los ejes: se añaden al final, encima de las líneas

    // Rejilla y eje de precios
    marcas(yMin, yMax, 4).forEach((v) => {
      nodo('line', { class: 'rejilla', x1: m.izq, x2: xFin, y1: y(v), y2: y(v) }, svg);
      nodo('text', { class: 'eje', x: m.izq, y: y(v) - 6 }, rotulos, numero(v, 0));
    });

    // Hoy: línea vertical y fechas en el eje
    nodo('line', { x1: xHoy, x2: xHoy, y1: m.arriba, y2: H - m.abajo, stroke: HUESO, 'stroke-opacity': 0.22, 'stroke-dasharray': '2 4' }, svg);
    nodo('text', { class: 'eje', x: xHoy, y: H - 8, 'text-anchor': 'middle' }, rotulos, `hoy · ${fecha(pv.fecha)}`);
    nodo('text', { class: 'eje', x: xFin, y: H - 8, 'text-anchor': 'end' }, rotulos,
      p.fecha_aproximada ? `≈ ${mesAño(p.fecha_objetivo)}` : fecha(p.fecha_objetivo));

    // Abanico del 80 %
    const pasos = 48;
    const ss = Array.from({ length: pasos + 1 }, (_, i) => (p.sesiones * i) / pasos);
    const xsF = ss.map(xFuturo);
    const altos = ss.map((s) => y(pv.precio * Math.exp(limite(nudos, s, 'alto'))));
    const bajos = ss.map((s) => y(pv.precio * Math.exp(limite(nudos, s, 'bajo'))));
    nodo('path', { d: banda(xsF, altos, bajos), fill: `url(#${idAbanico})` }, svg);
    const discontinuo = p.orientativo ? '4 4' : null;
    nodo('path', { d: linea(xsF, altos), fill: 'none', stroke: AMBAR, 'stroke-width': 1.2, 'stroke-dasharray': discontinuo }, svg);
    nodo('path', { d: linea(xsF, bajos), fill: 'none', stroke: AMBAR, 'stroke-width': 1.2, 'stroke-dasharray': discontinuo }, svg);
    // El rango en la fecha objetivo
    nodo('line', { x1: xFin, x2: xFin, y1: y(p.alto), y2: y(p.bajo), stroke: AMBAR, 'stroke-width': 2 }, svg);

    // Centro: el ingenuo (el precio de hoy, sin cambios)
    nodo('line', { x1: xHoy, x2: xFin, y1: y(p.ingenuo), y2: y(p.ingenuo), stroke: HUESO, 'stroke-opacity': 0.6, 'stroke-dasharray': '2 5' }, svg);

    // Precio reciente
    nodo('path', { d: linea(pasado.map((_, i) => xPasado(i)), pasado.map(y)), fill: 'none', stroke: HUESO, 'stroke-width': 1.5,
      'stroke-linejoin': 'round' }, svg);
    nodo('circle', { cx: xHoy, cy: y(pv.precio), r: 3.4, fill: AMBAR }, svg);

    // Previsión de la red, cuando exista
    if (p.prevision_red !== null) {
      nodo('circle', { cx: xFin, cy: y(p.prevision_red), r: 4, fill: '#000', stroke: HUESO, 'stroke-width': 1.5 }, svg);
    }

    svg.appendChild(rotulos);
    // Valores a la derecha: alto, ingenuo y bajo (y la red, si no pisa al ingenuo)
    const etiqueta = (valor, color, texto) => nodo('text', { x: xFin + 10, y: y(valor) + 4, fill: color, 'font-size': 11.5 }, svg, texto);
    etiqueta(p.alto, AMBAR, numero(p.alto, 2));
    etiqueta(p.bajo, AMBAR, numero(p.bajo, 2));
    etiqueta(p.ingenuo, '#a39c90', numero(p.ingenuo, 2));
    if (p.prevision_red !== null && Math.abs(y(p.prevision_red) - y(p.ingenuo)) > 14) {
      etiqueta(p.prevision_red, HUESO, numero(p.prevision_red, 2));
    }

    svg.setAttribute('aria-label', `Precio del Brent en las últimas ${pasado.length} sesiones y rango del 80 % a ${NOMBRE[plazo]}: `
      + `de ${dolares(p.bajo)} a ${dolares(p.alto)}, centrado en el precio de hoy, ${dolares(p.ingenuo)}.`);
  }

  // ---------------------------------------------------------------- pestañas
  function elegir(nuevo, enfocar = false) {
    if (nuevo === plazo) return;
    plazo = nuevo;
    pestañas.forEach((t) => {
      const activa = t.dataset.plazo === plazo;
      t.setAttribute('aria-selected', String(activa));
      t.tabIndex = activa ? 0 : -1;
      if (activa) {
        panel.setAttribute('aria-labelledby', t.id);
        if (enfocar) t.focus();
      }
    });
    const cambiar = () => { cifras(); grafico(); panel.classList.remove('cambiando'); };
    if (reducido) { cambiar(); return; }
    panel.classList.add('cambiando');
    setTimeout(cambiar, 230);
  }

  pestañas.forEach((t, i) => {
    t.addEventListener('click', () => elegir(t.dataset.plazo));
    t.addEventListener('keydown', (evento) => {
      const paso = { ArrowRight: 1, ArrowLeft: -1 }[evento.key];
      if (!paso) return;
      evento.preventDefault();
      elegir(pestañas[(i + paso + pestañas.length) % pestañas.length].dataset.plazo, true);
    });
  });

  cifras();
  grafico();
  alRedimensionar(svg.parentElement, grafico);
  previsionEnVivo(d);
}

// -------------------------------------------------------------------- previsión en vivo (D34)
function previsionEnVivo(d) {
  const v = d.en_vivo;
  const tarjeta = document.getElementById('vivo');
  const objetivo = fecha(v.fecha_objetivo);
  const hecha = v.estado !== 'pendiente' && v.bajo !== null && v.alto !== null;
  const comprobada = hecha && v.precio_real !== null && v.precio_real !== undefined;
  const dentro = comprobada && v.precio_real >= v.bajo && v.precio_real <= v.alto;

  // Distintivo del hero, según el estado
  const [etq, resumen] = comprobada
    ? ['Resultado', `Previsión del ${diaMes(v.fecha_objetivo)}: el precio real quedó ${dentro ? 'dentro' : 'fuera'} del rango`]
    : hecha
      ? ['Nuevo', `Previsión del ${diaMes(v.fecha_objetivo)}, guardada antes de descargar el precio`]
      : ['En curso', `Previsión del ${diaMes(v.fecha_objetivo)}: se guardará antes de descargar el precio`];
  document.getElementById('vivo-etiqueta').textContent = etq;
  document.getElementById('vivo-resumen').textContent = resumen;

  const crear = (etiqueta, clase, texto) => {
    const el = document.createElement(etiqueta);
    if (clase) el.className = clase;
    if (texto !== undefined) el.textContent = texto;
    return el;
  };

  const cabecera = crear('div');
  const titulo = crear('h3', 'vivo-titulo', `Previsión en vivo · ${objetivo} `);
  titulo.appendChild(crear('span', comprobada ? 'chip' : 'chip chip-gris', comprobada ? 'Comprobada' : hecha ? 'Guardada' : 'Pendiente'));
  cabecera.appendChild(titulo);
  tarjeta.appendChild(cabecera);

  if (!hecha) {
    tarjeta.appendChild(crear('p', 'vivo-texto',
      `La previsión a 1 semana desde el último dato (${fecha(v.fecha_origen)}) se guardará con fecha en el repositorio, `
      + 'después del examen final y antes de descargar ningún precio posterior. Entonces se comparará aquí con el precio real.'));
    return;
  }

  // Guardada (y quizá ya comprobada): cuándo se guardó, con qué commit, y las cifras
  const nota = crear('p', 'vivo-texto', `Guardada el ${fecha(v.guardada)}, antes de descargar datos posteriores al ${fecha(v.fecha_origen)}`);
  if (v.commit && /^[0-9a-f]{7,40}$/.test(v.commit)) {
    const repo = document.querySelector('.pie a[href*="github.com"]');
    const enlace = crear('a', 'mono', v.commit.slice(0, 7));
    enlace.href = `${repo ? repo.href : '#'}/commit/${v.commit}`;
    enlace.style.textDecoration = 'underline';
    nota.append(' (commit ', enlace, ')');
  }
  nota.append(comprobada ? '.' : `. Se comprobará con el precio del ${objetivo}.`);
  cabecera.appendChild(nota);
  nota.style.marginTop = '10px';

  const lista = crear('dl', 'vivo-datos');
  const dato = (nombre, valor, clase) => {
    const caja = crear('div');
    caja.append(crear('dt', 'leyenda', nombre), crear('dd', clase, valor));
    lista.appendChild(caja);
  };
  dato('Rango del 80 %', `${numero(v.bajo, 2)} – ${dolares(v.alto)}`, 'ambar');
  dato(`Red (${v.red})`, dolares(v.prevision_red));
  dato('Ingenuo', dolares(v.precio_origen));
  dato('Precio real', comprobada ? `${dolares(v.precio_real)} · ${dentro ? 'dentro' : 'fuera'}` : 'Pendiente');
  tarjeta.appendChild(lista);
}
