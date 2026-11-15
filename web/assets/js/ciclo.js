// El ciclo del petróleo: el precio diario del Brent con sus grandes picos y caídas marcados, y lo que
// los provocó. La fecha y el precio de cada uno se buscan en data/historico.json (el máximo o el
// mínimo dentro de su tramo); solo la explicación es texto.

import { nodo, vaciar, medir, escala, linea, marcas, alRedimensionar, iniciosDeAño } from './graficos.js';
import { numero, dolares, fecha, mesAño } from './formato.js';

const AMBAR = '#f2921d';
const HUESO = '#f4efe6';

/** Caída en % entre dos episodios: «76 %» */
const caida = (antes, despues) => `${numero(100 * (1 - despues.precio / antes.precio), 0)} %`;

// tipo: el máximo o el mínimo del tramo. «referencia»: solo se usa para el texto del siguiente.
const EPISODIOS = [
  { tipo: 'max', desde: '2008-01-01', hasta: '2008-12-31', titulo: 'Máximo histórico',
    texto: (e) => `El ${fecha(e.fecha)}, ${dolares(e.precio)}. La demanda de China y otros emergentes, un dólar débil y la entrada de dinero financiero en las materias primas empujaron el Brent a su récord, justo antes de la crisis.` },
  { tipo: 'min', desde: '2008-07-01', hasta: '2009-06-30', titulo: 'Crisis financiera',
    texto: (e, antes) => `Tras la quiebra de Lehman Brothers, la recesión mundial hundió la demanda: ${dolares(e.precio)} en ${mesAño(e.fecha)}, un ${caida(antes, e)} menos que en el máximo, en medio año.` },
  { tipo: 'max', desde: '2014-01-01', hasta: '2014-08-31', referencia: true },
  { tipo: 'min', desde: '2015-06-01', hasta: '2016-06-30', titulo: 'Exceso de oferta',
    texto: (e, antes) => `El petróleo de esquisto de EE. UU. inundó el mercado y la OPEP decidió no recortar su producción para defender su cuota. De ${dolares(antes.precio)} en ${mesAño(antes.fecha)} a ${dolares(e.precio)} en ${mesAño(e.fecha)}: un ${caida(antes, e)} menos.` },
  { tipo: 'min', desde: '2020-01-01', hasta: '2020-12-31', titulo: 'Pandemia',
    texto: (e, _, d) => `Los confinamientos paralizaron el transporte y la industria, el consumo se desplomó y los almacenes se llenaron. El ${fecha(e.fecha)}, ${dolares(e.precio)}`
      + (e.precio <= Math.min(...d.historico.precios) ? `: el precio más bajo de toda la serie desde ${d.historico.fechas[0].slice(0, 4)}.` : '.') },
  { tipo: 'max', desde: '2022-01-01', hasta: '2022-12-31', titulo: 'Invasión de Ucrania',
    texto: (e) => `La invasión rusa de Ucrania y las sanciones a Rusia, uno de los mayores exportadores de crudo, dispararon el miedo a quedarse sin suministro: ${dolares(e.precio)} en ${mesAño(e.fecha)}.` },
  { tipo: 'max', desde: '2026-01-01', hasta: '2099-12-31', titulo: 'Lo más reciente',
    texto: (e, _, d) => {
      const golpe = mayorCaidaDiaria(d.historico, e.indice);
      return `En 2026 el Brent volvió a dispararse, hasta ${dolares(e.precio)} el ${fecha(e.fecha)}, y después cayó con la misma brusquedad`
        + (golpe ? `: un ${numero(golpe.caida, 1)} % en un solo día, el ${fecha(golpe.fecha)}.` : '.')
        + ' Movimientos así no se pueden anticipar con datos de mercado: es justo cuando el rango se ensancha.';
    } },
];

/** La mayor caída de un día después de `desde` (en %), con su fecha */
function mayorCaidaDiaria({ fechas, precios }, desde) {
  let mejor = null;
  for (let i = desde + 1; i < precios.length; i++) {
    const c = 100 * (1 - precios[i] / precios[i - 1]);
    if (!mejor || c > mejor.caida) mejor = { caida: c, fecha: fechas[i] };
  }
  return mejor && mejor.caida > 0 ? mejor : null;
}

/** El máximo o el mínimo del precio dentro de un tramo de fechas */
function buscar({ fechas, precios }, { tipo, desde, hasta }) {
  let indice = -1;
  fechas.forEach((f, i) => {
    if (f < desde || f > hasta) return;
    if (indice < 0 || (tipo === 'max' ? precios[i] > precios[indice] : precios[i] < precios[indice])) indice = i;
  });
  return indice < 0 ? null : { indice, fecha: fechas[indice], precio: precios[indice] };
}

export function iniciarCiclo(d) {
  const svg = document.getElementById('ci-grafico');
  const lista = document.getElementById('ci-episodios');
  if (!svg || !lista) return;
  const { fechas, precios } = d.historico;

  // Cada episodio con su fecha y su precio reales, y el texto que los explica
  const episodios = [];
  let anterior = null;
  EPISODIOS.forEach((e) => {
    const encontrado = buscar(d.historico, e);
    if (!encontrado) return;
    const episodio = { ...e, ...encontrado };
    if (!e.referencia) episodios.push({ ...episodio, explicacion: e.texto(episodio, anterior, d) });
    anterior = episodio;
  });

  // Las tarjetas
  lista.textContent = '';
  episodios.forEach((e, n) => {
    const tarjeta = document.createElement('article');
    tarjeta.className = 'tarjeta uso';
    tarjeta.innerHTML = `<p class="leyenda">${String(n + 1).padStart(2, '0')} · ${e.fecha.slice(0, 4)} · ${e.tipo === 'max' ? 'pico' : 'caída'}</p>`
      + `<h3>${e.titulo}</h3><p>${e.explicacion}</p>`;
    lista.appendChild(tarjeta);
  });

  function dibujar() {
    vaciar(svg);
    const { ancho: W, alto: H } = medir(svg);
    if (W < 40) return;
    const m = { izq: 8, der: 16, arriba: 26, abajo: 26 };
    const x = escala(0, precios.length - 1, m.izq, W - m.der);
    const techo = Math.max(...precios) * 1.12;
    const y = escala(0, techo, H - m.abajo, m.arriba);

    marcas(0, techo, 4).forEach((v) => {
      nodo('line', { class: 'rejilla', x1: m.izq, x2: W - m.der, y1: y(v), y2: y(v) }, svg);
      nodo('text', { class: 'eje', x: m.izq, y: y(v) - 6 }, svg, `${numero(v, 0)} $`);
    });
    iniciosDeAño(fechas).filter(([año]) => año % 5 === 0).forEach(([año, i]) => {
      nodo('text', { class: 'eje', x: x(i), y: H - 6, 'text-anchor': 'middle' }, svg, String(año));
    });

    nodo('path', { d: linea(precios.map((_, i) => x(i)), precios.map(y)), fill: 'none', stroke: HUESO,
      'stroke-opacity': 0.75, 'stroke-width': 1.1, 'stroke-linejoin': 'round' }, svg);

    episodios.forEach((e, n) => {
      const cx = x(e.indice);
      const cy = y(e.precio);
      const arriba = e.tipo === 'max';
      nodo('line', { x1: cx, x2: cx, y1: cy, y2: arriba ? cy - 14 : cy + 14, stroke: AMBAR, 'stroke-opacity': 0.6 }, svg);
      nodo('circle', { cx, cy, r: 4.5, fill: AMBAR, stroke: '#000', 'stroke-width': 1.5 }, svg);
      nodo('text', { x: cx, y: arriba ? cy - 19 : cy + 26, fill: AMBAR, 'font-size': 11, 'text-anchor': 'middle' }, svg,
        String(n + 1).padStart(2, '0'));
    });

    svg.setAttribute('aria-label', `Precio diario del Brent de ${fechas[0].slice(0, 4)} a ${fechas.at(-1).slice(0, 4)} con sus grandes episodios: `
      + episodios.map((e, n) => `${n + 1}, ${e.titulo}, ${dolares(e.precio)} en ${mesAño(e.fecha)}`).join('; ') + '.');
  }

  dibujar();
  alRedimensionar(svg.parentElement, dibujar);
}
