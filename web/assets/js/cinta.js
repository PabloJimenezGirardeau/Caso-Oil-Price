// Cinta de cotizaciones del hero: el último valor del CSV del proyecto y su variación diaria.
// No son cotizaciones en directo, y la primera celda lo dice. Sin rojo ni verde: el signo basta.

import { fecha, numero, variacion } from './formato.js';

export function iniciarCinta(d) {
  const cinta = document.getElementById('cinta');
  const { fecha: dia, valores } = d.cotizaciones;

  const aviso = document.createElement('div');
  aviso.className = 'cinta-celda cinta-aviso';
  aviso.innerHTML = `<span>Datos a ${fecha(dia)}</span><span>No es tiempo real</span>`;
  cinta.appendChild(aviso);

  for (const v of valores) {
    const celda = document.createElement('div');
    celda.className = 'cinta-celda';
    const nombre = document.createElement('span');
    nombre.className = 'cinta-nombre';
    nombre.textContent = v.nombre;
    const valor = document.createElement('span');
    valor.textContent = numero(v.valor, 2);
    const cambio = document.createElement('span');
    cambio.className = 'cinta-var';
    cambio.textContent = variacion(v.variacion);
    celda.append(nombre, valor, cambio);
    cinta.appendChild(celda);
  }
}
