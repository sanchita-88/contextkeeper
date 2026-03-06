"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Sphere, Box, Icosahedron } from "@react-three/drei";
import * as THREE from "three";

function MemoryCore() {
    const coreRef = useRef<THREE.Mesh>(null);
    const outerRingsRef = useRef<THREE.Group>(null);

    useFrame((state, delta) => {
        if (coreRef.current) {
            coreRef.current.rotation.y += delta * 0.2;
            coreRef.current.rotation.x += delta * 0.1;
        }
        if (outerRingsRef.current) {
            outerRingsRef.current.rotation.y -= delta * 0.1;
            outerRingsRef.current.rotation.z += delta * 0.05;
        }
    });

    return (
        <group position={[0, 0, 0]}>
            {/* Central Core */}
            <Icosahedron ref={coreRef} args={[2.5, 1]} position={[0, 0, 0]}>
                <meshStandardMaterial
                    color="#a855f7" // Purple
                    emissive="#a855f7"
                    emissiveIntensity={0.5}
                    wireframe
                    transparent
                    opacity={0.8}
                />
            </Icosahedron>

            {/* Outer Shell/Rings */}
            <group ref={outerRingsRef}>
                <Icosahedron args={[3.5, 2]}>
                    <meshStandardMaterial
                        color="#3b82f6" // Blue
                        emissive="#3b82f6"
                        emissiveIntensity={0.2}
                        wireframe
                        transparent
                        opacity={0.3}
                    />
                </Icosahedron>
            </group>

            {/* Core Inner Glow */}
            <pointLight
                position={[0, 0, 0]}
                intensity={2}
                color="#a855f7"
                distance={10}
            />
        </group>
    );
}

function OrbitingParticles({ count = 3000 }) {
    const points = useRef<THREE.Points>(null);

    const particlesPosition = useMemo(() => {
        const positions = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            // Distribute particles in a spherical shell around the core
            const r = 5 + Math.random() * 25;
            const theta = 2 * Math.PI * Math.random();
            const phi = Math.acos(2 * Math.random() - 1);

            positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = r * Math.cos(phi);
        }
        return positions;
    }, [count]);

    useFrame((state, delta) => {
        if (points.current) {
            points.current.rotation.y += delta * 0.03;
            points.current.rotation.x += delta * 0.01;
        }
    });

    return (
        <points ref={points}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    count={particlesPosition.length / 3}
                    array={particlesPosition}
                    itemSize={3}
                />
            </bufferGeometry>
            <pointsMaterial
                size={0.05}
                color="#c084fc"
                transparent
                opacity={0.6}
                sizeAttenuation={true}
                blending={THREE.AdditiveBlending}
            />
        </points>
    );
}

export default function ThreejsBackground() {
    return (
        <div className="fixed inset-0 z-0 pointer-events-none opacity-60">
            <Canvas camera={{ position: [0, 0, 15], fov: 60 }}>
                <fog attach="fog" args={["#000000", 8, 30]} />
                <ambientLight intensity={0.2} />

                {/* Colorful dynamic lighting */}
                <directionalLight position={[10, 10, 5]} intensity={1} color="#3b82f6" />
                <directionalLight position={[-10, -10, -5]} intensity={1} color="#a855f7" />

                <MemoryCore />
                <OrbitingParticles count={3000} />
            </Canvas>

            {/* Background gradients overriding absolute blacks slightly for depth */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,0,0,0)_0%,#000000_100%)] z-10" />
            <div className="absolute inset-x-0 bottom-0 h-[40%] bg-gradient-to-t from-black to-transparent z-10" />
            <div className="absolute inset-x-0 top-0 h-[30%] bg-gradient-to-b from-black to-transparent z-10" />
        </div>
    );
}
