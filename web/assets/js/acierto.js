// «¿Acierta el modelo?»: el examen final (2022-2026) de cerca, como pide el profesor: valores reales frente
// a previstos, las métricas (R²) y cuándo acierta y cuándo falla.
//
// - El gráfico coloca cada previsión de la red elegida en la fecha a la que se refería, con el precio real,
//   el ingenuo y el rango del 80 %. Se recorre con el ratón, como el de «Calma y tormenta».
// - La tabla da el R² de cada modelo; la tarjeta de al lado, la nota frente al ingenuo según el mercado
//   (calma, normal, tormenta) y según lo que pasó después.
// Todo sale de data/acierto.json y data/test.json: aquí no se calcula nada.

import { nodo, vaciar, medir, escala, linea, banda, marcas, extremos, idUnico, alRedimensionar, iniciosDeAño } from './graficos.js';
import { numero, dolares, porcentaje, variacion, fechaCorta } from './formato.js';

const NOMBRE = { corto: '1 semana', medio: '3 meses', largo: '1 año' };
const AMBAR = '#f2921d';
const HUESO = '#f4efe6';
const GRIS = '#a39c90';
const TALLO = '#8a8378';
const MODELOS = [['RNN', 'RNN'], ['LSTM', 'LSTM'], ['GRU', 'GRU'], ['Lineal', 'Lineal (referencia)'], ['ingenuo', 'Ingenuo (precio de hoy)']];
const MERCADO = ['calma', 'normal', 'tormenta'];
const MOVIMIENTO = ['bajada fuerte', 'sin gran cambio', 'subida fuerte'];
const ROTULO = { 'bajada fuerte': ['bajada', 'fuerte'], 'sin gran cambio': ['sin', 'cambio'], 'subida fuerte': ['subida', 'fuerte'] };

const parecida = (nota) => Math.abs(nota - 1) < 0.02;

/** «un 23 % menos que el ingenuo», o «prácticamente lo mismo que el ingenuo» si la diferencia es menor del 2 % */
function frenteAlIngenuo(nota) {
  const diferencia = 100 * (nota - 1);
  if (parecida(nota)) return 'prácticamente lo mismo que el ingenuo';
  return `un ${numero(Math.abs(diferencia), 0)} % ${diferencia > 0 ? 'más' : 'menos'} que el ingenuo`;
}

export function iniciarAcierto(d) {
  const a = d.acierto;
  if (!a || !a.plazos) return;
  const el = (id) => document.getElementById(id);
  const svg = el('ac-grafico');
  const svgGrupos = el('ac-grupos');
  const botones = [...document.querySelectorAll('#ac-plazos [data-plazo]')];
  let plazo = 'corto';
  let indice = null;   // el punto que se está leyendo (null: el último)
  let geo = null;

  // ---------------------------------------------------------------- real frente a previsto
  function dibujar() {
    vaciar(svg);
    const { ancho: W, alto: H } = medir(svg);
    if (W < 40) return;
    const s = a.plazos[plazo];
    const n = s.fechas.length;
    const m = { izq: 6, der: 8, arriba: 12, abajo: 24 };
    const x = escala(0, n - 1, m.izq, W - m.der);
    // El eje se ajusta a los precios; el rango, que a 3 meses y a 1 año llega a ser muy ancho, se corta en el borde
    let [yMin, yMax] = extremos(s.real, s.red_precios, s.ingenuo);
    const holgura = (yMax - yMin) * 0.08;
    yMin -= holgura;
    yMax += holgura;
    const y = escala(yMin, yMax, H - m.abajo, m.arriba);
    const xs = s.fechas.map((_, i) => x(i));

    const idRecorte = idUnico('ac-r');
    nodo('rect', { x: 0, y: m.arriba, width: W, height: H - m.abajo - m.arriba }, nodo('clipPath', { id: idRecorte }, nodo('defs', {}, svg)));
    const rotulos = nodo('g', {});   // rótulos de los ejes: se añaden al final, encima de las líneas

    marcas(yMin, yMax, 4).forEach((v) => {
      nodo('line', { class: 'rejilla', x1: m.izq, x2: W - m.der, y1: y(v), y2: y(v) }, svg);
      nodo('text', { class: 'eje', x: m.izq, y: y(v) - 6 }, rotulos, numero(v, 0));
    });
    iniciosDeAño(s.fechas).forEach(([año, i]) => {
      if (i > 0) nodo('line', { class: 'rejilla', x1: x(i), x2: x(i), y1: m.arriba, y2: H - m.abajo }, svg);
      nodo('text', { class: 'eje', x: x(i) + (i > 0 ? 6 : 0), y: H - 7 }, rotulos, String(año));
    });

    const datos = nodo('g', { 'clip-path': `url(#${idRecorte})` }, svg);
    nodo('path', { d: banda(xs, s.alto.map(y), s.bajo.map(y)), fill: AMBAR, 'fill-opacity': 0.12 }, datos);
    nodo('path', { d: linea(xs, s.ingenuo.map(y)), fill: 'none', stroke: GRIS, 'stroke-width': 1, 'stroke-opacity': 0.7,
      'stroke-dasharray': '3 4' }, datos);
    nodo('path', { d: linea(xs, s.red_precios.map(y)), fill: 'none', stroke: AMBAR, 'stroke-width': 1.2, 'stroke-opacity': 0.9,
      'stroke-linejoin': 'round' }, datos);
    nodo('path', { d: linea(xs, s.real.map(y)), fill: 'none', stroke: HUESO, 'stroke-width': 1.5, 'stroke-linejoin': 'round' }, datos);
    svg.appendChild(rotulos);

    // Cursor: la previsión que se está leyendo
    const cursor = nodo('g', {}, svg);
    const vertical = nodo('line', { y1: m.arriba, y2: H - m.abajo, stroke: HUESO, 'stroke-opacity': 0.35 }, cursor);
    const rango = nodo('line', { stroke: AMBAR, 'stroke-width': 2.5, 'stroke-linecap': 'round', 'stroke-opacity': 0.7 }, cursor);
    const puntoRed = nodo('circle', { r: 3.4, fill: AMBAR }, cursor);
    const puntoReal = nodo('circle', { r: 3.6, fill: '#000', stroke: HUESO, 'stroke-width': 1.5 }, cursor);
    const dentro = (py) => Math.min(H - m.abajo, Math.max(m.arriba, py));
    geo = { x, y, dentro, vertical, rango, puntoRed, puntoReal };

    svg.setAttribute('aria-label', `Examen final a ${NOMBRE[plazo]}: ${numero(n, 0)} previsiones de la ${s.red} frente al precio real. `
      + `El precio quedó dentro del rango del 80 % el ${porcentaje(s.cobertura)} de las veces.`);
    fijar(indice === null ? n - 1 : indice);
  }

  function fijar(i) {
    if (!geo) return;
    const s = a.plazos[plazo];
    const k = Math.min(s.fechas.length - 1, Math.max(0, i));
    indice = k;
    const { x, y, dentro, vertical, rango, puntoRed, puntoReal } = geo;
    const px = x(k);
    [vertical, rango].forEach((l) => { l.setAttribute('x1', px); l.setAttribute('x2', px); });
    rango.setAttribute('y1', dentro(y(s.alto[k])));
    rango.setAttribute('y2', dentro(y(s.bajo[k])));
    puntoRed.setAttribute('cx', px);
    puntoRed.setAttribute('cy', y(s.red_precios[k]));
    puntoReal.setAttribute('cx', px);
    puntoReal.setAttribute('cy', y(s.real[k]));

    const fuera = s.real[k] < s.bajo[k] || s.real[k] > s.alto[k];
    el('ac-fecha').textContent = fechaCorta(s.fechas[k]);
    el('ac-real').textContent = dolares(s.real[k]);
    el('ac-red').textContent = dolares(s.red_precios[k]);
    el('ac-ingenuo').textContent = dolares(s.ingenuo[k]);
    el('ac-rango').textContent = `${numero(s.bajo[k], 2)} – ${dolares(s.alto[k])}${fuera ? ' · fuera' : ''}`;
  }

  svg.addEventListener('pointermove', (evento) => {
    if (!geo) return;
    const caja = svg.getBoundingClientRect();
    fijar(Math.round(geo.x.inversa(evento.clientX - caja.left)));
  });

  // ---------------------------------------------------------------- las métricas
  function tabla() {
    const t = el('ac-tabla');
    const examen = d.test.plazos[plazo];
    el('ac-metricas-plazo').textContent = NOMBRE[plazo];
    t.textContent = '';
    const cabeza = document.createElement('thead');
    cabeza.innerHTML = '<tr><th scope="col">Modelo</th><th scope="col">R² del precio</th><th scope="col">R² de la variación</th>'
      + '<th scope="col">Frente al ingenuo</th></tr>';
    t.appendChild(cabeza);
    const cuerpo = document.createElement('tbody');
    MODELOS.forEach(([clave, nombre]) => {
      const m = examen.modelos[clave];
      if (!m || m.r2_precio === undefined) return;
      const tr = document.createElement('tr');
      if (clave === 'ingenuo') tr.className = 'ingenuo';
      const elegida = examen.red_elegida === clave;
      tr.innerHTML = `<th scope="row">${elegida ? `<span class="elegida" title="Red elegida a ${NOMBRE[plazo]}">${nombre}</span>` : nombre}</th>`
        + `<td>${numero(m.r2_precio, 3)}</td><td>${numero(m.r2_variacion, 3)}</td>`
        + `<td>${numero(m.r2_frente, 3)}${clave === 'ingenuo' ? '<small>por definición</small>' : ''}</td>`;
      cuerpo.appendChild(tr);
    });
    t.appendChild(cuerpo);
  }

  // ---------------------------------------------------------------- cuándo acierta y cuándo falla
  function grupos() {
    const s = a.plazos[plazo];
    const g = Object.fromEntries(s.grupos.map((x) => [x.grupo, x]));
    const calma = g.calma.nota;
    const tormenta = g.tormenta.nota;
    const empata = parecida(calma) && parecida(tormenta);
    el('ac-cuando-titulo').textContent = empata ? 'Empata con el ingenuo, esté el mercado en calma o en tormenta'
      : calma < 1 && tormenta > 1 ? 'Gana en calma, pierde en tormenta' : 'Depende de cómo esté el mercado';
    let texto = empata
      ? `En calma y en tormenta, la ${s.red} se equivocó prácticamente lo mismo que el ingenuo (${numero(calma, 2)} y ${numero(tormenta, 2)}).`
      : `En calma, la ${s.red} se equivocó ${frenteAlIngenuo(calma)}; en tormenta, ${frenteAlIngenuo(tormenta)}.`;
    if (tormenta > 1.05) {
      texto += ` Con el mercado nervioso prevé de media un ${variacion(100 * g.tormenta.prevista, 1)}, y el precio se movió un `
        + `${variacion(100 * g.tormenta.real, 1)}.`;
    }
    texto += ` Según lo que pasó después, mejora al ingenuo cuando el precio sube con fuerza (${numero(g['subida fuerte'].nota, 2)}) `
      + `y falla cuando apenas se mueve (${numero(g['sin gran cambio'].nota, 2)}): prevé subida en el ${porcentaje(s.subidas_previstas)} `
      + `de las fichas, y el precio subió en el ${porcentaje(s.subidas_reales)}.`;
    if (plazo === 'largo') texto += ' A 1 año hay pocos movimientos independientes: es orientativo.';
    el('ac-cuando-texto').textContent = texto;
    dibujarGrupos(g);
  }

  /** Nota frente al ingenuo (= 1) de cada grupo, como el minigráfico de los hallazgos */
  function dibujarGrupos(g) {
    vaciar(svgGrupos);
    const { ancho: W, alto: H } = medir(svgGrupos);
    if (W < 40) return;
    const orden = [...MERCADO, ...MOVIMIENTO];
    const valores = orden.map((k) => g[k].nota);
    const desvio = Math.max(0.1, ...valores.map((v) => Math.abs(v - 1))) * 1.2;
    const HUECO = 1.5;                                 // entre los dos grupos, donde va el rótulo del ingenuo
    const posicion = (i) => (i < 3 ? i : i + HUECO);
    const x = escala(-0.55, 5 + HUECO + 0.55, 8, W - 8);
    const y = escala(1 - desvio, 1 + desvio, H - 44, 26);

    nodo('line', { x1: 0, x2: W, y1: y(1), y2: y(1), stroke: HUESO, 'stroke-opacity': 0.4, 'stroke-dasharray': '2 4' }, svgGrupos);
    nodo('text', { class: 'eje', x: x(1), y: 11, 'text-anchor': 'middle' }, svgGrupos, 'mercado ese día');
    nodo('text', { class: 'eje', x: x(posicion(4)), y: 11, 'text-anchor': 'middle' }, svgGrupos, 'movimiento después');
    nodo('text', { class: 'eje', x: x(2 + (HUECO + 1) / 2), y: y(1) - 6, 'text-anchor': 'middle' }, svgGrupos, 'ingenuo = 1');

    orden.forEach((k, i) => {
      const cx = x(posicion(i));
      const v = valores[i];
      nodo('line', { x1: cx, x2: cx, y1: y(1), y2: y(v), stroke: TALLO, 'stroke-width': 1 }, svgGrupos);
      nodo('circle', { cx, cy: y(v), r: 3.4, fill: HUESO }, svgGrupos);
      nodo('text', { class: 'eje', x: cx, y: v >= 1 ? y(v) - 9 : y(v) + 17, 'text-anchor': 'middle', fill: HUESO }, svgGrupos, numero(v, 2));
      (ROTULO[k] || [k]).forEach((palabra, j, todas) => {
        nodo('text', { class: 'eje', x: cx, y: H - 8 - 13 * (todas.length - 1 - j), 'text-anchor': 'middle' }, svgGrupos, palabra);
      });
    });
    svgGrupos.setAttribute('aria-label', `Nota de la ${a.plazos[plazo].red} frente al ingenuo (1): `
      + orden.map((k, i) => `${k} ${numero(valores[i], 2)}`).join(', ') + '. Por debajo de 1, menos error que el ingenuo.');
  }

  // ---------------------------------------------------------------- plazo
  function elegir(nuevo) {
    plazo = nuevo;
    indice = null;
    botones.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.plazo === plazo)));
    el('ac-red-nombre').textContent = `Red (${a.plazos[plazo].red})`;
    dibujar();
    tabla();
    grupos();
  }
  botones.forEach((b) => b.addEventListener('click', () => { if (b.dataset.plazo !== plazo) elegir(b.dataset.plazo); }));

  elegir('corto');
  alRedimensionar(svg.parentElement, dibujar);
  alRedimensionar(svgGrupos.parentElement, () => grupos());
}
