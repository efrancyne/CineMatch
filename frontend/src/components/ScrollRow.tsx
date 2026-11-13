"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import styles from "./ScrollRow.module.css";

/**
 * Lista horizontal rolável com setas e arrastar com o mouse.
 * (A barra de rolagem fica escondida no design; sem isto, só trackpad/toque rolava.)
 */
export function ScrollRow({ children, className }: { children: React.ReactNode; className: string }) {
  const ref = useRef<HTMLUListElement>(null);
  const [podeVoltar, setPodeVoltar] = useState(false);
  const [podeAvancar, setPodeAvancar] = useState(false);
  const arrasto = useRef({ ativo: false, moveu: false, x: 0, scroll: 0 });

  const atualizar = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    setPodeVoltar(el.scrollLeft > 4);
    setPodeAvancar(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    atualizar();
    const obs = new ResizeObserver(atualizar);
    obs.observe(el);
    return () => obs.disconnect();
  }, [atualizar, children]);

  function rolar(direcao: 1 | -1) {
    const el = ref.current;
    if (el) el.scrollBy({ left: direcao * el.clientWidth * 0.8, behavior: "smooth" });
  }

  function aoPressionar(e: React.PointerEvent<HTMLUListElement>) {
    if (e.pointerType !== "mouse" || e.button !== 0) return; // toque já rola nativamente
    arrasto.current = { ativo: true, moveu: false, x: e.clientX, scroll: ref.current?.scrollLeft ?? 0 };
  }

  function aoMover(e: React.PointerEvent<HTMLUListElement>) {
    const a = arrasto.current;
    const el = ref.current;
    if (!a.ativo || !el) return;
    const dx = e.clientX - a.x;
    if (!a.moveu && Math.abs(dx) > 5) {
      a.moveu = true;
      el.dataset.arrastando = "true";
    }
    if (a.moveu) el.scrollLeft = a.scroll - dx;
  }

  function aoSoltar() {
    const el = ref.current;
    arrasto.current.ativo = false;
    if (el) delete el.dataset.arrastando;
  }

  return (
    <div className={styles.wrap}>
      {podeVoltar && (
        <button type="button" className={`${styles.seta} ${styles.voltar}`} onClick={() => rolar(-1)} aria-label="Ver anteriores">
          ‹
        </button>
      )}
      <ul
        ref={ref}
        className={`${className} ${styles.lista}`}
        onScroll={atualizar}
        onPointerDown={aoPressionar}
        onPointerMove={aoMover}
        onPointerUp={aoSoltar}
        onPointerLeave={aoSoltar}
        // depois de arrastar, não deixa o "click" abrir o filme
        onClickCapture={(e) => {
          if (arrasto.current.moveu) {
            e.preventDefault();
            e.stopPropagation();
            arrasto.current.moveu = false;
          }
        }}
        onDragStart={(e) => e.preventDefault()}
      >
        {children}
      </ul>
      {podeAvancar && (
        <button type="button" className={`${styles.seta} ${styles.avancar}`} onClick={() => rolar(1)} aria-label="Ver mais">
          ›
        </button>
      )}
    </div>
  );
}
