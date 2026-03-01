export const fragmentShader = /* glsl */ `
uniform vec3 uColor;
uniform vec3 uColorAlt1;
uniform vec3 uColorAlt2;
uniform vec3 uColorAlt3;

varying float vAlpha;
varying float vColorVariant;
varying float vDensity;

void main() {
  // Hard circular dot — crisp stipple, no soft edges
  float dist = length(gl_PointCoord - vec2(0.5));
  if (dist > 0.45) discard;

  // Pick from 4 color variants based on per-particle random
  vec3 col;
  if (vColorVariant < 0.4) {
    col = uColor;             // 40% primary
  } else if (vColorVariant < 0.65) {
    col = uColorAlt1;         // 25% lighter tint
  } else if (vColorVariant < 0.85) {
    col = uColorAlt2;         // 20% darker shade
  } else {
    col = uColorAlt3;         // 15% complementary accent
  }

  // Slight brightness variation based on density (core = richer, edges = lighter)
  col = mix(col, vec3(1.0), (1.0 - vDensity) * 0.15);

  gl_FragColor = vec4(col, vAlpha);
}
`;
