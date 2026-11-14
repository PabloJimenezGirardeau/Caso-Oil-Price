// Movimiento de la página: scroll suave, entradas al hacer scroll, títulos por líneas,
// contadores y el desplazamiento leve de las curvas de nivel.
//
// Principios: lento y con curvas suaves (sin rebotes), pocas cosas a la vez, nada en bucle.
// Con «reducir movimiento» no se anima nada: todo aparece en su estado final.

import { numero, leer } from './formato.js';

export function iniciarMovimiento(d, { reducido }) {
  const { gsap, ScrollTrigger, SplitText, Lenis } = window;

  // La barra superior se vuelve translúcida al empezar a bajar
  const barra = document.getElementById('barra');
  const alDesplazar = () => barra.classList.toggle('fija', window.scrollY > 24);
  window.addEventListener('scroll', alDesplazar, { passive: true });
  alDesplazar();

  const contadores = [...document.querySelectorAll('[data-cuenta]')];
  const valorDe = (el) => leer(d, el.dataset.cuenta);

  if (reducido || !gsap || !ScrollTrigger) {
    contadores.forEach((el) => { el.textContent = numero(valorDe(el)); });
    document.documentElement.classList.add('rescate');   // por si faltan las librerías: todo visible
    return;
  }
  gsap.registerPlugin(ScrollTrigger, SplitText);

  // --- Scroll suave ---------------------------------------------------------------------------
  if (Lenis) {
    const lenis = new Lenis({ lerp: 0.12, anchors: true });
    lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add((tiempo) => lenis.raf(tiempo * 1000));
    gsap.ticker.lagSmoothing(0);
  }

  /** Llama a `hacer(elementos)` con los elementos que van entrando en pantalla (una sola vez cada
      uno). Se usa IntersectionObserver: no depende de la velocidad ni de los saltos del scroll. */
  const alEntrar = (elementos, hacer, margen = '0px 0px -8% 0px') => {
    const observador = new IntersectionObserver((entradas) => {
      const visibles = entradas.filter((e) => e.isIntersecting).map((e) => e.target);
      if (!visibles.length) return;
      visibles.forEach((el) => observador.unobserve(el));
      hacer(visibles);
    }, { rootMargin: margen });
    elementos.forEach((el) => observador.observe(el));
  };

  /** Título por líneas: cada línea sube desde detrás de una máscara. Al acabar se deshace la
      división, para no dejar máscaras que recorten las cursivas. */
  const porLineas = (elemento, retraso = 0) => {
    gsap.set(elemento, { opacity: 1 });
    const division = SplitText.create(elemento, { type: 'lines', mask: 'lines' });
    gsap.from(division.lines, {
      yPercent: 110, duration: 0.95, ease: 'power3.out', stagger: 0.09, delay: retraso,
      onComplete: () => division.revert(),
    });
  };

  // --- Hero: distintivo, título y botones, escalonados -----------------------------------------
  gsap.fromTo('[data-hero]', { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.8, ease: 'power2.out', stagger: 0.1, delay: 0.1 });
  gsap.set('.hero-titulo', { opacity: 1 });
  document.querySelectorAll('[data-hero-linea]').forEach((lineaTitulo, i) => porLineas(lineaTitulo, 0.2 + i * 0.12));

  // --- Títulos de sección -------------------------------------------------------------------
  alEntrar([...document.querySelectorAll('[data-titulo]')], (titulos) => titulos.forEach((titulo) => porLineas(titulo)), '0px 0px -12% 0px');

  // --- Entradas: texto y tarjetas, escalonadas (las que entran a la vez, una tras otra) ---------
  gsap.set('[data-revela]', { y: 22 });
  alEntrar([...document.querySelectorAll('[data-revela]')], (elementos) => {
    gsap.to(elementos, { opacity: 1, y: 0, duration: 0.85, ease: 'power2.out', stagger: 0.08 });
  });

  // --- Contadores: solo los que cuentan algo (años y sesiones) ---------------------------------
  contadores.forEach((el) => { el.textContent = numero(0); });
  alEntrar(contadores, (elementos) => elementos.forEach((el) => {
    const cuenta = { v: 0 };
    gsap.to(cuenta, { v: valorDe(el), duration: 1.5, ease: 'power2.out', onUpdate: () => { el.textContent = numero(Math.round(cuenta.v)); } });
  }));

  // --- Curvas de nivel: se desplazan apenas con el scroll -------------------------------------
  document.querySelectorAll('canvas[data-relieve]').forEach((relieve) => {
    gsap.fromTo(relieve, { y: -50 }, { y: 50, ease: 'none',
      scrollTrigger: { trigger: relieve.parentElement, start: 'top bottom', end: 'bottom top', scrub: true } });
  });

  // --- Método: el eje del tiempo se rellena con el scroll ------------------------------------
  const tiempo = document.getElementById('tiempo');
  if (tiempo && tiempo.fijarAvance) {
    tiempo.classList.add('con-scroll');
    tiempo.fijarAvance(0);
    ScrollTrigger.create({ trigger: tiempo, start: 'top 80%', end: 'top 28%', scrub: true, onUpdate: (self) => tiempo.fijarAvance(self.progress) });
  }

  // Las posiciones dependen de fuentes y gráficos ya colocados
  window.addEventListener('load', () => ScrollTrigger.refresh());
}
