// «Calma y tormenta»: el precio real de 2019-2021 con el rango del 80 % de cada día.
//
// - La banda se colorea con la volatilidad del día en que se hizo: fría en calma, ámbar en tormenta.
// - La sección se queda fija y el scroll recorre las fechas: el gráfico se va descubriendo y la
//   banda se abre al llegar al desplome de 2020. Con «reducir movimiento» (o en una ventana muy
//   baja) se ve entero y se recorre con el ratón.
// - El fondo es el mismo crudo del hero, y su agitación sigue a la volatilidad real de la fecha.
// - Al lado, la cobertura en calma, normal y tormenta frente al rango fijo, con la marca del 80 %.

import { nodo, vaciar, medir, escala, linea, banda, marcas, extremos, idUnico, alRedimensionar, iniciosDeAño } from './graficos.js';
import { numero, dolares, porcentaje, fechaCorta } from './formato.js';
import { crearCrudo } from './crudo.js';

const FRIO = [124, 150, 163];
const AMBAR = [242, 146, 29];
const HUESO = '#f4efe6';
const TERCIOS = [['calma', 'Calma'], ['normal', 'Normal'], ['tormenta', 'Tormenta']];

const mezcla = (a) => `rgb(${FRIO.map((c, i) => Math.round(c + (AMBAR[i] - c) * a)).join(' ')})`;

export function iniciarCalma(d, { reducido }) {
  const seccion = document.getElementById('calma');
  const svg = document.getElementById('cl-grafico');
  const botones = [...document.querySelectorAll('#cl-plazos button')];
  const el = (id) => document.getElementById(id);
  const crudo = crearCrudo(el('calma-crudo'), { quieto: reducido, brillo: 0.85, tiempoInicial: 40 });

  let plazo = 'corto';
  let serie = null;      // la serie del plazo elegido
  let nervio = [];       // volatilidad de cada día, de 0 (calma) a 1 (tormenta)
  let geo = null;        // geometría del último dibujo
  let conScroll = false; // true: el scroll descubre el gráfico
  let indice = 0;

  function preparar() {
    serie = d.rango.plazos[plazo].serie;
    // Calma y tormenta relativas al periodo: del percentil 20 al 97 de la volatilidad (en logaritmos)
    const ordenada = [...serie.volatilidad].sort((a, b) => a - b);
    const q = (p) => Math.log(ordenada[Math.floor(p * (ordenada.length - 1))]);
    const [bajo, alto] = [q(0.2), q(0.97)];
    nervio = serie.volatilidad.map((v) => Math.min(1, Math.max(0, (Math.log(v) - bajo) / (alto - bajo))));
  }

  function dibujar() {
    vaciar(svg);
    const { ancho: W, alto: H } = medir(svg);
    if (W < 40) return;
    const n = serie.fechas.length;
    const m = { izq: 6, der: 8, arriba: 12, abajo: 24 };
    const x = escala(0, n - 1, m.izq, W - m.der);
    // El eje se ajusta al precio real y al rango fijo. Si nuestro rango se sale (pasa a 3 meses en 2020,
    // cuando llegó a ser enorme), se corta en el borde; sus cifras exactas siguen en la lectura de arriba
    const [yMin, yMax] = extremos(serie.real, serie.bajo_fijo, serie.alto_fijo);
    // Escala logarítmica: el rango es un porcentaje del precio, y así su anchura se ve igual a 20 $ que a 80 $
    const yLog = escala(Math.log(yMin * 0.7), Math.log(yMax * 1.25), H - m.abajo, m.arriba);
    const y = (precio) => yLog(Math.log(Math.max(precio, 0.01)));
    const xs = serie.fechas.map((_, i) => x(i));

    const ids = { banda: idUnico('cl-b'), recorte: idUnico('cl-r') };
    const defs = nodo('defs', {}, svg);
    // Degradado horizontal: el color de cada tramo es la volatilidad de ese momento
    const g = nodo('linearGradient', { id: ids.banda, gradientUnits: 'userSpaceOnUse', x1: x(0), x2: x(n - 1), y1: 0, y2: 0 }, defs);
    const tramos = 64;
    for (let t = 0; t <= tramos; t++) {
      const i = Math.round((t / tramos) * (n - 1));
      nodo('stop', { offset: (t / tramos).toFixed(4), 'stop-color': mezcla(nervio[i]) }, g);
    }
    const recorte = nodo('rect', { x: 0, y: m.arriba, width: W, height: H - m.abajo - m.arriba }, nodo('clipPath', { id: ids.recorte }, defs));
    const rotulos = nodo('g', {});   // rótulos de los ejes: se añaden al final, encima de las líneas

    // Rejilla, precios y años
    [10, 15, 20, 30, 40, 60, 80, 120, 160].filter((v) => v >= yMin * 0.75 && v <= yMax * 1.2).forEach((v) => {
      nodo('line', { class: 'rejilla', x1: m.izq, x2: W - m.der, y1: y(v), y2: y(v) }, svg);
      nodo('text', { class: 'eje', x: m.izq, y: y(v) - 6 }, rotulos, `${numero(v, 0)} $`);
    });
    iniciosDeAño(serie.fechas).forEach(([año, i]) => {
      if (i > 0) nodo('line', { class: 'rejilla', x1: x(i), x2: x(i), y1: m.arriba, y2: H - m.abajo }, svg);
      nodo('text', { class: 'eje', x: x(i) + (i > 0 ? 6 : 0), y: H - 7 }, rotulos, String(año));
    });

    // Los datos, dentro del recorte que el scroll va abriendo
    const datos = nodo('g', { 'clip-path': `url(#${ids.recorte})` }, svg);
    nodo('path', { d: banda(xs, serie.alto.map(y), serie.bajo.map(y)), fill: `url(#${ids.banda})`, 'fill-opacity': 0.3 }, datos);
    nodo('path', { d: linea(xs, serie.alto.map(y)), fill: 'none', stroke: `url(#${ids.banda})`, 'stroke-width': 1, 'stroke-opacity': 0.85 }, datos);
    nodo('path', { d: linea(xs, serie.bajo.map(y)), fill: 'none', stroke: `url(#${ids.banda})`, 'stroke-width': 1, 'stroke-opacity': 0.85 }, datos);
    ['alto_fijo', 'bajo_fijo'].forEach((clave) => {
      nodo('path', { d: linea(xs, serie[clave].map(y)), fill: 'none', stroke: '#a39c90', 'stroke-width': 1, 'stroke-opacity': 0.75,
        'stroke-dasharray': '3 4' }, datos);
    });
    nodo('path', { d: linea(xs, serie.real.map(y)), fill: 'none', stroke: HUESO, 'stroke-width': 1.5, 'stroke-linejoin': 'round' }, datos);

    svg.appendChild(rotulos);
    // Cursor: la fecha que se está leyendo
    const cursor = nodo('g', {}, svg);
    const vertical = nodo('line', { y1: m.arriba, y2: H - m.abajo, stroke: HUESO, 'stroke-opacity': 0.35 }, cursor);
    const rango = nodo('line', { stroke: mezcla(1), 'stroke-width': 2.5, 'stroke-linecap': 'round' }, cursor);
    const punto = nodo('circle', { r: 3.6, fill: '#000', stroke: HUESO, 'stroke-width': 1.5 }, cursor);

    const dentro = (py) => Math.min(H - m.abajo, Math.max(m.arriba, py));   // sin salirse del gráfico
    geo = { W, H, x, y, dentro, recorte, vertical, rango, punto };
    fijar(indice);
  }

  /** Sitúa la lectura en el día i: cursor, cifras, recorte y agitación del fondo */
  function fijar(i) {
    if (!geo || !serie) return;
    const n = serie.fechas.length;
    indice = Math.min(n - 1, Math.max(0, i));
    const { x, y, W, dentro, recorte, vertical, rango, punto } = geo;
    const px = x(indice);
    recorte.setAttribute('width', conScroll ? px + 1 : W);
    vertical.setAttribute('x1', px);
    vertical.setAttribute('x2', px);
    rango.setAttribute('x1', px);
    rango.setAttribute('x2', px);
    rango.setAttribute('y1', dentro(y(serie.alto[indice])));
    rango.setAttribute('y2', dentro(y(serie.bajo[indice])));
    rango.setAttribute('stroke', mezcla(nervio[indice]));
    punto.setAttribute('cx', px);
    punto.setAttribute('cy', y(serie.real[indice]));

    el('cl-fecha').textContent = fechaCorta(serie.fechas[indice]);
    el('cl-real').textContent = dolares(serie.real[indice]);
    el('cl-rango').textContent = `${numero(serie.bajo[indice], 2)} – ${dolares(serie.alto[indice])}`;
    el('cl-fijo').textContent = `${numero(serie.bajo_fijo[indice], 2)} – ${dolares(serie.alto_fijo[indice])}`;
    if (crudo) crudo.estado.agitacion = nervio[indice];
  }

  /** Panel de cobertura del plazo elegido */
  function cobertura() {
    const p = d.rango.plazos[plazo];
    el('cb-periodo').textContent = `${p.años[0]}-${p.años.at(-1)}`;
    el('cb-mejora').textContent = Math.round(100 * p.mejora);
    const caja = el('cb-medidores');
    caja.textContent = '';
    TERCIOS.forEach(([clave, nombre]) => {
      const medidor = document.createElement('div');
      medidor.className = 'medidor';
      const titulo = document.createElement('p');
      titulo.className = 'leyenda';
      titulo.textContent = nombre;
      medidor.appendChild(titulo);
      [['Nuestro', p.elegido.tercios[clave], 'nuestro'], ['Fijo', p.fijo.tercios[clave], '']].forEach(([quien, valor, clase]) => {
        const fila = document.createElement('div');
        fila.className = 'medidor-fila';
        fila.innerHTML = `<span>${quien}</span><div class="medidor-barra"><i class="${clase}" style="--v:${valor}"></i></div><b>${porcentaje(valor)}</b>`;
        medidor.appendChild(fila);
      });
      caja.appendChild(medidor);
    });
    const año = '2020';
    el('cb-resumen').innerHTML = `La marca vertical es el 80 % prometido. En ${año}, el año del desplome, nuestro rango acertó el `
      + `<strong>${porcentaje(p.elegido.por_año[año])}</strong> de las veces; el fijo, el <strong>${porcentaje(p.fijo.por_año[año])}</strong>.`;
    const examen = d.test.estado === 'hecho' ? d.test.plazos[plazo].rango : null;
    if (examen) {
      el('cb-resumen').innerHTML += ` En el examen final (${d.test.periodo}) acertó el <strong>${porcentaje(examen.cobertura)}</strong> y fue `
        + (examen.mejora_pct > 0 ? `un ${examen.mejora_pct} % más preciso que el fijo.` : 'tan preciso como el fijo, no más.');
    }
  }

  /** Día de más volatilidad: donde empieza la lectura si no hay scroll */
  const diaDeTormenta = () => nervio.reduce((mejor, v, i) => (serie.volatilidad[i] > serie.volatilidad[mejor] ? i : mejor), 0);

  function elegir(nuevo) {
    plazo = nuevo;
    botones.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.plazo === plazo)));
    preparar();
    if (!conScroll) indice = diaDeTormenta();
    dibujar();
    cobertura();
  }
  botones.forEach((b) => b.addEventListener('click', () => { if (b.dataset.plazo !== plazo) elegir(b.dataset.plazo); }));

  // Recorrer el gráfico con el ratón
  const leerPuntero = (evento) => {
    if (!geo) return;
    const caja = svg.getBoundingClientRect();
    fijar(Math.round(geo.x.inversa(evento.clientX - caja.left)));
  };
  svg.addEventListener('pointermove', leerPuntero);

  preparar();
  indice = diaDeTormenta();
  dibujar();
  cobertura();
  alRedimensionar(svg.parentElement, dibujar);

  // El scroll recorre las fechas si se admiten animaciones y la ventana tiene altura suficiente
  const { gsap, ScrollTrigger } = window;
  if (!reducido && gsap && ScrollTrigger) {
    gsap.matchMedia().add('(min-height: 700px)', () => {
      conScroll = true;
      const disparador = ScrollTrigger.create({
        trigger: seccion,
        start: 'top 65%',
        end: 'bottom bottom',
        onUpdate: (self) => {
          const avance = Math.min(1, Math.max(0, (self.progress - 0.02) / 0.9));
          fijar(Math.round(avance * (serie.fechas.length - 1)));
        },
      });
      fijar(Math.round(disparador.progress * (serie.fechas.length - 1)));
      return () => { conScroll = false; fijar(diaDeTormenta()); };
    });
  }
}
