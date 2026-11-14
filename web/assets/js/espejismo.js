// «El espejismo»: el precio real, el ingenuo y la red entrenada con precios (control D15).
// El interruptor retrasa la línea del precio real las 5 sesiones del plazo: entonces cae
// exactamente sobre el ingenuo y se ve que la red estaba más cerca del precio de hace una
// semana que del que quería prever. Sin trucos: es un desplazamiento horizontal, y las dos
// distancias que se leen debajo están medidas en el estudio (data/espejismo.json).

import { nodo, vaciar, medir, escala, linea, marcas, extremos, idUnico, alRedimensionar } from './graficos.js';
import { numero, dolares, fechaCorta } from './formato.js';

const AMBAR = '#f2921d';
const HUESO = '#f4efe6';
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

export function iniciarEspejismo(d) {
  const e = d.espejismo;
  const { fechas, real, ingenuo, red_precios: red } = e.serie;
  const h = e.sesiones;
  const svg = document.getElementById('es-grafico');
  const interruptor = document.getElementById('es-interruptor');
  const lectura = document.getElementById('es-lectura');

  // Tramo que se enseña: el desplome de finales de 2018, donde el retraso se ve a simple vista
  const i0 = Math.max(h, fechas.findIndex((f) => f >= e.ventana[0]));
  let i1 = fechas.length - 1;
  while (i1 > i0 && fechas[i1] > e.ventana[1]) i1--;
  document.getElementById('es-tramo').textContent = `Brent · ${fechaCorta(fechas[i0])} – ${fechaCorta(fechas[i1])} · previsión a 1 semana`;

  let retrasada = false;
  let gReal = null;
  let paso = 0;

  function dibujar() {
    vaciar(svg);
    const { ancho: W, alto: H } = medir(svg);
    if (W < 40) return;
    const m = { izq: 6, der: 8, arriba: 12, abajo: 24 };
    const x = escala(i0, i1, m.izq, W - m.der);
    paso = x(1) - x(0);
    const tramo = (serie) => serie.slice(i0 - h, i1 + 1);
    const [yMin, yMax] = extremos(tramo(real), tramo(ingenuo), tramo(red));
    const y = escala(yMin - 2, yMax + 2, H - m.abajo, m.arriba);

    const idRecorte = idUnico('es-r');
    nodo('rect', { x: m.izq, y: 0, width: W - m.izq - m.der, height: H - m.abajo + 2 },
      nodo('clipPath', { id: idRecorte }, nodo('defs', {}, svg)));
    const rotulos = nodo('g', {});   // rótulos de los ejes: se añaden al final, encima de las líneas

    marcas(yMin, yMax, 4).forEach((v) => {
      nodo('line', { class: 'rejilla', x1: m.izq, x2: W - m.der, y1: y(v), y2: y(v) }, svg);
      nodo('text', { class: 'eje', x: m.izq, y: y(v) - 6 }, rotulos, `${numero(v, 0)} $`);
    });
    // Un rótulo por mes
    for (let i = i0 + 1; i <= i1; i++) {
      if (fechas[i].slice(5, 7) === fechas[i - 1].slice(5, 7)) continue;
      const mes = Number(fechas[i].slice(5, 7));
      nodo('line', { class: 'rejilla', x1: x(i), x2: x(i), y1: m.arriba, y2: H - m.abajo }, svg);
      nodo('text', { class: 'eje', x: x(i) + 6, y: H - 7 }, rotulos, mes === 1 ? `ene ${fechas[i].slice(0, 4)}` : MESES[mes - 1]);
    }

    const datos = nodo('g', { 'clip-path': `url(#${idRecorte})` }, svg);
    const indices = Array.from({ length: i1 - (i0 - h) + 1 }, (_, k) => i0 - h + k);
    const trazo = (serie) => linea(indices.map(x), indices.map((i) => y(serie[i])));
    nodo('path', { d: trazo(ingenuo), fill: 'none', stroke: '#a39c90', 'stroke-width': 1.2, 'stroke-dasharray': '3 4' }, datos);
    nodo('path', { d: trazo(red), fill: 'none', stroke: AMBAR, 'stroke-width': 1.6, 'stroke-linejoin': 'round' }, datos);
    // El precio real va en su propio grupo: es lo que se desplaza con el interruptor
    gReal = nodo('g', { class: 'espejismo-real' }, datos);
    nodo('path', { d: trazo(real), fill: 'none', stroke: HUESO, 'stroke-width': 1.6, 'stroke-linejoin': 'round' }, gReal);
    svg.appendChild(rotulos);
    aplicar();
  }

  function aplicar() {
    if (gReal) gReal.style.transform = retrasada ? `translateX(${(h * paso).toFixed(2)}px)` : 'translateX(0px)';
    const medidas = e.medidas.precios;
    lectura.innerHTML = retrasada
      ? `Con el precio real retrasado ${h} sesiones (cae justo sobre el ingenuo), la red queda más cerca: a <strong>${dolares(medidas.error_hoy)}</strong> de media. `
        + `Se parece más al precio de hace una semana que al que quería prever. Medido en ${e.periodo_medidas}.`
      : `Tal como se dibuja, la red parece seguir al precio real, pero queda a <strong>${dolares(medidas.error_futuro)}</strong> de media de él. `
        + `Active el interruptor para ver a qué se parece de verdad. Medido en ${e.periodo_medidas}.`;
  }

  interruptor.addEventListener('click', () => {
    retrasada = !retrasada;
    interruptor.setAttribute('aria-checked', String(retrasada));
    aplicar();
  });

  dibujar();
  alRedimensionar(svg.parentElement, dibujar);
}
