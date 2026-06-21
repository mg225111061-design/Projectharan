import { useEffect, useRef } from "react";

// Pointer-driven 3D tilt for the dimensional objects. The element is rotated toward the pointer with a spring
// lerp (no per-frame React renders — we write CSS custom props directly). Honors prefers-reduced-motion: when
// set, we leave the element flat and let the static layered shadows carry the depth instead.
export function useTilt<T extends HTMLElement>(max = 7, persp = 1100) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.setProperty("--persp", `${persp}px`);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return; // keep depth via shadow/layering, drop the motion

    let raf = 0;
    let tx = 0, ty = 0, cx = 0, cy = 0, lift = 0, tl = 0;
    const tick = () => {
      cx += (tx - cx) * 0.12;
      cy += (ty - cy) * 0.12;
      lift += (tl - lift) * 0.12;
      el.style.setProperty("--rx", `${cx.toFixed(2)}deg`);
      el.style.setProperty("--ry", `${cy.toFixed(2)}deg`);
      el.style.setProperty("--lift", `${lift.toFixed(1)}px`);
      raf =
        Math.abs(tx - cx) > 0.01 || Math.abs(ty - cy) > 0.01 || Math.abs(tl - lift) > 0.05
          ? requestAnimationFrame(tick)
          : 0;
    };
    const kick = () => {
      if (!raf) raf = requestAnimationFrame(tick);
    };
    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5;
      const py = (e.clientY - r.top) / r.height - 0.5;
      tx = -py * max;
      ty = px * max;
      tl = 6;
      kick();
    };
    const onLeave = () => {
      tx = 0; ty = 0; tl = 0;
      kick();
    };
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerleave", onLeave);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [max, persp]);
  return ref;
}
