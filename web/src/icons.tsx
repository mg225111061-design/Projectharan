// Tiny inline icons — line weight matches the design system (thin, calm, no fills).
import type { ReactNode } from "react";
import type { ModeId } from "./types";

const S = (p: { children: ReactNode; size?: number }) => (
  <svg
    width={p.size ?? 18}
    height={p.size ?? 18}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {p.children}
  </svg>
);

export const ModeIcon = ({ mode, size }: { mode: ModeId; size?: number }) => {
  if (mode === "fast")
    // a bolt — felt speed, first win
    return (
      <S size={size}>
        <path d="M13 2 4 14h7l-1 8 9-12h-7z" />
      </S>
    );
  if (mode === "normal")
    // balanced scale
    return (
      <S size={size}>
        <path d="M12 3v18M5 7h14M5 7l-2.5 6a3 3 0 0 0 5 0L5 7zm14 0-2.5 6a3 3 0 0 0 5 0L19 7zM8 21h8" />
      </S>
    );
  // extend — a shield (proof, the moat)
  return (
    <S size={size}>
      <path d="M12 3 5 6v6c0 4 3 6.5 7 9 4-2.5 7-5 7-9V6l-7-3z" />
      <path d="m9 12 2 2 4-4" />
    </S>
  );
};

export const Check = () => (
  <S size={15}>
    <path d="M20 6 9 17l-5-5" />
  </S>
);
export const Info = () => (
  <S size={15}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 16v-4M12 8h.01" />
  </S>
);
export const Lock = () => (
  <S size={15}>
    <rect x="4" y="11" width="16" height="9" rx="2" />
    <path d="M8 11V7a4 4 0 0 1 8 0v4" />
  </S>
);
export const Arrow = () => (
  <S size={15}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </S>
);
