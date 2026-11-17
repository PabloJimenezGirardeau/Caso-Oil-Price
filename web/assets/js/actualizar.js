// El botón «Actualizar datos». Solo funciona con la aplicación en marcha (python app/app.py): Python sirve
// esta misma web y, al pulsarlo, descarga los datos de FRED y Yahoo Finance y los pasa por los modelos
// finales, ya entrenados (no se reentrena nada). La web se vuelve a pintar con su propio código: mismo
// diseño, datos nuevos. En GitHub Pages no hay Python detrás: se enseña la previsión publicada y un enlace
// a cómo ejecutar la aplicación en local.

import { calcular } from './datos.js';
import { enlazar, fecha } from './formato.js';
import { iniciarCinta } from './cinta.js';

/** ¿Sirve la web la aplicación? (en GitHub Pages, la ruta no existe) */
async function preguntarServidor() {
  try {
    const respuesta = await fetch('api/estado', { cache: 'no-store' });
    if (!respuesta.ok) return null;
    const estado = await respuesta.json();
    return estado && estado.servidor === true ? estado : null;
  } catch {
    return null;
  }
}

export async function iniciarActualizar(d, { prevision }) {
  const boton = document.getElementById('pv-actualizar');
  const enlaceLocal = document.getElementById('pv-local');
  const estado = document.getElementById('pv-estado');
  if (!boton || !estado) return;
  const entrenados = (iso) => `modelos entrenados hasta el ${fecha(iso)}`;

  const servidor = await preguntarServidor();
  if (!servidor) {
    enlaceLocal.hidden = false;
    estado.textContent = `Previsión publicada con los datos hasta el ${fecha(d.prevision.fecha)}. `
      + 'Para descargar los de hoy y pasarlos por los modelos, ejecuta la aplicación en local.';
    return;
  }

  boton.hidden = false;
  estado.textContent = `Previsión publicada con los datos hasta el ${fecha(d.prevision.fecha)} · ${entrenados(servidor.modelos_hasta)}. `
    + 'Al actualizar, los datos de hoy pasan por los modelos, sin reentrenarlos.';

  boton.addEventListener('click', async () => {
    boton.disabled = true;
    boton.textContent = 'Actualizando…';
    estado.textContent = 'Descargando los datos de FRED y Yahoo Finance y pasándolos por los modelos…';
    try {
      const respuesta = await fetch('api/actualizar', { method: 'POST' });
      const nuevo = await respuesta.json();
      if (!respuesta.ok) throw new Error(nuevo.error || `error ${respuesta.status}`);

      // Los datos nuevos ocupan el lugar de los publicados y cada parte se pinta con su código de siempre
      d.prevision = nuevo.prevision;
      d.historico = nuevo.historico;
      d.cotizaciones = nuevo.cotizaciones;
      calcular(d);
      enlazar(d);
      if (prevision) prevision.refrescar();
      const cinta = document.getElementById('cinta');
      if (cinta) {
        cinta.textContent = '';
        iniciarCinta(d);
      }

      const e = nuevo.estado;
      estado.textContent = e.origen.startsWith('descargados')
        ? `Actualizada a las ${e.hora} con los datos de FRED y Yahoo Finance hasta el ${fecha(e.datos_hasta)} · `
          + `${entrenados(e.modelos_hasta)}, sin reentrenar.`
        : `Sin datos nuevos: previsión de las ${e.hora} con ${e.origen} · ${entrenados(e.modelos_hasta)}, sin reentrenar.`;
      if (e.avisos.length) {
        console.warn('[actualizar]', ...e.avisos);
        estado.textContent += ' No se han podido descargar todos los datos: se usan los últimos disponibles.';
      }
    } catch (error) {
      console.error('[actualizar]', error);
      estado.textContent = `No se ha podido actualizar (${error.message}). Sigue la previsión anterior.`;
    } finally {
      boton.disabled = false;
      boton.textContent = 'Actualizar datos';
    }
  });
}
