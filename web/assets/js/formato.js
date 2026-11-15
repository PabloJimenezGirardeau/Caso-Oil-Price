// Formato español de cifras y fechas: coma decimal, punto de miles, espacio antes de % y $.
// Se hace a mano (y no con Intl) para que 6501 salga siempre como «6.501» en cualquier navegador.

const ESPACIO = ' ';   // espacio de no separación
const MENOS = '−';     // signo menos tipográfico
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
  'octubre', 'noviembre', 'diciembre'];

/** 6501 → «6.501»; 107.03 → «107,03» */
export function numero(valor, decimales = 0) {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return '—';
  const [entero, fraccion] = Math.abs(valor).toFixed(decimales).split('.');
  const miles = entero.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return (valor < 0 ? MENOS : '') + miles + (fraccion ? ',' + fraccion : '');
}

/** 107.03 → «107,03 $» */
export function dolares(valor, decimales = 2) {
  return valor === null || valor === undefined ? '—' : numero(valor, decimales) + ESPACIO + '$';
}

/** 0.82 → «82 %» (el valor llega como proporción) */
export function porcentaje(proporcion, decimales = 0) {
  return proporcion === null || proporcion === undefined ? '—' : numero(100 * proporcion, decimales) + ESPACIO + '%';
}

/** −0.34 → «−0,34 %»; 3.54 → «+3,54 %» (el valor llega ya en %) */
export function variacion(valor, decimales = 2) {
  if (valor === null || valor === undefined) return '—';
  return (valor > 0 ? '+' : '') + numero(valor, decimales) + ESPACIO + '%';
}

function partes(iso) {
  const [año, mes, dia] = iso.split('-').map(Number);
  return { año, mes, dia };
}

/** «2026-11-03» → «3/11/2026» */
export function fecha(iso) {
  if (!iso) return '—';
  const { año, mes, dia } = partes(iso);
  return `${dia}/${mes}/${año}`;
}

/** «2026-11-03» → «3 nov 2026» */
export function fechaCorta(iso) {
  if (!iso) return '—';
  const { año, mes, dia } = partes(iso);
  return `${dia} ${MESES[mes - 1].slice(0, 3)} ${año}`;
}

/** «2027-01-29» → «enero de 2027» */
export function mesAño(iso) {
  if (!iso) return '—';
  const { año, mes } = partes(iso);
  return `${MESES[mes - 1]} de ${año}`;
}

/** Busca «a.b.c» dentro de un objeto */
function leer(objeto, ruta) {
  return ruta.split('.').reduce((o, clave) => (o === null || o === undefined ? o : o[clave]), objeto);
}

const FORMATOS = {
  entero: (v) => numero(v, 0),
  numero2: (v) => numero(v, 2),
  numero3: (v) => numero(v, 3),
  pct0: (v) => porcentaje(v, 0),
  puntos: (v) => numero(100 * v, 0),   // proporción → puntos porcentuales, sin signo %
  fecha,
  dolares: (v) => dolares(v),
  variacion1: (v) => variacion(v, 1),   // ya en % → «+13,4 %»
};

/** Rellena todos los [data-d="ruta"] con el dato correspondiente, con el formato de data-f. */
export function enlazar(datos, raiz = document) {
  raiz.querySelectorAll('[data-d]').forEach((el) => {
    const valor = leer(datos, el.dataset.d);
    if (valor === null || valor === undefined) return;   // dato pendiente: se queda la raya
    const formato = FORMATOS[el.dataset.f];
    el.textContent = formato ? formato(valor) : String(valor);
  });
}

export { leer };
