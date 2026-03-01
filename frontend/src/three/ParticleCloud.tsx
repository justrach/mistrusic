import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { generateParticles } from './geometry';
import { vertexShader } from './stipple.vert';
import { fragmentShader } from './stipple.frag';
import { ShaderUniforms, DEFAULT_UNIFORMS } from './featureMap';
import { stipplePalette } from './colors';
import { LERP_FACTOR } from '../constants';

interface Props {
  color: string;
  targetUniforms: ShaderUniforms;
  entranceProgress: number;
  ghostOpacity: number;
  onClick?: () => void;
  position?: [number, number, number];
}

export function ParticleCloud({
  color,
  targetUniforms,
  entranceProgress,
  ghostOpacity,
  onClick,
  position = [0, 0, 0],
}: Props) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  const { positions, seeds, densities, colorVariants } = useMemo(() => generateParticles(), []);

  const [c0, c1, c2, c3] = stipplePalette(color);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uScale: { value: DEFAULT_UNIFORMS.uScale },
      uSpikiness: { value: DEFAULT_UNIFORMS.uSpikiness },
      uBreathRate: { value: DEFAULT_UNIFORMS.uBreathRate },
      uScatter: { value: DEFAULT_UNIFORMS.uScatter },
      uEntranceProgress: { value: 0 },
      uGhostOpacity: { value: ghostOpacity },
      uColor: { value: new THREE.Color(c0) },
      uColorAlt1: { value: new THREE.Color(c1) },
      uColorAlt2: { value: new THREE.Color(c2) },
      uColorAlt3: { value: new THREE.Color(c3) },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  useFrame(({ clock }) => {
    const mat = materialRef.current;
    if (!mat) return;

    mat.uniforms.uTime.value = clock.getElapsedTime();

    mat.uniforms.uScale.value += (targetUniforms.uScale - mat.uniforms.uScale.value) * LERP_FACTOR;
    mat.uniforms.uSpikiness.value += (targetUniforms.uSpikiness - mat.uniforms.uSpikiness.value) * LERP_FACTOR;
    mat.uniforms.uBreathRate.value += (targetUniforms.uBreathRate - mat.uniforms.uBreathRate.value) * LERP_FACTOR;
    mat.uniforms.uScatter.value += (targetUniforms.uScatter - mat.uniforms.uScatter.value) * LERP_FACTOR;
    mat.uniforms.uEntranceProgress.value += (entranceProgress - mat.uniforms.uEntranceProgress.value) * LERP_FACTOR;
    mat.uniforms.uGhostOpacity.value += (ghostOpacity - mat.uniforms.uGhostOpacity.value) * LERP_FACTOR;

    // Lerp all 4 stipple colors toward targets
    const palette = stipplePalette(color);
    const colorUniforms = [mat.uniforms.uColor, mat.uniforms.uColorAlt1, mat.uniforms.uColorAlt2, mat.uniforms.uColorAlt3];
    for (let i = 0; i < 4; i++) {
      (colorUniforms[i].value as THREE.Color).lerp(new THREE.Color(palette[i]), LERP_FACTOR);
    }
  });

  return (
    <group position={position}>
      {/* Invisible sphere for click detection — R3F can't raycast <points> */}
      {onClick && (
        <mesh onClick={(e) => { e.stopPropagation(); onClick(); }}>
          <sphereGeometry args={[1.8, 16, 12]} />
          <meshBasicMaterial visible={false} />
        </mesh>
      )}
      <points>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            array={positions}
            count={positions.length / 3}
            itemSize={3}
          />
          <bufferAttribute
            attach="attributes-aRandomSeed"
            array={seeds}
            count={seeds.length}
            itemSize={1}
          />
          <bufferAttribute
            attach="attributes-aDensity"
            array={densities}
            count={densities.length}
            itemSize={1}
          />
          <bufferAttribute
            attach="attributes-aColorVariant"
            array={colorVariants}
            count={colorVariants.length}
            itemSize={1}
          />
        </bufferGeometry>
        <shaderMaterial
          ref={materialRef}
          vertexShader={vertexShader}
          fragmentShader={fragmentShader}
          uniforms={uniforms}
          transparent
          depthWrite={false}
        />
      </points>
    </group>
  );
}
