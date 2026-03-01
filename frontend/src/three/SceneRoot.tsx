import { Canvas } from '@react-three/fiber';
import { ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

export function SceneRoot({ children }: Props) {
  return (
    <Canvas
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 1,
        pointerEvents: 'auto',
      }}
      gl={{ alpha: true, antialias: true }}
      camera={{ position: [0, 0, 10], fov: 45 }}
    >
      {children}
    </Canvas>
  );
}
