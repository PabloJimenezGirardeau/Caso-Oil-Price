// El crudo en macro: una cinta de líquido negro y denso que cruza la pantalla y atrapa la luz
// en ámbar, con un rastro verdoso (el irisado de una película de aceite) solo en los bordes.
// Es un único shader de fragmentos sobre un triángulo que cubre el lienzo, en WebGL directo:
// no hace falta ninguna librería para esto.
//
// Rendimiento: resolución limitada (se pinta más pequeño y el CSS lo amplía, lo que además le da
// el desenfoque de una foto macro), unos 30 fotogramas por segundo, y solo mientras el lienzo
// está en pantalla. Sin WebGL, el lienzo muestra una imagen fija equivalente (clase «fija»).

const VERTICE = `
attribute vec2 posicion;
void main() { gl_Position = vec4(posicion, 0.0, 1.0); }
`;

const fragmento = (octavas) => `
precision highp float;

uniform vec2 uRes;         // tamaño del lienzo en píxeles
uniform float uTiempo;     // tiempo acumulado (avanza más deprisa con la agitación)
uniform vec2 uLuz;         // inclinación de la luz (la mueve un poco el cursor)
uniform float uPluma;      // posición horizontal (0-1) de la punta de la línea del Brent
uniform float uFuerza;     // cuánto ilumina la punta
uniform float uAgitacion;  // 0 = calma, 1 = tormenta
uniform float uBrillo;     // brillo general

float azar(vec2 p) {
  // Se redondea primero: cada esquina de la malla debe dar exactamente el mismo valor desde
  // las cuatro celdas que la comparten, aunque el compilador reordene las sumas (si no, se ven costuras)
  p = floor(p + 0.5);
  p = fract(p * vec2(0.1031, 0.1030));
  p += dot(p, p.yx + 33.33);
  return fract((p.x + p.y) * p.y);
}

// Tramado: aquí la posición no es entera y no hace falta redondear
float grano(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

// Ruido de valor con interpolación de quinto grado (suave, sin escalones)
float ruido(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  return mix(mix(azar(i), azar(i + vec2(1.0, 0.0)), u.x),
             mix(azar(i + vec2(0.0, 1.0)), azar(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p) {
  float suma = 0.0;
  float amplitud = 0.5;
  for (int i = 0; i < ${octavas}; i++) {
    suma += amplitud * ruido(p);
    p = p * 2.03 + vec2(11.7, 5.3);
    amplitud *= 0.5;
  }
  return suma;
}

// Eje de la cinta: sube de izquierda a derecha y ondula muy despacio
float ejeCinta(float x, float t) {
  return -0.15 + 0.10 * x + 0.10 * sin(x * 1.25 + 0.5 + t * 0.10) + 0.045 * sin(x * 2.9 - 1.1 - t * 0.07);
}

// Altura de la superficie: pliegues largos y paralelos a la cinta (como seda pesada), que un
// ruido lento hace serpentear. Devuelve (altura, ruido lento).
vec2 superficie(vec2 p, float t) {
  float v = p.y - ejeCinta(p.x, t);
  float lento = fbm(vec2(p.x * 0.55 + t * 0.035, v * 1.3 - t * 0.02));
  float altura = 0.50 * sin(v * 8.5 + lento * 7.0 + p.x * 0.9)
               + 0.26 * sin(v * 16.0 - lento * 10.0 + p.x * 1.9 + 1.3)
               + 0.10 * sin(v * 29.0 + lento * 15.0 - p.x * 1.1 + 2.1) * (1.0 + 1.4 * uAgitacion);
  return vec2(altura * (1.0 + 0.45 * uAgitacion), lento);
}

void main() {
  vec2 uv = gl_FragCoord.xy / uRes;
  float aspecto = uRes.x / uRes.y;
  vec2 p = vec2((uv.x - 0.5) * aspecto, uv.y - 0.5);
  float t = uTiempo;

  float v = p.y - ejeCinta(p.x, t);
  float ancho = 0.27 + 0.05 * sin(p.x * 0.9 + 1.7);
  float cinta = exp(-1.6 * (v / ancho) * (v / ancho));

  // Normal de la superficie por diferencias finitas
  float paso = 1.5 / uRes.y;
  vec2 centro = superficie(p, t);
  float hx = superficie(p + vec2(paso, 0.0), t).x;
  float hy = superficie(p + vec2(0.0, paso), t).x;
  vec3 normal = normalize(vec3(-(vec2(hx, hy) - centro.x) / paso * 0.085, 1.0));
  vec3 luz = normalize(vec3(-0.30 + uLuz.x, 0.52 + uLuz.y, 0.62));
  vec3 medio = normalize(luz + vec3(0.0, 0.0, 1.0));
  float nh = max(dot(normal, medio), 0.0);
  float reflejo = pow(nh, 90.0);   // el brillo vivo
  float lustre = pow(nh, 10.0);    // el halo que lo rodea

  // La luz no llega igual a toda la cinta: hay tramos en sombra
  float tramo = 0.22 + 0.78 * smoothstep(-0.45, 0.85, sin(p.x * 1.05 + 0.9 + t * 0.04) + 0.9 * (centro.y - 0.5));

  vec3 ambar = vec3(0.949, 0.573, 0.114);
  vec3 hondo = vec3(0.55, 0.26, 0.04);
  vec3 verde = vec3(0.30, 0.52, 0.46);

  float materia = cinta * tramo * uBrillo;
  vec3 color = vec3(0.014, 0.011, 0.008);
  color += hondo * lustre * 0.20 * materia;
  color += ambar * reflejo * 1.0 * materia;
  color += vec3(1.0, 0.86, 0.66) * pow(reflejo, 3.0) * 0.5 * materia;

  // Irisado: solo en el borde de la luz y hacia las orillas de la cinta
  float borde = smoothstep(0.25, 0.55, lustre) * (1.0 - smoothstep(0.55, 0.92, lustre));
  float orilla = smoothstep(0.35, 1.0, abs(v) / ancho);
  color += verde * borde * (0.04 + 0.22 * orilla) * materia;

  // La punta de la línea del Brent ilumina el crudo a su paso
  float lejos = (uv.x - uPluma) / 0.14;
  color *= 1.0 + 1.5 * uFuerza * exp(-lejos * lejos);

  // Viñeta y tramado (evita el bandeado en los degradados oscuros)
  color *= mix(0.55, 1.0, smoothstep(1.25, 0.25, length(vec2(p.x / aspecto * 1.6, p.y * 1.5))));
  color += (grano(gl_FragCoord.xy) - 0.5) / 255.0;

  gl_FragColor = vec4(color, 1.0);
}
`;

function compilar(gl, tipo, codigo) {
  const shader = gl.createShader(tipo);
  gl.shaderSource(shader, codigo);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
  return shader;
}

/**
 * Pinta el crudo en `lienzo`. Devuelve null si no hay WebGL (y deja la imagen fija).
 * opciones: quieto (un solo fotograma), brillo, tiempoInicial.
 * El objeto devuelto expone `estado`, que otros módulos modifican:
 *   luz [x, y], pluma (0-1), fuerza, agitacion (0-1).
 */
export function crearCrudo(lienzo, { quieto = false, brillo = 1, tiempoInicial = 12 } = {}) {
  const fallo = () => {
    lienzo.classList.add('fija');
    return null;
  };

  let gl = null;
  try {
    gl = lienzo.getContext('webgl', { alpha: false, antialias: false, depth: false, stencil: false, powerPreference: 'low-power' });
  } catch {
    gl = null;
  }
  if (!gl) return fallo();

  let programa;
  try {
    programa = gl.createProgram();
    gl.attachShader(programa, compilar(gl, gl.VERTEX_SHADER, VERTICE));
    gl.attachShader(programa, compilar(gl, gl.FRAGMENT_SHADER, fragmento(4)));
    gl.linkProgram(programa);
    if (!gl.getProgramParameter(programa, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(programa));
  } catch (error) {
    console.warn('Crudo: el shader no compila; se usa la imagen fija.', error);
    return fallo();
  }
  gl.useProgram(programa);

  // Un triángulo que cubre toda la pantalla
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const posicion = gl.getAttribLocation(programa, 'posicion');
  gl.enableVertexAttribArray(posicion);
  gl.vertexAttribPointer(posicion, 2, gl.FLOAT, false, 0, 0);

  const u = Object.fromEntries(['uRes', 'uTiempo', 'uLuz', 'uPluma', 'uFuerza', 'uAgitacion', 'uBrillo']
    .map((nombre) => [nombre, gl.getUniformLocation(programa, nombre)]));

  const estado = { luz: [0, 0], pluma: 0.5, fuerza: 0, agitacion: 0, brillo };
  // Valores suavizados: lo que se pinta persigue despacio a lo que se pide
  const suave = { luz: [0, 0], agitacion: 0 };
  let tiempo = tiempoInicial;
  let anterior = 0;
  let visible = false;
  let perdido = false;
  let cuadro = 0;

  function ajustarTamaño() {
    const densidad = Math.min(window.devicePixelRatio || 1, 1.5) * 0.7;
    const ancho = Math.max(2, Math.round(lienzo.clientWidth * densidad));
    const alto = Math.max(2, Math.round(lienzo.clientHeight * densidad));
    if (lienzo.width !== ancho || lienzo.height !== alto) {
      lienzo.width = ancho;
      lienzo.height = alto;
      gl.viewport(0, 0, ancho, alto);
    }
  }

  function pintar() {
    ajustarTamaño();
    gl.uniform2f(u.uRes, lienzo.width, lienzo.height);
    gl.uniform1f(u.uTiempo, tiempo);
    gl.uniform2f(u.uLuz, suave.luz[0], suave.luz[1]);
    gl.uniform1f(u.uPluma, estado.pluma);
    gl.uniform1f(u.uFuerza, estado.fuerza);
    gl.uniform1f(u.uAgitacion, suave.agitacion);
    gl.uniform1f(u.uBrillo, estado.brillo);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  function bucle(ahora) {
    cuadro = 0;
    if (!visible || perdido || document.hidden) return;
    cuadro = requestAnimationFrame(bucle);
    const dt = Math.min((ahora - anterior) / 1000, 0.1);
    if (dt < 0.03) return;   // ~30 fotogramas por segundo: el movimiento es lento
    anterior = ahora;
    suave.luz[0] += (estado.luz[0] - suave.luz[0]) * 0.06;
    suave.luz[1] += (estado.luz[1] - suave.luz[1]) * 0.06;
    suave.agitacion += (estado.agitacion - suave.agitacion) * 0.08;
    // En calma casi no se mueve; en tormenta, deprisa
    tiempo += dt * (1.0 + 5.0 * suave.agitacion);
    pintar();
  }

  function arrancar() {
    if (quieto || cuadro) return;
    anterior = performance.now();
    cuadro = requestAnimationFrame(bucle);
  }

  // Solo se anima mientras se ve
  const observador = new IntersectionObserver(([entrada]) => {
    visible = entrada.isIntersecting;
    if (visible) arrancar();
  });
  observador.observe(lienzo);
  document.addEventListener('visibilitychange', () => { if (!document.hidden && visible) arrancar(); });

  lienzo.addEventListener('webglcontextlost', (evento) => {
    evento.preventDefault();
    perdido = true;
    lienzo.classList.add('fija');
  });

  // Con «quieto» (reducir movimiento) se pinta un fotograma, y otro si cambia el tamaño
  new ResizeObserver(() => { if (!perdido && (quieto || !visible)) pintar(); }).observe(lienzo);
  pintar();

  return { estado, pintar };
}
