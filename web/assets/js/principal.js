// Punto de entrada: carga los datos y arranca cada parte de la web por separado, de modo que
// un fallo en una sección no deje sin funcionar a las demás.

import { cargarDatos } from './datos.js';
import { enlazar } from './formato.js';
import { crearCrudo } from './crudo.js';
import { iniciarCinta } from './cinta.js';
import { iniciarHero } from './hero.js';
import { iniciarPrevision } from './prevision.js';
import { iniciarCalma } from './calma.js';
import { iniciarEspejismo } from './espejismo.js';
import { iniciarHallazgos, iniciarMetodo, iniciarTabla, iniciarExamen } from './secciones.js';
import { iniciarCiclo } from './ciclo.js';
import { iniciarRelieve } from './relieve.js';
import { iniciarMovimiento } from './movimiento.js';

const reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Aviso discreto en una esquina (datos de ejemplo, o error al cargar) */
function avisar(texto) {
  const aviso = document.createElement('p');
  aviso.className = 'aviso-datos';
  aviso.setAttribute('role', 'status');
  aviso.textContent = texto;
  document.body.appendChild(aviso);
}

/** Ejecuta un arranque y, si falla, lo anota sin detener el resto */
function probar(nombre, arranque) {
  try {
    return arranque();
  } catch (error) {
    console.error(`[${nombre}]`, error);
    return null;
  }
}

/** Espera a las fuentes (como mucho 2,5 s): las medidas del hero dependen de ellas */
const fuentesListas = () => Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 2500))]);

async function iniciar() {
  let d;
  try {
    d = await cargarDatos();
  } catch (error) {
    console.error(error);
    document.documentElement.classList.add('rescate');
    avisar('No se han podido cargar los datos. Abre la web con un servidor local (ver web/README.md).');
    return;
  }
  if (d.ejemplo.length) avisar(`Datos de ejemplo: ${d.ejemplo.join(', ')}`);

  enlazar(d);
  await fuentesListas();

  const crudo = probar('crudo', () => crearCrudo(document.getElementById('hero-crudo'), { quieto: reducido }));
  // El fondo fijo de toda la página. Mientras el hero (que tiene el suyo) llena la pantalla, se pausa
  const fondo = probar('fondo', () => crearCrudo(document.getElementById('fondo-crudo'),
    { quieto: reducido, brillo: 1.8, tiempoInicial: 80 }));
  const hero = document.getElementById('hero');
  if (fondo && !reducido && hero) {
    new IntersectionObserver(([e]) => {
      fondo.ocultar(e.intersectionRatio >= 0.85 && e.boundingClientRect.height >= window.innerHeight * 0.85);
    }, { threshold: [0, 0.5, 0.85, 1] }).observe(hero);
  }
  probar('cinta', () => iniciarCinta(d));
  probar('hero', () => iniciarHero(d, { crudo, reducido }));
  probar('prevision', () => iniciarPrevision(d, { reducido }));
  probar('hallazgos', () => iniciarHallazgos(d));
  probar('ciclo', () => iniciarCiclo(d));
  probar('calma', () => iniciarCalma(d, { reducido }));
  probar('espejismo', () => iniciarEspejismo(d));
  probar('metodo', () => iniciarMetodo(d));
  probar('tabla', () => iniciarTabla(d));
  probar('examen', () => iniciarExamen(d));
  probar('relieve', () => iniciarRelieve());
  probar('movimiento', () => iniciarMovimiento(d, { reducido }));

  window.__webLista = true;
}

iniciar();
