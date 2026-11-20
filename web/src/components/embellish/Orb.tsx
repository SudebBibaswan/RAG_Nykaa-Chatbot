"use client";

import { useEffect, useRef } from "react";
import { useEmbellish } from "./store";

/**
 * embellish's orb: a liquid-gloss sphere rendered in a single fragment shader.
 * The surface is flowing fbm noise mixed between rani pink, deep plum and a marigold
 * sheen, with a fresnel rim and a soft specular highlight. Mode and voice level are
 * uniforms, so the orb breathes when idle, swirls when thinking and ripples with the voice.
 */

const VERT = `
attribute vec2 p;
varying vec2 vUv;
void main(){ vUv = p * 0.5 + 0.5; gl_Position = vec4(p, 0.0, 1.0); }`;

const FRAG = `
precision highp float;
varying vec2 vUv;
uniform float uTime;
uniform float uEnergy;   // 0 idle -> 1 thinking
uniform float uLevel;    // voice level 0..1
uniform float uRes;

float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1,0)), u.x), mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), u.x), u.y);
}
float fbm(vec2 p){
  float v = 0.0, a = 0.5;
  for (int i = 0; i < 5; i++){ v += a * noise(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; }
  return v;
}

void main(){
  vec2 uv = vUv * 2.0 - 1.0;
  float t = uTime * (0.18 + uEnergy * 0.55);

  // wobbling silhouette: the voice pushes the edge outwards in soft lobes
  float ang = atan(uv.y, uv.x);
  float wob = (noise(vec2(ang * 1.6 + t * 2.0, t)) - 0.5) * (0.035 + uLevel * 0.16);
  float r = length(uv) / (0.86 + wob + sin(uTime * 1.3) * 0.008 * (1.0 - uEnergy));
  float edge = 1.5 / uRes;
  float alpha = 1.0 - smoothstep(1.0 - edge * 2.0, 1.0, r);
  if (alpha <= 0.0) { gl_FragColor = vec4(0.0); return; }

  // sphere normal
  vec2 q = uv / (0.86 + wob);
  float z = sqrt(max(0.0, 1.0 - dot(q, q)));
  vec3 n = normalize(vec3(q, z));

  // flowing liquid surface, wrapped on the sphere
  vec2 sp = n.xy / (1.0 + n.z) * 1.6;
  vec2 w = vec2(fbm(sp * 1.5 + vec2(t, -t * 0.7)), fbm(sp * 1.5 + vec2(-t * 0.6, t)));
  float f = fbm(sp * 2.0 + w * (1.6 + uEnergy) + t * 0.4);

  vec3 plum   = vec3(0.235, 0.055, 0.180);
  vec3 rani   = vec3(0.886, 0.094, 0.357);
  vec3 petal  = vec3(0.992, 0.760, 0.840);
  vec3 gold   = vec3(0.941, 0.635, 0.231);

  vec3 col = mix(plum, rani, smoothstep(0.25, 0.65, f));
  col = mix(col, petal, smoothstep(0.62, 0.92, f) * 0.75);
  col += gold * pow(smoothstep(0.55, 0.95, w.x * f + uLevel * 0.25), 3.0) * (0.45 + uEnergy * 0.4);

  // lighting: soft key light, glossy specular, iridescent fresnel rim
  vec3 L = normalize(vec3(-0.45, 0.55, 0.75));
  float diff = clamp(dot(n, L), 0.0, 1.0);
  col *= 0.55 + 0.6 * diff;
  vec3 H = normalize(L + vec3(0.0, 0.0, 1.0));
  float spec = pow(clamp(dot(n, H), 0.0, 1.0), 60.0);
  col += vec3(1.0, 0.96, 0.98) * spec * 0.9;
  float fres = pow(1.0 - z, 2.4);
  col = mix(col, mix(petal, gold, 0.5 + 0.5 * sin(ang * 2.0 + uTime)), fres * 0.55);

  gl_FragColor = vec4(col * alpha, alpha);
}`;

export default function Orb({ className }: { className?: string }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const fallback = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const c = canvas.current!;
    const gl = c.getContext("webgl", { premultipliedAlpha: true, alpha: true, antialias: true });
    if (!gl) {
      c.style.display = "none";
      if (fallback.current) fallback.current.style.display = "block";
      return;
    }
    const sh = (type: number, src: string) => {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      return s;
    };
    const prog = gl.createProgram()!;
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, VERT));
    gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(prog);
    gl.useProgram(prog);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "p");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    const uTime = gl.getUniformLocation(prog, "uTime");
    const uEnergy = gl.getUniformLocation(prog, "uEnergy");
    const uLevel = gl.getUniformLocation(prog, "uLevel");
    const uRes = gl.getUniformLocation(prog, "uRes");

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    let energy = 0;
    let level = 0;
    const start = performance.now();

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const size = Math.max(1, Math.round(c.clientWidth * dpr));
      if (c.width !== size) {
        c.width = size;
        c.height = size;
      }
      gl.viewport(0, 0, c.width, c.height);
      gl.uniform1f(uRes, c.width);
    };
    const ro = new ResizeObserver(resize);
    ro.observe(c);
    resize();

    const frame = (now: number) => {
      const { orbMode, level: target } = useEmbellish.getState();
      const wantEnergy = orbMode === "thinking" ? 1 : orbMode === "idle" ? 0 : 0.45;
      energy += (wantEnergy - energy) * 0.04;
      level += (target - level) * 0.18;
      gl.uniform1f(uTime, reduce ? 4.0 : (now - start) / 1000);
      gl.uniform1f(uEnergy, energy);
      gl.uniform1f(uLevel, reduce ? 0 : level);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      if (!reduce) raf = requestAnimationFrame(frame);
    };
    const onVis = () => {
      cancelAnimationFrame(raf);
      if (!document.hidden) raf = requestAnimationFrame(frame);
    };
    document.addEventListener("visibilitychange", onVis);
    raf = requestAnimationFrame(frame);
    // reduced motion still re-renders on mode changes, without animating
    const unsub = reduce ? useEmbellish.subscribe(() => requestAnimationFrame(frame)) : () => {};

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      unsub();
      document.removeEventListener("visibilitychange", onVis);
      // Don't force-lose the context here: React re-runs effects on the same canvas in
      // development, and a lost context can't be re-acquired from that element.
      gl.deleteProgram(prog);
      gl.deleteBuffer(buf);
    };
  }, []);

  return (
    <div className={className} style={{ position: "relative" }}>
      <canvas ref={canvas} className="block h-full w-full" aria-hidden />
      <div
        ref={fallback}
        aria-hidden
        className="absolute inset-0 hidden rounded-full"
        style={{ background: "radial-gradient(circle at 35% 30%, #fdc2d6, #e2185b 45%, #3c0e2e 85%)" }}
      />
    </div>
  );
}
