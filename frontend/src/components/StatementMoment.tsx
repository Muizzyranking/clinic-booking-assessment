import { useEffect, useRef } from "react";

interface Props {
  words: string[];
  /** Indexes of the words that turn to the accent colour. */
  strong?: number[];
}

/**
 * One large statement that turns from half ink to full ink, word by word, as
 * it crosses the middle of the screen. Runs back on the way up. With reduced
 * motion every word is simply at full ink.
 */
export function StatementMoment({ words, strong = [] }: Props) {
  const container = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    const element = container.current;
    if (!element) return;
    const spans = Array.from(element.querySelectorAll<HTMLElement>("[data-word]"));
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      spans.forEach((span) => span.classList.add("is-lit"));
      return;
    }

    let frame = 0;
    const update = () => {
      frame = 0;
      const rect = element.getBoundingClientRect();
      const viewport = window.innerHeight;
      // 0 when the block enters the bottom third, 1 when it reaches the top third.
      const progress = (viewport * 0.85 - rect.top) / (viewport * 0.55 + rect.height * 0.4);
      const lit = Math.round(Math.min(1, Math.max(0, progress)) * spans.length);
      spans.forEach((span, index) => span.classList.toggle("is-lit", index < lit));
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };

    update();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <p className="statement" ref={container}>
      {words.map((word, index) => (
        <span
          key={`${word}-${index}`}
          data-word
          className={strong.includes(index) ? "statement__word is-strong" : "statement__word"}
        >
          {word}{" "}
        </span>
      ))}
    </p>
  );
}
