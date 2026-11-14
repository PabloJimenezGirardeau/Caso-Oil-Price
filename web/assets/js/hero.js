// El elemento central de la web: la línea histórica del Brent (2000-2026) se dibuja sola y
// termina abriéndose en un abanico, el rango del 80 % a 1 semana, 3 meses y 1 año.
//
// - La historia va a escala real de tiempo; el futuro, ampliado (raíz del plazo) para que se vea.
// - El abanico pasa por los rangos reales de data/prevision.json y está centrado en el precio
//   de hoy (la línea de puntos): ese centro es el modelo ingenuo.
// - Mientras la línea avanza, la luz del crudo viaja con su punta (crudo.estado.pluma).

import { nodo, vaciar, curva, linea, idUnico, alRedimensionar, iniciosDeAño } from './graficos.js';
import { dolares, fecha } from './formato.js';

const PLAZOS = [
  { clave: 'corto', sesiones: 5, nombre: '1 sem' },
  { clave: 'medio', sesiones: 63, nombre: '3 meses' },
  { clave: 'largo', sesiones: 252, nombre: '1 año' },
];
const AMBAR = '#f2921d';
const HUESO = '#f4efe6';
const FONDO = '#050403';

/** Reduce la serie a unos pocos puntos por píxel conservando mínimos y máximos */
function compactar(precios, cubos) {
  const n = precios.length;
  const tamaño = n / cubos;
  const indices = [];
  for (let c = 0; c < cubos; c++) {
    const desde = Math.floor(c * tamaño);
    const hasta = Math.min(n, Math.floor((c + 1) * tamaño));
    let iMin = desde;
    let iMax = desde;
    for (let i = desde; i < hasta; i++) {
      if (precios[i] < precios[iMin]) iMin = i;
      if (precios[i] > precios[iMax]) iMax = i;
    }
    indices.push(Math.min(iMin, iMax));
    if (iMin !== iMax) indices.push(Math.max(iMin, iMax));
  }
  if (indices.at(-1) !== n - 1) indices.push(n - 1);
  return indices;
}

/** Longitud del trazo hasta que alcanza la coordenada x (búsqueda por mitades) */
function longitudHasta(trazo, x) {
  let a = 0;
  let b = trazo.getTotalLength();
  for (let i = 0; i < 24; i++) {
    const m = (a + b) / 2;
    if (trazo.getPointAtLength(m).x < x) a = m; else b = m;
  }
  return a;
}

export function iniciarHero(d, { crudo, reducido }) {
  const hero = document.getElementById('hero');
  const svg = document.getElementById('hero-grafico');
  const contenido = document.getElementById('hero-contenido');
  const pie = document.getElementById('hero-pie');

  const { precios, fechas } = d.historico;
  const pv = d.prevision;
  const plazos = PLAZOS.map((p) => ({ ...p, ...pv.plazos[p.clave] }));
  const maxHistorico = precios.reduce((m, v) => Math.max(m, v), 0);
  const maxAbanico = Math.max(...plazos.map((p) => p.alto));
  const años = iniciosDeAño(fechas);
  let piezas = null;

  function dibujar() {
    vaciar(svg);
    const caja = hero.getBoundingClientRect();
    const W = caja.width;
    const H = caja.height;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);

    // Zona del gráfico: entre el texto y la cinta. El abanico puede subir por la derecha, donde
    // no hay texto.
    const base = pie.getBoundingClientRect().top - caja.top - 30;
    const techoLinea = contenido.getBoundingClientRect().bottom - caja.top + 24;
    const techoAbanico = 56;
    const k = Math.min((base - techoLinea) / maxHistorico, (base - techoAbanico) / (maxAbanico * 1.04));
    const y = (precio) => base - precio * k;
    const xHoy = W * 0.74;
    const xFin = W - 64;
    const n = precios.length;
    const x = (i) => (i / (n - 1)) * xHoy;
    const xFuturo = (sesiones) => xHoy + (xFin - xHoy) * Math.sqrt(sesiones / 252);
    const yHoy = y(pv.precio);

    const ids = { linea: idUnico('h-linea'), area: idUnico('h-area'), abanico: idUnico('h-abanico'),
      rHist: idUnico('h-rh'), rAb: idUnico('h-ra') };
    const defs = nodo('defs', {}, svg);

    // Degradados: la línea va del gris al blanco cálido y acaba en ámbar; el abanico se apaga
    const gLinea = nodo('linearGradient', { id: ids.linea, gradientUnits: 'userSpaceOnUse', x1: 0, x2: xHoy, y1: 0, y2: 0 }, defs);
    [[0, '#5c574f'], [0.5, '#a39c90'], [0.9, HUESO], [1, AMBAR]]
      .forEach(([o, c]) => nodo('stop', { offset: o, 'stop-color': c }, gLinea));
    const gArea = nodo('linearGradient', { id: ids.area, gradientUnits: 'userSpaceOnUse', x1: 0, x2: 0, y1: y(maxHistorico), y2: base }, defs);
    nodo('stop', { offset: 0, 'stop-color': AMBAR, 'stop-opacity': 0.13 }, gArea);
    nodo('stop', { offset: 1, 'stop-color': AMBAR, 'stop-opacity': 0 }, gArea);
    const gAbanico = nodo('linearGradient', { id: ids.abanico, gradientUnits: 'userSpaceOnUse', x1: xHoy, x2: xFin, y1: 0, y2: 0 }, defs);
    [[0, 0.5], [0.5, 0.24], [1, 0.07]]
      .forEach(([o, a]) => nodo('stop', { offset: o, 'stop-color': AMBAR, 'stop-opacity': a }, gAbanico));

    // Recortes que se abren de izquierda a derecha: así «se dibuja» la línea y se abre el abanico
    const recorteHist = nodo('rect', { x: 0, y: 0, width: xHoy + 2, height: H }, nodo('clipPath', { id: ids.rHist }, defs));
    const recorteAb = nodo('rect', { x: xHoy, y: 0, width: W - xHoy, height: H }, nodo('clipPath', { id: ids.rAb }, defs));

    const texto = (attrs, contenidoTexto, padre) => nodo('text', {
      'font-size': 11, fill: '#8a8378', stroke: FONDO, 'stroke-width': 3.5, 'stroke-linejoin': 'round',
      'paint-order': 'stroke', ...attrs }, padre, contenidoTexto);

    // --- Años, bajo la línea --------------------------------------------------------------
    const gAños = nodo('g', {}, svg);
    años.filter(([año]) => año % 5 === 0).forEach(([año, i]) => {
      texto({ x: Math.max(x(i), 64), y: base + 18, 'text-anchor': i === 0 ? 'start' : 'middle' }, String(año), gAños);
    });

    // --- Historia ----------------------------------------------------------------------------
    const indices = compactar(precios, Math.round(xHoy / 1.6));
    const xs = indices.map(x);
    const ys = indices.map((i) => y(precios[i]));
    const gHist = nodo('g', { 'clip-path': `url(#${ids.rHist})` }, svg);
    nodo('path', { d: `${linea(xs, ys)}L${xHoy},${base}L0,${base}Z`, fill: `url(#${ids.area})` }, gHist);
    nodo('path', { d: linea(xs, ys), fill: 'none', stroke: `url(#${ids.linea})`, 'stroke-width': 1.4,
      'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, gHist);

    // --- Abanico -----------------------------------------------------------------------------
    const gAb = nodo('g', { 'clip-path': `url(#${ids.rAb})` }, svg);
    const arriba = [[xHoy, yHoy], ...plazos.map((p) => [xFuturo(p.sesiones), y(p.alto)])];
    const abajo = [[xHoy, yHoy], ...plazos.map((p) => [xFuturo(p.sesiones), y(p.bajo)])];
    nodo('path', { d: `${curva(arriba)}${curva([...abajo].reverse(), 0.5, true)}Z`, fill: `url(#${ids.abanico})` }, gAb);
    // Centro: el precio de hoy (el ingenuo)
    nodo('line', { x1: xHoy, x2: xFin, y1: yHoy, y2: yHoy, stroke: HUESO, 'stroke-opacity': 0.5, 'stroke-width': 1,
      'stroke-dasharray': '2 5' }, gAb);
    // Bordes: continuos hasta 3 meses y discontinuos después (1 año es orientativo)
    const xMedio = xFuturo(63);
    [arriba, abajo].forEach((puntos) => {
      const borde = nodo('path', { d: curva(puntos), fill: 'none', stroke: AMBAR, 'stroke-width': 1.2, 'stroke-opacity': 0.9 }, gAb);
      const hastaMedio = longitudHasta(borde, xMedio);
      borde.setAttribute('stroke-dasharray', `${hastaMedio.toFixed(1)} 4 ${'3 4 '.repeat(80)}`);
    });
    // El rango de cada plazo, como una marca vertical fina
    plazos.forEach((p) => {
      const xp = xFuturo(p.sesiones);
      nodo('line', { x1: xp, x2: xp, y1: y(p.alto), y2: y(p.bajo), stroke: AMBAR, 'stroke-opacity': 0.32, 'stroke-width': 1 }, gAb);
    });

    // --- Rótulos del abanico ---------------------------------------------------------------
    const gRotulos = nodo('g', {}, svg);
    plazos.forEach((p) => {
      const xp = xFuturo(p.sesiones);
      const ancla = p.clave === 'largo' ? 'end' : 'middle';
      texto({ x: xp, y: base + 18, 'text-anchor': ancla }, p.nombre, gRotulos);
      if (p.orientativo) texto({ x: xp, y: base + 30, 'text-anchor': ancla, 'font-size': 9.5, fill: AMBAR }, 'orientativo', gRotulos);
    });
    const largo = plazos.at(-1);
    const provisional = pv.estado === 'provisional' ? ' · PROVISIONAL' : '';
    texto({ x: xFin, y: y(largo.alto) - 26, 'text-anchor': 'end', fill: AMBAR, 'letter-spacing': '0.06em' },
      `RANGO DEL 80 %${provisional}`, gRotulos);
    texto({ x: xFin, y: y(largo.alto) - 10, 'text-anchor': 'end', fill: HUESO }, dolares(largo.alto), gRotulos);
    texto({ x: xFin, y: y(largo.bajo) + 18, 'text-anchor': 'end', fill: HUESO }, dolares(largo.bajo), gRotulos);

    // --- El último dato -----------------------------------------------------------------------
    const gPunto = nodo('g', { transform: `translate(${xHoy},${yHoy})` }, svg);
    nodo('circle', { r: 9, fill: 'none', stroke: AMBAR, 'stroke-opacity': 0.35 }, gPunto);
    nodo('circle', { r: 3.4, fill: AMBAR }, gPunto);
    const gHoy = nodo('g', {}, svg);
    // El rótulo va por encima de lo más alto del último tramo de la línea, para no pisarla
    const cima = ys.reduce((min, yy, j) => (xs[j] > xHoy - 110 ? Math.min(min, yy) : min), yHoy);
    texto({ x: xHoy - 8, y: cima - 27, 'text-anchor': 'end', fill: HUESO, 'font-size': 13 }, dolares(pv.precio), gHoy);
    texto({ x: xHoy - 8, y: cima - 12, 'text-anchor': 'end' }, fecha(pv.fecha), gHoy);

    piezas = { W, xHoy, yHoy, base, xs, ys, recorteHist, recorteAb, gPunto, gHoy, gRotulos, gAños };
    return piezas;
  }

  /** Altura de la línea en una x cualquiera (interpolando la serie compactada) */
  function alturaEn(px) {
    const { xs, ys } = piezas;
    let a = 0;
    let b = xs.length - 1;
    while (b - a > 1) {
      const m = (a + b) >> 1;
      if (xs[m] < px) a = m; else b = m;
    }
    const tramo = xs[b] - xs[a] || 1;
    return ys[a] + ((ys[b] - ys[a]) * (px - xs[a])) / tramo;
  }

  function estadoFinal() {
    if (crudo) {
      crudo.estado.pluma = piezas.xHoy / piezas.W;
      crudo.estado.fuerza = 0.4;
      crudo.pintar();
    }
  }

  function animar() {
    const { gsap } = window;
    const p = piezas;
    const avance = { v: 0 };
    gsap.set([p.gHoy, p.gRotulos, p.gAños], { opacity: 0 });
    gsap.set(p.gPunto, { opacity: 0 });
    p.recorteHist.setAttribute('width', 0);
    p.recorteAb.setAttribute('width', 0);
    if (crudo) { crudo.estado.pluma = 0; crudo.estado.fuerza = 0; }

    const tl = gsap.timeline({ delay: 0.55 });
    // 1. La línea se dibuja de 2000 a 2026 y la luz del crudo va con su punta
    tl.to(p.gAños, { opacity: 1, duration: 1.2, ease: 'power1.out' }, 0);
    tl.set(p.gPunto, { opacity: 1 }, 0);
    tl.to(avance, {
      v: 1, duration: 2.5, ease: 'power2.inOut',
      onUpdate() {
        // Durante un redibujado (cambio de tamaño) `piezas` es otro objeto: se usa el actual
        const q = piezas;
        const px = avance.v * q.xHoy;
        q.recorteHist.setAttribute('width', px + 2);
        q.gPunto.setAttribute('transform', `translate(${px.toFixed(1)},${alturaEn(px).toFixed(1)})`);
        if (crudo) { crudo.estado.pluma = px / q.W; crudo.estado.fuerza = Math.min(1, avance.v * 4); }
      },
    }, 0);
    // 2. El último dato y, desde él, el abanico
    tl.to(p.gHoy, { opacity: 1, duration: 0.5, ease: 'power1.out' }, '>-0.1');
    tl.to(p.recorteAb, { attr: { width: p.W - p.xHoy }, duration: 1.2, ease: 'power3.out' }, '<');
    tl.to(p.gRotulos, { opacity: 1, duration: 0.6, ease: 'power1.out' }, '>-0.5');
    if (crudo) tl.to(crudo.estado, { fuerza: 0.4, duration: 1.6, ease: 'power2.out' }, '<-0.6');
    return tl;
  }

  dibujar();
  let animacion = null;
  if (reducido || !window.gsap) estadoFinal(); else animacion = animar();

  // Si cambia el ancho, se redibuja ya terminado (sin repetir la animación)
  alRedimensionar(hero, () => {
    if (animacion) { animacion.kill(); animacion = null; }
    dibujar();
    estadoFinal();
  });

  // El cursor inclina un poco la luz, sin estelas
  if (crudo && !reducido) {
    hero.addEventListener('pointermove', (evento) => {
      const caja = hero.getBoundingClientRect();
      crudo.estado.luz[0] = ((evento.clientX - caja.left) / caja.width - 0.5) * 0.24;
      crudo.estado.luz[1] = (0.5 - (evento.clientY - caja.top) / caja.height) * 0.18;
    });
    hero.addEventListener('pointerleave', () => { crudo.estado.luz[0] = 0; crudo.estado.luz[1] = 0; });
  }
}
