import { useEffect, useRef } from "react";

// Scroll-driven parallax: the element drifts vertically relative to the page as you scroll, so layers separate
// in depth (the floating object lags the copy). Writes a CSS var (no re-renders). Honors prefers-reduced-motion
// — when set, the element stays put and the static layered shadows carry the depth instead.
export function useParallax<T extends HTMLElement>(factor = 0.08) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const update = () => {
      const r = el.getBoundingClientRect();
      const fromCenter = r.top + r.height / 2 - window.innerHeight / 2;
      el.style.setProperty("--py", `${(-fromCenter * factor).toFixed(1)}px`);
      raf = 0;
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [factor]);
  return ref;
}
