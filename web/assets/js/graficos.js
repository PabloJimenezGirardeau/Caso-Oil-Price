// Utilidades mínimas para dibujar los gráficos en SVG, sin librería: escalas, trazos y ejes.
// Cada gráfico se dibuja en píxeles reales de su contenedor (el texto queda nítido) y se
// vuelve a dibujar si cambia el ancho.

const NS = 'http://www.w3.org/2000/svg';
let contador = 0;

/** Identificador único para degradados y recortes */
export const idUnico = (prefijo) => `${prefijo}-${++contador}`;

/** Crea un elemento SVG con sus atributos y, si se indica, lo cuelga de `padre` */
export function nodo(etiqueta, atributos = {}, padre = null, texto = null) {
  const el = document.createElementNS(NS, etiqueta);
  for (const [clave, valor] of Object.entries(atributos)) {
    if (valor !== null && valor !== undefined) el.setAttribute(clave, valor);
  }
  if (texto !== null) el.textContent = texto;
  if (padre) padre.appendChild(el);
  return el;
}

export function vaciar(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
}

/** Tamaño en píxeles del SVG; fija el viewBox para trabajar en esas coordenadas */
export function medir(svg) {
  const { width, height } = svg.getBoundingClientRect();
  svg.setAttribute('viewBox', `0 0 ${Math.max(width, 1)} ${Math.max(height, 1)}`);
  return { ancho: width, alto: height };
}

/** Escala lineal: dominio [d0, d1] → píxeles [r0, r1] */
export function escala(d0, d1, r0, r1) {
  const k = (r1 - r0) / (d1 - d0 || 1);
  const f = (v) => r0 + (v - d0) * k;
  f.inversa = (px) => d0 + (px - r0) / k;
  return f;
}

const f1 = (v) => v.toFixed(1);

/** Línea quebrada «M x,y L x,y …» */
export function linea(xs, ys) {
  let d = '';
  for (let i = 0; i < xs.length; i++) d += (i ? 'L' : 'M') + f1(xs[i]) + ',' + f1(ys[i]);
  return d;
}

/** Banda cerrada entre dos series (arriba y abajo) con las mismas x */
export function banda(xs, altos, bajos) {
  let d = linea(xs, altos);
  for (let i = xs.length - 1; i >= 0; i--) d += 'L' + f1(xs[i]) + ',' + f1(bajos[i]);
  return d + 'Z';
}

/** Curva suave que pasa por los puntos [[x, y], …] (Catmull-Rom convertida a Bézier) */
export function curva(puntos, tension = 0.5, continuar = false) {
  let d = (continuar ? 'L' : 'M') + f1(puntos[0][0]) + ',' + f1(puntos[0][1]);
  for (let i = 0; i < puntos.length - 1; i++) {
    const p0 = puntos[i - 1] || puntos[i];
    const p1 = puntos[i];
    const p2 = puntos[i + 1];
    const p3 = puntos[i + 2] || p2;
    const c1 = [p1[0] + ((p2[0] - p0[0]) * tension) / 3, p1[1] + ((p2[1] - p0[1]) * tension) / 3];
    const c2 = [p2[0] - ((p3[0] - p1[0]) * tension) / 3, p2[1] - ((p3[1] - p1[1]) * tension) / 3];
    d += `C${f1(c1[0])},${f1(c1[1])} ${f1(c2[0])},${f1(c2[1])} ${f1(p2[0])},${f1(p2[1])}`;
  }
  return d;
}

/** Marcas «redondas» para un eje (1, 2, 2,5 o 5 × 10ⁿ) */
export function marcas(min, max, cuantas = 4) {
  const bruto = (max - min) / Math.max(cuantas, 1);
  const potencia = 10 ** Math.floor(Math.log10(bruto));
  const paso = [1, 2, 2.5, 5, 10].map((m) => m * potencia).find((p) => p >= bruto) || bruto;
  const lista = [];
  for (let v = Math.ceil(min / paso) * paso; v <= max + 1e-9; v += paso) lista.push(Number(v.toFixed(6)));
  return lista;
}

/** Mínimo y máximo de varias series, ignorando huecos */
export function extremos(...series) {
  let min = Infinity;
  let max = -Infinity;
  for (const serie of series) {
    for (const v of serie) {
      if (v === null || v === undefined) continue;
      if (v < min) min = v;
      if (v > max) max = v;
    }
  }
  return [min, max];
}

/** Vuelve a llamar a `dibujar` cuando cambia el ancho del elemento (no el alto: evita bucles) */
export function alRedimensionar(el, dibujar) {
  let ancho = el.getBoundingClientRect().width;
  let pendiente = 0;
  const observador = new ResizeObserver(() => {
    const nuevo = el.getBoundingClientRect().width;
    if (Math.abs(nuevo - ancho) < 1) return;
    ancho = nuevo;
    cancelAnimationFrame(pendiente);
    pendiente = requestAnimationFrame(dibujar);
  });
  observador.observe(el);
  return observador;
}

/** Primer índice de cada año en una lista de fechas ISO: [[año, índice], …] */
export function iniciosDeAño(fechas) {
  const lista = [];
  let anterior = null;
  fechas.forEach((f, i) => {
    const año = f.slice(0, 4);
    if (año !== anterior) lista.push([Number(año), i]);
    anterior = año;
  });
  return lista;
}
