// Secciones que solo colocan datos: el minigráfico de los hallazgos, el eje del tiempo del
// método y la tabla comparativa. Todo sale de data/validacion.json y data/test.json.

import { nodo, vaciar, medir, escala, alRedimensionar } from './graficos.js';
import { numero, porcentaje } from './formato.js';

const NOMBRE = { corto: '1 semana', medio: '3 meses', largo: '1 año' };
const ORDEN = ['corto', 'medio', 'largo'];
const MODELOS = [['RNN', 'RNN'], ['LSTM', 'LSTM'], ['GRU', 'GRU'], ['Lineal', 'Lineal (referencia)']];

// ---------------------------------------------------------------------------------------------
// Hallazgo 1: la nota de la red elegida a 3 meses, año a año, alrededor del ingenuo (= 1)
// ---------------------------------------------------------------------------------------------
export function iniciarHallazgos(d) {
  const svg = document.getElementById('hz-notas');
  const plazo = d.validacion.plazos.medio;
  const notas = Object.entries(plazo.modelos[plazo.red_elegida].por_año);
  // Los años del examen final (la misma red, entrenada hasta 2021), en ámbar y tras un hueco
  const examen = d.test.estado === 'hecho' ? Object.entries(d.test.plazos.medio.modelos[plazo.red_elegida].por_año) : [];
  const HUECO = examen.length ? 1 : 0;

  function dibujar() {
    vaciar(svg);
    const { ancho: W, alto: H } = medir(svg);
    if (W < 40) return;
    const todas = [...notas, ...examen];
    const desvio = Math.max(...todas.map(([, v]) => Math.abs(v - 1))) * 1.15;
    const x = escala(0, todas.length - 1 + HUECO, 14, W - 96);
    const posicion = (i) => x(i < notas.length ? i : i + HUECO);
    const y = escala(1 - desvio, 1 + desvio, H - 18, 6);   // por debajo de la línea: menos error que el ingenuo
    nodo('line', { x1: 0, x2: W, y1: y(1), y2: y(1), stroke: '#f4efe6', 'stroke-opacity': 0.4, 'stroke-dasharray': '2 4' }, svg);
    nodo('text', { class: 'eje', x: W, y: y(1) - 6, 'text-anchor': 'end' }, svg, 'ingenuo = 1');
    if (examen.length) {
      const xSep = x(notas.length - 0.5 + HUECO / 2);
      nodo('line', { x1: xSep, x2: xSep, y1: 4, y2: H - 16, stroke: '#f2921d', 'stroke-opacity': 0.35, 'stroke-dasharray': '2 3' }, svg);
      nodo('text', { class: 'eje', x: xSep + 6, y: 12, fill: '#f2921d' }, svg, 'examen final');
    }
    todas.forEach(([año, v], i) => {
      const enExamen = i >= notas.length;
      nodo('line', { x1: posicion(i), x2: posicion(i), y1: y(1), y2: y(v), stroke: enExamen ? '#b5610f' : '#8a8378', 'stroke-width': 1 }, svg);
      nodo('circle', { cx: posicion(i), cy: y(v), r: 3.2, fill: enExamen ? '#f2921d' : '#f4efe6' }, svg);
      nodo('text', { class: 'eje', x: posicion(i), y: H - 2, 'text-anchor': 'middle' }, svg, `’${año.slice(2)}`);
    });
    svg.setAttribute('aria-label', `Nota de la red ${plazo.red_elegida} a 3 meses en cada año de ${notas[0][0]} a ${notas.at(-1)[0]}: `
      + `gana al ingenuo en ${plazo.modelos[plazo.red_elegida].ganados} de ${notas.length} años`
      + (examen.length ? `; en el examen final (${examen[0][0]}-${examen.at(-1)[0]}), en ${examen.filter(([, v]) => v < 1).length} de ${examen.length}.` : '.'));
  }
  dibujar();
  alRedimensionar(svg.parentElement, dibujar);

  if (d.test.estado !== 'pendiente') document.getElementById('hz-examen').textContent = 'Examen final · hecho';
}

// ---------------------------------------------------------------------------------------------
// Método: el eje real de los datos, con sus tramos. Se rellena con el scroll (movimiento.js
// escribe la variable --p de 0 a 1) y cada paso se enciende cuando el avance llega a su tramo.
// ---------------------------------------------------------------------------------------------
export function iniciarMetodo(d) {
  const tiempo = document.getElementById('tiempo');
  const eje = document.getElementById('tiempo-eje');
  const a0 = d.calc.año_ini;
  const a1 = d.calc.año_fin + 1;
  const pos = (año) => (año - a0) / (a1 - a0);
  const añoDe = (iso) => Number(iso.slice(0, 4)) + (Number(iso.slice(5, 7)) - 1) / 12 + Number(iso.slice(8, 10)) / 365;
  const validacion = d.validacion.plazos.medio.modelos[d.validacion.plazos.medio.red_elegida].por_año;
  const añosPrueba = Object.keys(validacion).map(Number);
  const primero = añosPrueba[0];
  const examen = añosPrueba.at(-1) + 1;
  const vivo = añoDe(d.en_vivo.fecha_objetivo);

  const caja = (clase, izquierda, hijos = '') => {
    const el = document.createElement('div');
    el.className = clase;
    el.style.left = `${(100 * izquierda).toFixed(3)}%`;
    el.innerHTML = hijos;
    eje.appendChild(el);
    return el;
  };
  eje.innerHTML = '<div class="tiempo-linea"></div><div class="tiempo-avance"></div>';
  caja('tiempo-tramo', pos(a0), `<span class="leyenda">${a0}</span><small class="leyenda">Datos y entrenamiento</small>`);
  caja('tiempo-tramo', pos(primero), `<span class="leyenda">${primero}</span><small class="leyenda">Prueba año a año</small>`);
  caja('tiempo-tramo', pos(examen), `<span class="leyenda">${examen}</span><small class="leyenda">Examen final</small>`);
  añosPrueba.slice(1).forEach((año) => caja('tiempo-marca', pos(año)));
  caja('tiempo-punto', pos(vivo));

  // Avance a partir del cual se enciende cada paso
  const umbral = { datos: 0.02, entrenamiento: pos(a0 + 5), prueba: pos(primero), examen: pos(examen), vivo: pos(vivo) - 0.01 };
  const pasos = [...tiempo.querySelectorAll('[data-paso]')];
  tiempo.fijarAvance = (p) => {
    tiempo.style.setProperty('--p', p.toFixed(4));
    pasos.forEach((paso) => paso.classList.toggle('activo', p >= umbral[paso.dataset.paso]));
  };
  tiempo.fijarAvance(1);

  if (d.test.estado === 'hecho') {
    const plazos = Object.values(d.test.plazos);
    const sinVentaja = plazos.every((p) => p.conclusion === 'sin evidencia de ventaja');
    const cumple = plazos.every((p) => p.rango.veredicto === 'cumple');
    document.getElementById('mt-examen').textContent = 'Ya se ha hecho: '
      + (sinVentaja ? 'ninguna red mejora al ingenuo' : 'el resultado de cada red está en la tabla')
      + (cumple ? ', y el rango acierta lo prometido en los tres plazos.' : '.');
  }
}

// ---------------------------------------------------------------------------------------------
// Tabla comparativa: plazos × modelos. No se colorea «mejor o peor que 1»: una nota por debajo
// de 1 en doce años no demuestra ventaja. Se enseñan los años ganados y el veredicto de la regla.
// ---------------------------------------------------------------------------------------------
export function iniciarTabla(d) {
  const tabla = document.getElementById('tabla-modelos');
  const v = d.validacion;
  const hecho = d.test.estado !== 'pendiente';
  const celda = (etiqueta, html, atributos = {}) => {
    const el = document.createElement(etiqueta);
    el.innerHTML = html;
    Object.entries(atributos).forEach(([k, valor]) => el.setAttribute(k, valor));
    return el;
  };
  const fila = (celdas, clase) => {
    const tr = document.createElement('tr');
    if (clase) tr.className = clase;
    tr.append(...celdas);
    return tr;
  };
  const notaExamen = (h, modelo) => {
    const nota = hecho ? d.test.plazos?.[h]?.modelos?.[modelo]?.nota : null;
    return nota === null || nota === undefined ? '<span class="pendiente">Pendiente</span>' : numero(nota, 3);
  };

  const titulo = document.createElement('caption');
  titulo.className = 'sr-only';
  titulo.textContent = `Nota de cada modelo frente al ingenuo (error del modelo dividido por el del ingenuo) en ${v.periodo} y en el examen final, por plazo.`;
  tabla.appendChild(titulo);

  const cabeza = document.createElement('thead');
  cabeza.append(
    fila([celda('th', '<span class="sr-only">Modelo</span>', { scope: 'col' }),
      ...ORDEN.map((h) => celda('th', NOMBRE[h], { colspan: 2, scope: 'colgroup', class: 'grupo' }))]),
    fila([celda('th', 'Modelo', { scope: 'col' }),
      ...ORDEN.flatMap((h) => [celda('th', v.periodo, { scope: 'col', class: 'grupo' }),
        celda('th', hecho ? `Examen ${d.test.periodo || ''}` : 'Examen final', { scope: 'col' })])]),
  );
  tabla.appendChild(cabeza);

  const cuerpo = document.createElement('tbody');
  MODELOS.forEach(([clave, nombre]) => {
    cuerpo.appendChild(fila([celda('th', nombre, { scope: 'row' }), ...ORDEN.flatMap((h) => {
      const m = v.plazos[h].modelos[clave];
      const nota = numero(m.nota, 3);
      const elegida = v.plazos[h].red_elegida === clave;
      return [
        celda('td', `${elegida ? `<span class="elegida" title="Red elegida a ${NOMBRE[h]}">${nota}</span>` : nota}<small>gana ${m.ganados} de ${m.años} años</small>`, { class: 'grupo' }),
        celda('td', notaExamen(h, clave)),
      ];
    })]));
  });
  cuerpo.appendChild(fila([celda('th', 'Ingenuo (precio de hoy)', { scope: 'row' }), ...ORDEN.flatMap(() => [
    celda('td', `${numero(1, 3)}<small>por definición</small>`, { class: 'grupo' }),
    celda('td', hecho ? numero(1, 3) : '<span class="pendiente">Pendiente</span>'),
  ])], 'ingenuo'));
  tabla.appendChild(cuerpo);

  // Conclusión con las reglas fijadas antes de calcular: la del examen final, si ya se ha hecho;
  // si no, el veredicto de 2010-2021 (con la media de las tres redes)
  const pieTabla = document.createElement('tfoot');
  const aclaracion = (texto) => `<small class="aclaracion" style="display:block;font-weight:400;color:#8a8378">${texto}</small>`;
  pieTabla.appendChild(fila([celda('th', `${hecho ? 'Conclusión' : 'Veredicto de la regla'}${aclaracion('fijada antes de calcular')}`, { scope: 'row' }),
    ...ORDEN.map((h) => {
      const c = v.plazos[h].criterio;
      const enValidacion = `en ${v.periodo}, ventaja «${c.veredicto}»: las redes ganan ${c.ganados} de ${c.años} años`;
      return hecho
        ? celda('td', `${d.test.plazos[h].conclusion[0].toUpperCase()}${d.test.plazos[h].conclusion.slice(1)}<small class="aclaracion">examen ${d.test.periodo}; ${enValidacion}</small>`, { colspan: 2, class: 'grupo' })
        : celda('td', `Ventaja «${c.veredicto}»<small class="aclaracion">las redes ganan ${c.ganados} de ${c.años} años</small>`, { colspan: 2, class: 'grupo' });
    })]));
  tabla.appendChild(pieTabla);

  // Notas al pie, con las cifras que salen de los datos
  const todos = ORDEN.flatMap((h) => MODELOS.map(([clave]) => v.plazos[h].modelos[clave].p));
  const pMin = Math.min(...todos);
  const azar = ORDEN.map((h) => v.plazos[h].criterio.prob_sin_ventaja);
  const notas = [
    'Nota: error medio del modelo, en dólares, dividido por el del ingenuo, con todos los años juntos. Por debajo de 1, se equivocó menos que el ingenuo en esos años; por encima, más.',
    pMin >= 0.05
      ? `En ${v.periodo}, ninguna diferencia con el ingenuo se distingue del azar: el contraste de Diebold-Mariano da p ≥ 0,05 en todos los casos (el más bajo, p = ${numero(pMin, 2)}).`
      : `En ${v.periodo}, el contraste de Diebold-Mariano distingue del ingenuo algunos casos (p más bajo: ${numero(pMin, 3)}); el resto no se distingue del azar.`,
    'Con contorno, la red elegida en cada plazo: la mejor de 2010-2021, fijada antes del examen final. Las diferencias entre las tres redes tampoco se distinguen del azar.',
    `«Dudosa» no es evidencia de ventaja: ganar esos años sin tener ninguna ocurre entre el ${porcentaje(Math.min(...azar))} y el ${porcentaje(Math.max(...azar))} de las veces. A 1 año hay ${v.plazos.largo.criterio.años} años evaluados, no ${v.plazos.medio.criterio.años}.`,
  ];
  if (!hecho) notas.push('El examen final (2022-2026) se hará una sola vez, con todo lo anterior ya decidido. Hasta entonces, su columna queda pendiente.');
  if (hecho) {
    // Los casos del examen que el contraste distingue del ingenuo (p < 0,05), con su sentido
    const distintos = ORDEN.flatMap((h) => MODELOS.map(([clave, nombre]) => ({ h, clave, nombre, m: d.test.plazos[h].modelos[clave] })))
      .filter(({ m }) => m.p < 0.05);
    const elegidaDistinta = distintos.some(({ h, clave }) => d.test.plazos[h].red_elegida === clave);
    notas.push(distintos.length === 0
      ? `En el examen final (${d.test.periodo}), ningún modelo se distingue del ingenuo (Diebold-Mariano, p ≥ 0,05).`
      : `En el examen final (${d.test.periodo}), el contraste de Diebold-Mariano solo distingue del ingenuo `
        + distintos.map(({ h, nombre, m }) => `la ${nombre} a ${NOMBRE[h]} (${m.nota > 1 ? 'peor' : 'mejor'}, p = ${numero(m.p, 3)})`).join(' y ')
        + (elegidaDistinta ? '.' : '. Las redes elegidas no se distinguen de él.'));
  }
  const cajaNotas = document.getElementById('tabla-notas');
  notas.forEach((texto) => {
    const p = document.createElement('p');
    p.textContent = texto;
    cajaNotas.appendChild(p);
  });
}


// ---------------------------------------------------------------------------------------------
// El examen final en dólares: la tabla que pide el enunciado (MAE, RMSE, mejora frente al
// ingenuo, parámetros y tiempo de entrenamiento), con una pestaña por plazo.
// ---------------------------------------------------------------------------------------------
export function iniciarExamen(d) {
  const caja = document.getElementById('examen-detalle');
  if (!caja || d.test.estado !== 'hecho') return;
  const botones = [...document.querySelectorAll('#ex-plazos [data-plazo]')];
  const tabla = document.getElementById('tabla-examen');
  let plazo = 'corto';
  const filas = [...MODELOS, ['ingenuo', 'Ingenuo (precio de hoy)']];

  function pintar() {
    const p = d.test.plazos[plazo];
    tabla.textContent = '';
    const cabeza = document.createElement('thead');
    cabeza.innerHTML = '<tr><th scope="col">Modelo</th><th scope="col">Error medio (MAE)</th><th scope="col">RMSE</th>'
      + '<th scope="col">Frente al ingenuo</th><th scope="col">Parámetros</th><th scope="col">Entrenamiento</th></tr>';
    tabla.appendChild(cabeza);
    const cuerpo = document.createElement('tbody');
    filas.forEach(([clave, nombre]) => {
      const m = p.modelos[clave];
      const tr = document.createElement('tr');
      if (clave === 'ingenuo') tr.className = 'ingenuo';
      const elegida = p.red_elegida === clave;
      const mejora = clave === 'ingenuo' ? 'la referencia'
        : `un ${numero(Math.abs(100 * m.mejora), 1)} % ${m.mejora > 0 ? 'menos' : 'más'} de error`;
      const celdas = [
        `<th scope="row">${elegida ? `<span class="elegida" title="Red elegida a ${NOMBRE[plazo]}">${nombre}</span>` : nombre}</th>`,
        `<td>${numero(m.mae, 2)} $</td>`, `<td>${numero(m.rmse, 2)} $</td>`, `<td>${mejora}</td>`,
        `<td>${m.parametros === null ? '—' : numero(m.parametros, 0)}</td>`,
        `<td>${clave === 'Lineal' || clave === 'ingenuo' ? '—' : `${numero(m.segundos, 1)} s`}</td>`,
      ];
      tr.innerHTML = celdas.join('');
      cuerpo.appendChild(tr);
    });
    tabla.appendChild(cuerpo);
  }

  botones.forEach((b) => b.addEventListener('click', () => {
    plazo = b.dataset.plazo;
    botones.forEach((o) => o.setAttribute('aria-pressed', String(o === b)));
    pintar();
  }));
  caja.hidden = false;
  pintar();
}
