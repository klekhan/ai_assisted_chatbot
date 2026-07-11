import { useEffect, useRef, useState } from "react";

/**
 * A soft glowing gradient blob behind the chat UI that drifts in response
 * to real motion input:
 *  - Desktop: mouse position relative to the viewport center
 *  - Mobile: the device's actual gyroscope/tilt (DeviceOrientationEvent)
 *
 * Falls back gracefully to just its own idle "breathing" animation
 * (orb_float, defined in tailwind.config.js) if neither input is available
 * or motion permission is denied — so it never looks broken, just calmer.
 */
export default function AmbientOrb() {
  const orbRef = useRef(null);
  const target = useRef({ x: 0, y: 0 });
  const current = useRef({ x: 0, y: 0 });
  const [needsPermissionPrompt, setNeedsPermissionPrompt] = useState(false);

  useEffect(() => {
    const handleMouseMove = (e) => {
      const nx = (e.clientX / window.innerWidth - 0.5) * 2;
      const ny = (e.clientY / window.innerHeight - 0.5) * 2;
      target.current = { x: nx * 26, y: ny * 26 };
    };
    window.addEventListener("mousemove", handleMouseMove);

    let raf;
    const animate = () => {
      current.current.x += (target.current.x - current.current.x) * 0.05;
      current.current.y += (target.current.y - current.current.y) * 0.05;
      if (orbRef.current) {
        orbRef.current.style.setProperty("--orb-x", `${current.current.x}px`);
        orbRef.current.style.setProperty("--orb-y", `${current.current.y}px`);
      }
      raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  useEffect(() => {
    const hasOrientation = typeof window !== "undefined" && "DeviceOrientationEvent" in window;
    if (!hasOrientation) return;

    const iosNeedsPermission = typeof DeviceOrientationEvent.requestPermission === "function";

    const handleOrientation = (e) => {
      const gamma = e.gamma ?? 0; // left/right tilt, roughly -90..90
      const beta = e.beta ?? 0;   // front/back tilt, roughly -180..180
      target.current = {
        x: Math.max(-26, Math.min(26, gamma)),
        y: Math.max(-26, Math.min(26, beta - 45)),
      };
    };

    if (iosNeedsPermission) {
      // iOS requires an explicit user gesture before we're allowed to read
      // motion data — show a small opt-in button instead of auto-requesting.
      setNeedsPermissionPrompt(true);
      return;
    }

    window.addEventListener("deviceorientation", handleOrientation);
    return () => window.removeEventListener("deviceorientation", handleOrientation);
  }, []);

  const enableMotion = async () => {
    try {
      const result = await DeviceOrientationEvent.requestPermission();
      if (result === "granted") {
        setNeedsPermissionPrompt(false);
        window.addEventListener("deviceorientation", (e) => {
          const gamma = e.gamma ?? 0;
          const beta = e.beta ?? 0;
          target.current = {
            x: Math.max(-26, Math.min(26, gamma)),
            y: Math.max(-26, Math.min(26, beta - 45)),
          };
        });
      }
    } catch {
      // Denied or unsupported — orb just keeps its idle animation.
      setNeedsPermissionPrompt(false);
    }
  };

  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden -z-10">
      <div
        ref={orbRef}
        style={{ transform: "translate(var(--orb-x, 0px), var(--orb-y, 0px))" }}
        className="absolute top-[12%] left-1/2 -translate-x-1/2 w-[620px] h-[620px] rounded-full
          bg-gradient-to-br from-accent via-orange-500 to-fuchsia-600 blur-[120px] animate-orb_float"
      />
      <div
        className="absolute bottom-[8%] right-[10%] w-[360px] h-[360px] rounded-full
          bg-gradient-to-br from-navy-soft to-fuchsia-700 blur-[100px] opacity-20 animate-orb_float"
        style={{ animationDelay: "1.5s" }}
      />

      {needsPermissionPrompt && (
        <button
          onClick={enableMotion}
          className="pointer-events-auto fixed bottom-24 right-4 text-[11px] text-white/60 bg-white/5
            border border-white/10 backdrop-blur px-3 py-1.5 rounded-full hover:text-white/90 transition-colors"
        >
          Enable motion
        </button>
      )}
    </div>
  );
}
