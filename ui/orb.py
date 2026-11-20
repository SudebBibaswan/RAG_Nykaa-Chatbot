"""embellish's orb for Streamlit: the same fragment shader as the storefront, injected with st.html.

The orb reads window.__embellishOrb ('idle' | 'thinking' | 'speaking') every frame, so a tiny
script elsewhere on the page can change its mood while an answer is being produced.
"""

FRAG = """
precision highp float;
varying vec2 vUv;
uniform float uTime, uEnergy, uLevel, uRes;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){ vec2 i=floor(p), f=fract(p); vec2 u=f*f*(3.0-2.0*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),u.x), mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),u.x), u.y); }
float fbm(vec2 p){ float v=0.0,a=0.5; for(int i=0;i<5;i++){ v+=a*noise(p); p=p*2.03+vec2(1.7,9.2); a*=0.5; } return v; }
void main(){
  vec2 uv = vUv*2.0-1.0;
  float t = uTime*(0.18+uEnergy*0.55);
  float ang = atan(uv.y, uv.x);
  float wob = (noise(vec2(ang*1.6+t*2.0, t))-0.5)*(0.035+uLevel*0.16);
  float r = length(uv)/(0.86+wob+sin(uTime*1.3)*0.008*(1.0-uEnergy));
  float edge = 1.5/uRes;
  float alpha = 1.0-smoothstep(1.0-edge*2.0, 1.0, r);
  if (alpha <= 0.0) { gl_FragColor = vec4(0.0); return; }
  vec2 q = uv/(0.86+wob);
  float z = sqrt(max(0.0, 1.0-dot(q,q)));
  vec3 n = normalize(vec3(q, z));
  vec2 sp = n.xy/(1.0+n.z)*1.6;
  vec2 w = vec2(fbm(sp*1.5+vec2(t,-t*0.7)), fbm(sp*1.5+vec2(-t*0.6,t)));
  float f = fbm(sp*2.0+w*(1.6+uEnergy)+t*0.4);
  vec3 plum=vec3(0.235,0.055,0.180), rani=vec3(0.886,0.094,0.357), petal=vec3(0.992,0.760,0.840), gold=vec3(0.941,0.635,0.231);
  vec3 col = mix(plum, rani, smoothstep(0.25,0.65,f));
  col = mix(col, petal, smoothstep(0.62,0.92,f)*0.75);
  col += gold*pow(smoothstep(0.55,0.95,w.x*f+uLevel*0.25),3.0)*(0.45+uEnergy*0.4);
  vec3 L = normalize(vec3(-0.45,0.55,0.75));
  col *= 0.55+0.6*clamp(dot(n,L),0.0,1.0);
  vec3 H = normalize(L+vec3(0.0,0.0,1.0));
  col += vec3(1.0,0.96,0.98)*pow(clamp(dot(n,H),0.0,1.0),60.0)*0.9;
  float fres = pow(1.0-z, 2.4);
  col = mix(col, mix(petal, gold, 0.5+0.5*sin(ang*2.0+uTime)), fres*0.55);
  gl_FragColor = vec4(col*alpha, alpha);
}
"""

SCRIPT = """
<script>
(function start(tries) {
  // Streamlit may run this before the canvas is attached; wait for it.
  const c = document.getElementById("embellish-orb");
  if (!c || !c.clientWidth) { if (tries < 240) requestAnimationFrame(() => start(tries + 1)); return; }
  if (c.dataset.ready) return;
  c.dataset.ready = "1";
  const gl = c.getContext("webgl", { premultipliedAlpha: true, alpha: true, antialias: true });
  if (!gl) { c.parentElement.classList.add("no-gl"); return; }
  const sh = (t, s) => { const x = gl.createShader(t); gl.shaderSource(x, s); gl.compileShader(x); return x; };
  const p = gl.createProgram();
  gl.attachShader(p, sh(gl.VERTEX_SHADER, "attribute vec2 p; varying vec2 vUv; void main(){ vUv=p*0.5+0.5; gl_Position=vec4(p,0.0,1.0); }"));
  gl.attachShader(p, sh(gl.FRAGMENT_SHADER, FRAG_SRC));
  gl.linkProgram(p); gl.useProgram(p);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,1,1]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(p, "p"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  const u = (n) => gl.getUniformLocation(p, n);
  const uT = u("uTime"), uE = u("uEnergy"), uL = u("uLevel"), uR = u("uRes");
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const size = Math.round(c.clientWidth * dpr) || 200;
  c.width = size; c.height = size; gl.viewport(0, 0, size, size); gl.uniform1f(uR, size);
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let e = 0, l = 0; const t0 = performance.now();
  const frame = (now) => {
    if (!c.isConnected) return;
    const mode = window.__embellishOrb || "idle";
    e += ((mode === "thinking" ? 1 : mode === "speaking" ? 0.45 : 0) - e) * 0.05;
    const want = mode === "speaking" ? 0.35 + 0.3 * Math.sin(now / 90) * Math.sin(now / 37) : 0;
    l += (want - l) * 0.2;
    gl.uniform1f(uT, reduce ? 4 : (now - t0) / 1000); gl.uniform1f(uE, e); gl.uniform1f(uL, reduce ? 0 : l);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    if (!reduce || mode !== "idle") requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
})(0);
</script>
"""


def orb_html() -> str:
    import json

    return (
        '<div class="orb-wrap"><span class="halo"></span><canvas id="embellish-orb" aria-hidden="true"></canvas></div>'
        # Streamlit's sanitizer drops any script containing "<" followed by a word character
        # (the shader has "i<5"), so escape "<" inside the embedded string.
        + SCRIPT.replace("FRAG_SRC", json.dumps(FRAG).replace("<", "\\u003c"))
        + "<style>.orb-wrap.no-gl{border-radius:50%;background:radial-gradient(circle at 34% 30%,#fff2f6 0%,#fdc2d6 18%,#e2185b 52%,#3c0e2e 92%)}</style>"
    )


def orb_mode(mode: str) -> str:
    """A tiny script that changes the orb's mood."""
    return f'<script>window.__embellishOrb = "{mode}";</script>'
