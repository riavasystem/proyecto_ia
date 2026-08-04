"use client";

import { useEffect, useRef } from "react";

// Guarda para efectos de fetch: evita que un setState dispare después de que
// el componente se desmontó, y satisface react-hooks/set-state-in-effect al
// condicionar el setState en vez de llamarlo sin guardas.
export function useIsMounted() {
  const ref = useRef(true);
  useEffect(() => {
    return () => {
      ref.current = false;
    };
  }, []);
  return ref;
}
