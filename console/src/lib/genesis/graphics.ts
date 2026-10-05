export type StageFrame = {
  cores: number;
  progress: number;
  running: boolean;
  arms: number;
};

export type GraphicsMount = (canvas: HTMLCanvasElement, read: () => StageFrame) => () => void;

let current: GraphicsMount = mountFluid;

/** Replace the field before the next mount. The shell does not need to change. */
export function registerGraphics(next: GraphicsMount) {
  current = next;
}

export function mountGraphics(canvas: HTMLCanvasElement, read: () => StageFrame) {
  return current(canvas, read);
}

const VERT = `attribute vec2 a;void main(){gl_Position=vec4(a,0.0,1.0);}`;

const FRAG = `precision mediump float;
uniform vec2 uRes;
uniform float uTime;
uniform float uRun;
uniform float uProg;
uniform vec2 uPointer;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){
  vec2 i=floor(p);vec2 f=fract(p);
  float a=hash(i);float b=hash(i+vec2(1.0,0.0));
  float c=hash(i+vec2(0.0,1.0));float d=hash(i+vec2(1.0,1.0));
  vec2 u=f*f*(3.0-2.0*f);
  return mix(mix(a,b,u.x),mix(c,d,u.x),u.y);
}
float fbm(vec2 p){
  float v=0.0;float a=0.5;
  for(int i=0;i<5;i++){v+=a*noise(p);p=p*2.03+vec2(1.7,9.2);a*=0.5;}
  return v;
}
void main(){
  vec2 p=(gl_FragCoord.xy-0.5*uRes)/min(uRes.x,uRes.y);
  vec2 pull=(uPointer-0.5)*0.35;
  p+=pull;
  float speed=0.07+uRun*0.11;
  float t=uTime*speed;
  vec2 q=vec2(fbm(p+vec2(0.0,t)),fbm(p+vec2(5.2,1.3)-t));
  vec2 r=vec2(fbm(p+2.2*q+vec2(1.7,9.2)+t*0.6),fbm(p+2.2*q+vec2(8.3,2.8)-t*0.45));
  float f=fbm(p+2.6*r);
  float ridge=pow(smoothstep(0.35,0.82,f),1.4);
  vec3 ink=vec3(0.08,0.16,0.2);
  vec3 deep=vec3(0.1,0.32,0.4);
  vec3 ice=vec3(0.78,0.95,0.98);
  vec3 tide=vec3(0.2,0.72,0.7);
  vec3 ember=vec3(0.95,0.5,0.32);
  vec3 col=mix(ink,deep,0.65);
  col=mix(col,tide,0.35+0.65*smoothstep(0.2,0.8,f));
  col=mix(col,ice,smoothstep(0.48,0.9,f)*0.7+ridge*0.45);
  col=mix(col,ember,uRun*smoothstep(0.45,0.85,r.y)*(0.35+0.55*uProg));
  float vig=smoothstep(1.4,0.2,length(p));
  col*=mix(0.9,1.2,vig)*(1.0+0.08*uProg);
  col=mix(col,ice,ridge*uProg*0.1);
  float grain=hash(gl_FragCoord.xy+fract(uTime)*10.0)-0.5;
  col+=grain*0.025;
  gl_FragColor=vec4(col,1.0);
}`;

function mountFluid(canvas: HTMLCanvasElement, read: () => StageFrame) {
  const gl = canvas.getContext("webgl", { antialias: false, alpha: false, premultipliedAlpha: false });
  if (!gl) return () => undefined;
  const program = programOf(gl, VERT, FRAG);
  if (!program) return () => undefined;
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(program, "a");
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const uRes = gl.getUniformLocation(program, "uRes");
  const uTime = gl.getUniformLocation(program, "uTime");
  const uRun = gl.getUniformLocation(program, "uRun");
  const uProg = gl.getUniformLocation(program, "uProg");
  const uPointer = gl.getUniformLocation(program, "uPointer");
  gl.useProgram(program);
  let raf = 0;
  let pointerX = 0.5;
  let pointerY = 0.5;
  let lost = false;
  const started = performance.now();
  const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const onMove = (event: PointerEvent) => {
    const rect = canvas.getBoundingClientRect();
    if (rect.width < 1) return;
    pointerX = (event.clientX - rect.left) / rect.width;
    pointerY = 1 - (event.clientY - rect.top) / rect.height;
  };
  window.addEventListener("pointermove", onMove);
  const paint = (now: number) => {
    if (lost) return;
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(1.5, window.devicePixelRatio || 1);
    const width = Math.max(1, Math.round(rect.width * dpr));
    const height = Math.max(1, Math.round(rect.height * dpr));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
      gl.viewport(0, 0, width, height);
    }
    const frame = read();
    gl.uniform2f(uRes, width, height);
    gl.uniform1f(uTime, motion.matches ? 4 : (now - started) / 1000);
    gl.uniform1f(uRun, frame.running ? 1 : 0);
    gl.uniform1f(uProg, Math.min(1, Math.max(0.04, frame.progress || 0)));
    gl.uniform2f(uPointer, pointerX, pointerY);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  };
  const stop = () => {
    if (!raf) return;
    window.cancelAnimationFrame(raf);
    raf = 0;
  };
  const tick = (now: number) => {
    raf = 0;
    if (lost || document.hidden) return;
    paint(now);
    if (!lost && !document.hidden && !motion.matches) raf = window.requestAnimationFrame(tick);
  };
  const onVisibility = () => {
    if (document.hidden) {
      stop();
      return;
    }
    if (lost) return;
    paint(performance.now());
    if (!motion.matches && !raf) raf = window.requestAnimationFrame(tick);
  };
  const onMotion = () => {
    stop();
    if (lost || document.hidden) return;
    paint(performance.now());
    if (!motion.matches) raf = window.requestAnimationFrame(tick);
  };
  const onLost = (event: Event) => {
    event.preventDefault();
    lost = true;
    stop();
  };
  document.addEventListener("visibilitychange", onVisibility);
  motion.addEventListener("change", onMotion);
  canvas.addEventListener("webglcontextlost", onLost);
  if (!document.hidden) {
    paint(started);
    if (!motion.matches) raf = window.requestAnimationFrame(tick);
  }
  return () => {
    stop();
    window.removeEventListener("pointermove", onMove);
    document.removeEventListener("visibilitychange", onVisibility);
    motion.removeEventListener("change", onMotion);
    canvas.removeEventListener("webglcontextlost", onLost);
    gl.deleteProgram(program);
    gl.deleteBuffer(buffer);
  };
}

function programOf(gl: WebGLRenderingContext, vert: string, frag: string) {
  const program = gl.createProgram();
  const vs = shader(gl, gl.VERTEX_SHADER, vert);
  const fs = shader(gl, gl.FRAGMENT_SHADER, frag);
  if (!program || !vs || !fs) return null;
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return null;
  return program;
}

function shader(gl: WebGLRenderingContext, type: number, source: string) {
  const made = gl.createShader(type);
  if (!made) return null;
  gl.shaderSource(made, source);
  gl.compileShader(made);
  if (!gl.getShaderParameter(made, gl.COMPILE_STATUS)) {
    gl.deleteShader(made);
    return null;
  }
  return made;
}
