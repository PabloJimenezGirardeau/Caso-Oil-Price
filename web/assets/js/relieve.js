// Curvas de nivel de fondo: líneas finas como las de un mapa topográfico o sísmico de un
// yacimiento, a muy baja opacidad. No es una imagen: se calculan con «marching squares» sobre un
// relieve suave inventado (unas cuantas colinas), distinto según la semilla.
//
// Se pintan una sola vez en un <canvas> (y otra si cambia el ancho): así el navegador solo mueve
// una imagen ya hecha al desplazarlas con el scroll, en lugar de recalcular miles de trazos.

import { alRedimensionar } from './graficos.js';

const ANCHO = 1600;      // tamaño de referencia del dibujo; se escala para cubrir el lienzo
const ALTO = 1000;
const COLUMNAS = 96;
const FILAS = 60;
const NIVELES = 13;

/** Generador pseudoaleatorio con semilla (mulberry32): mismo dibujo en cada visita */
function aleatorio(semilla) {
  let a = semilla >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Segmentos [x1, y1, x2, y2, …] de todas las curvas de nivel, en coordenadas de referencia */
function calcularCurvas(semilla) {
  const azar = aleatorio(semilla);
  // El relieve: suma de colinas y hondonadas
  const colinas = Array.from({ length: 11 }, () => ({
    x: azar(), y: azar(), radio: 0.1 + azar() * 0.26, altura: azar() - 0.32,
  }));
  const altura = (u, v) => colinas.reduce((suma, c) => suma + c.altura * Math.exp(-((u - c.x) ** 2 + (v - c.y) ** 2) / c.radio ** 2), 0);

  const malla = [];
  let min = Infinity;
  let max = -Infinity;
  for (let j = 0; j <= FILAS; j++) {
    const fila = [];
    for (let i = 0; i <= COLUMNAS; i++) {
      const valor = altura(i / COLUMNAS, j / FILAS);
      fila.push(valor);
      if (valor < min) min = valor;
      if (valor > max) max = valor;
    }
    malla.push(fila);
  }

  const dx = ANCHO / COLUMNAS;
  const dy = ALTO / FILAS;
  const segmentos = [];
  for (let n = 1; n < NIVELES; n++) {
    const nivel = min + ((max - min) * n) / NIVELES;
    for (let j = 0; j < FILAS; j++) {
      for (let i = 0; i < COLUMNAS; i++) {
        const a = malla[j][i];           // esquina superior izquierda
        const b = malla[j][i + 1];       // superior derecha
        const c = malla[j + 1][i + 1];   // inferior derecha
        const e = malla[j + 1][i];       // inferior izquierda
        const cruces = [];
        // Punto donde la curva cruza cada lado de la celda (interpolación lineal)
        if ((a < nivel) !== (b < nivel)) cruces.push((i + (nivel - a) / (b - a)) * dx, j * dy);
        if ((b < nivel) !== (c < nivel)) cruces.push((i + 1) * dx, (j + (nivel - b) / (c - b)) * dy);
        if ((e < nivel) !== (c < nivel)) cruces.push((i + (nivel - e) / (c - e)) * dx, (j + 1) * dy);
        if ((a < nivel) !== (e < nivel)) cruces.push(i * dx, (j + (nivel - a) / (e - a)) * dy);
        for (let k = 0; k + 3 < cruces.length; k += 4) segmentos.push(cruces[k], cruces[k + 1], cruces[k + 2], cruces[k + 3]);
      }
    }
  }
  return segmentos;
}

function pintar(lienzo, segmentos) {
  const caja = lienzo.getBoundingClientRect();
  if (caja.width < 2 || caja.height < 2) return;
  const densidad = Math.min(window.devicePixelRatio || 1, 1.5);
  lienzo.width = Math.round(caja.width * densidad);
  lienzo.height = Math.round(caja.height * densidad);
  const ctx = lienzo.getContext('2d');
  if (!ctx) return;

  // El dibujo de referencia cubre el lienzo sin deformarse, centrado
  const escala = Math.max(lienzo.width / ANCHO, lienzo.height / ALTO);
  const ox = (lienzo.width - ANCHO * escala) / 2;
  const oy = (lienzo.height - ALTO * escala) / 2;
  ctx.beginPath();
  for (let k = 0; k < segmentos.length; k += 4) {
    ctx.moveTo(ox + segmentos[k] * escala, oy + segmentos[k + 1] * escala);
    ctx.lineTo(ox + segmentos[k + 2] * escala, oy + segmentos[k + 3] * escala);
  }
  ctx.strokeStyle = '#f4efe6';
  ctx.lineWidth = densidad;
  ctx.lineCap = 'round';
  ctx.stroke();

  // Se desvanece hacia los bordes (queda horneado en la imagen: sin máscaras de CSS)
  const centroX = lienzo.width / 2;
  const centroY = lienzo.height / 2;
  ctx.globalCompositeOperation = 'destination-in';
  ctx.save();
  ctx.translate(centroX, centroY);
  ctx.scale(centroX * 1.25, centroY * 1.1);
  const fundido = ctx.createRadialGradient(0, 0, 0.3, 0, 0, 1);
  fundido.addColorStop(0, 'rgba(0,0,0,1)');
  fundido.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = fundido;
  ctx.fillRect(-1, -1, 2, 2);
  ctx.restore();
  ctx.globalCompositeOperation = 'source-over';
}

export function iniciarRelieve() {
  document.querySelectorAll('canvas[data-relieve]').forEach((lienzo) => {
    const segmentos = calcularCurvas(Number(lienzo.dataset.relieve) || 1);
    pintar(lienzo, segmentos);
    alRedimensionar(lienzo, () => pintar(lienzo, segmentos));
  });
}
