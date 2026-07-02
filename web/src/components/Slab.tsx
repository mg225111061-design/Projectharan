import type { ReactNode } from "react";
import { useTilt } from "../useTilt";

// A physical object floating in the white volume: layered soft shadows + pointer-driven 3D tilt. The few
// elements that survive the minimalism are rendered as these slabs — minimal in count, maximal in dimension.
export function Slab({
  children,
  className = "",
  max = 7,
  style,
}: {
  children: ReactNode;
  className?: string;
  max?: number;
  style?: React.CSSProperties;
}) {
  const ref = useTilt<HTMLDivElement>(max);
  return (
    <div ref={ref} className={`slab float-in ${className}`} style={style}>
      {children}
    </div>
  );
}
