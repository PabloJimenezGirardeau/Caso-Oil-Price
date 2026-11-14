// Carga de los datos. La web no calcula resultados: lee los JSON que genera
// scripts/exportar_web.py en web/data/ y, como mucho, redondea o resta dos cifras.

const ARCHIVOS = ['historico', 'cotizaciones', 'validacion', 'rango', 'espejismo', 'prevision', 'test', 'en_vivo'];

async function leerJSON(nombre) {
  const respuesta = await fetch(`data/${nombre}.json`, { cache: 'no-cache' });
  if (!respuesta.ok) throw new Error(`No se pudo leer data/${nombre}.json (${respuesta.status})`);
  return respuesta.json();
}

export async function cargarDatos() {
  const lista = await Promise.all(ARCHIVOS.map(leerJSON));
  const d = Object.fromEntries(ARCHIVOS.map((nombre, i) => [nombre, lista[i]]));

  // Archivos marcados como de ejemplo: la web lo avisa
  d.ejemplo = ARCHIVOS.filter((nombre) => d[nombre].ejemplo === true);

  // Cifras derivadas que se repiten en los textos (todas salen de los JSON)
  const plazos = d.rango.plazos;
  d.calc = {
    sesiones: d.historico.fechas.length,
    año_ini: Number(d.historico.fechas[0].slice(0, 4)),
    año_fin: Number(d.historico.fechas.at(-1).slice(0, 4)),
    años: d.validacion.plazos.medio.criterio.años,
    años_largo: plazos.largo.años.length,
    mejora_corto: Math.round(100 * plazos.corto.mejora),
    mejora_medio: Math.round(100 * plazos.medio.mejora),
    mejora_largo: Math.round(100 * plazos.largo.mejora),
    exceso: Math.round(100 * (d.espejismo.medidas.precios.nota - 1)),
  };
  return d;
}
