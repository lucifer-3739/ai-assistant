"use client";

import React, { useEffect, useRef } from "react";

interface WaveformProps {
  active: boolean;
  state: string;
}

export const HolographicWaveform: React.FC<WaveformProps> = ({ active, state }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let phase = 0;

    // Particle field
    const particleCount = 45;
    const particles: Array<{
      x: number;
      y: number;
      radius: number;
      speed: number;
      alpha: number;
      hue: number;
    }> = [];

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * 800,
        y: Math.random() * 180,
        radius: Math.random() * 2.2 + 0.6,
        speed: Math.random() * 0.9 + 0.2,
        alpha: Math.random() * 0.7 + 0.2,
        hue: Math.random() * 40 - 20 // hue jitter
      });
    }

    // Spectrum bars simulation
    const barCount = 32;
    const barHeights = new Array(barCount).fill(0);

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      const isListening = active || state === "LISTENING";
      const isSpeaking = state === "SPEAKING";
      const isPlanning = state === "PLANNING" || state === "UNDERSTANDING" || state === "EXECUTING";
      const isWaitingPerm = state === "WAITING_FOR_PERMISSION";

      // Dynamic activity multiplier & speed
      const ampMultiplier = isListening ? 2.2 : isSpeaking ? 2.0 : isPlanning ? 1.6 : isWaitingPerm ? 1.4 : 0.65;
      const speedMultiplier = isListening ? 0.045 : isSpeaking ? 0.038 : isPlanning ? 0.03 : isWaitingPerm ? 0.025 : 0.015;

      phase += speedMultiplier;

      // Color themes according to state
      const primaryGlow = isListening 
        ? "#00f0ff" 
        : isSpeaking 
        ? "#c084fc" 
        : isPlanning 
        ? "#38bdf8" 
        : isWaitingPerm 
        ? "#f59e0b" 
        : "#0284c7";

      const primaryRgba = isListening 
        ? "0, 240, 255" 
        : isSpeaking 
        ? "192, 132, 252" 
        : isPlanning 
        ? "56, 189, 248" 
        : isWaitingPerm 
        ? "245, 158, 11" 
        : "2, 132, 199";

      // 1. Draw Spectrum Equalizer Bars at bottom
      const barWidth = 3;
      const barSpacing = (width - 160) / barCount;
      const startX = 80;

      for (let i = 0; i < barCount; i++) {
        const targetHeight = (isListening || isSpeaking || isPlanning)
          ? Math.sin(phase * 2 + i * 0.4) * 14 + Math.cos(phase * 3 + i * 0.7) * 10 + 18
          : Math.sin(phase + i * 0.3) * 4 + 5;

        barHeights[i] += (targetHeight - barHeights[i]) * 0.2;

        const bx = startX + i * barSpacing;
        const by = height - 12;

        ctx.save();
        ctx.fillStyle = `rgba(${primaryRgba}, 0.35)`;
        ctx.shadowColor = primaryGlow;
        ctx.shadowBlur = 6;
        ctx.fillRect(bx, by - barHeights[i], barWidth, barHeights[i]);
        ctx.restore();
      }

      // 2. Draw Floating Holographic Particles
      particles.forEach((p) => {
        p.y -= p.speed * (isListening || isSpeaking ? 1.6 : 0.7);
        if (p.y < 0) {
          p.y = height;
          p.x = Math.random() * width;
        }

        ctx.save();
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${primaryRgba}, ${p.alpha})`;
        ctx.shadowColor = primaryGlow;
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.restore();
      });

      // 3. Layered Sine Wave Configurations (matching Iron Man HUD)
      const waves = [
        {
          frequency: 0.011,
          amplitude: 40 * ampMultiplier,
          speed: 1.0,
          color: `rgba(${primaryRgba}, 0.3)`,
          lineWidth: 2,
          blur: 10
        },
        {
          frequency: 0.017,
          amplitude: 30 * ampMultiplier,
          speed: -1.2,
          color: `rgba(${primaryRgba}, 0.55)`,
          lineWidth: 2.5,
          blur: 16
        },
        {
          frequency: 0.009,
          amplitude: 46 * ampMultiplier,
          speed: 0.75,
          color: `rgba(${primaryRgba}, 0.8)`,
          lineWidth: 3.5,
          blur: 24
        },
        {
          frequency: 0.014,
          amplitude: 34 * ampMultiplier,
          speed: -0.85,
          color: "rgba(255, 255, 255, 0.95)",
          lineWidth: 1.8,
          blur: 20
        }
      ];

      waves.forEach((wave) => {
        ctx.save();
        ctx.beginPath();
        ctx.shadowColor = primaryGlow;
        ctx.shadowBlur = wave.blur;
        ctx.strokeStyle = wave.color;
        ctx.lineWidth = wave.lineWidth;
        ctx.lineCap = "round";

        for (let x = 0; x < width; x++) {
          const edgeDist = Math.min(x, width - x) / (width / 2);
          const envelope = Math.sin((Math.PI / 2) * Math.min(1, edgeDist * 1.5));

          const y =
            centerY +
            Math.sin(x * wave.frequency + phase * wave.speed) *
              wave.amplitude *
              envelope +
            Math.cos(x * wave.frequency * 0.55 + phase * 0.6) *
              (wave.amplitude * 0.35) *
              envelope;

          if (x === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
        ctx.restore();
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [active, state]);

  return (
    <div className="relative w-full flex flex-col items-center justify-center overflow-hidden select-none">
      <canvas
        ref={canvasRef}
        width={800}
        height={180}
        className="w-full max-w-2xl h-36 drop-shadow-[0_0_20px_rgba(0,240,255,0.2)]"
      />
    </div>
  );
};
