export const fragmentShader = /* glsl */ `
uniform vec3 uColor;
uniform vec3 uColorAlt1;
uniform vec3 uColorAlt2;
uniform vec3 uColorAlt3;

varying float vAlpha;
varying float vColorVariant;
varying float vDensity;

void main() {
  float dist = length(gl_PointCoord - vec2(0.5));
  if (dist > 0.45) discard;

  vec3 col;
  if (vColorVariant < 0.4) {
    col = uColor;
  } else if (vColorVariant < 0.65) {
    col = uColorAlt1;
  } else if (vColorVariant < 0.85) {
    col = uColorAlt2;
  } else {
    col = uColorAlt3;
  }

  col = mix(col, vec3(1.0), (1.0 - vDensity) * 0.15);

  gl_FragColor = vec4(col, vAlpha);
}
`;
