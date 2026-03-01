export const vertexShader = /* glsl */ `
uniform float uTime;
uniform float uScale;
uniform float uSpikiness;
uniform float uBreathRate;
uniform float uScatter;
uniform float uEntranceProgress;
uniform float uGhostOpacity;

attribute float aRandomSeed;
attribute float aDensity;
attribute float aColorVariant;

varying float vAlpha;
varying float vColorVariant;
varying float vDensity;

vec3 hash3(vec3 p) {
  p = vec3(
    dot(p, vec3(127.1, 311.7, 74.7)),
    dot(p, vec3(269.5, 183.3, 246.1)),
    dot(p, vec3(113.5, 271.9, 124.6))
  );
  return fract(sin(p) * 43758.5453123) * 2.0 - 1.0;
}

float simplex3d(vec3 p) {
  vec3 i = floor(p);
  vec3 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(
      mix(dot(hash3(i), f), dot(hash3(i + vec3(1,0,0)), f - vec3(1,0,0)), f.x),
      mix(dot(hash3(i + vec3(0,1,0)), f - vec3(0,1,0)), dot(hash3(i + vec3(1,1,0)), f - vec3(1,1,0)), f.x),
      f.y
    ),
    mix(
      mix(dot(hash3(i + vec3(0,0,1)), f - vec3(0,0,1)), dot(hash3(i + vec3(1,0,1)), f - vec3(1,0,1)), f.x),
      mix(dot(hash3(i + vec3(0,1,1)), f - vec3(0,1,1)), dot(hash3(i + vec3(1,1,1)), f - vec3(1,1,1)), f.x),
      f.y
    ),
    f.z
  );
}

void main() {
  vec3 pos = position;

  float distFromCenter = length(pos);
  vec3 dir = distFromCenter > 0.001 ? normalize(pos) : vec3(0.0, 1.0, 0.0);

  // Breathing
  float breath = sin(uTime * uBreathRate * 0.5 + aRandomSeed * 6.28318) * 0.03;
  pos += dir * breath;

  // Spikiness (noise displacement)
  float noise = simplex3d(pos * 2.0 + uTime * 0.3);
  pos += dir * noise * uSpikiness * 0.5;

  // Scatter
  pos += dir * uScatter * distFromCenter * 0.3;

  // Scale
  pos *= uScale;

  // Entrance animation: scatter -> converge
  vec3 scatteredPos = pos * 5.0 + dir * aRandomSeed * 8.0;
  pos = mix(scatteredPos, pos, uEntranceProgress);

  // Slow Y-axis rotation
  float angle = uTime * 0.15;
  float c = cos(angle);
  float s = sin(angle);
  pos = vec3(c * pos.x + s * pos.z, pos.y, -s * pos.x + c * pos.z);

  vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * mvPosition;

  // Tiny crisp dots matching background grid dot size (~1.5px on screen)
  float size = mix(0.8, 1.5, aRandomSeed) * (30.0 / -mvPosition.z);
  gl_PointSize = max(size, 0.5);

  // Alpha: core particles more opaque, edges more transparent, random variation
  float baseAlpha = smoothstep(0.0, 0.15, aDensity);
  float randomDim = 0.4 + aRandomSeed * 0.6; // some dots dimmer than others
  vAlpha = baseAlpha * randomDim * uGhostOpacity;

  vColorVariant = aColorVariant;
  vDensity = aDensity;
}
`;
