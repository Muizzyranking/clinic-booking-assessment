import {
  createContext,
  useCallback,
  useContext,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { Modal } from "./Modal";

export interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** "danger" paints the confirm button red, for destructive actions. */
  tone?: "default" | "danger";
}

type Confirm = (options: ConfirmOptions) => Promise<boolean>;

const ConfirmContext = createContext<Confirm | null>(null);

/** Resolves true on confirm, false on cancel, Escape or a click outside. */
export function useConfirm(): Confirm {
  const confirm = useContext(ConfirmContext);
  if (!confirm) throw new Error("useConfirm must be used inside <DialogProvider>");
  return confirm;
}

export function DialogProvider({ children }: { children: ReactNode }) {
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const resolver = useRef<((answer: boolean) => void) | null>(null);
  const titleId = useId();

  const confirm = useCallback<Confirm>((next) => {
    resolver.current?.(false);
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve;
      setOptions(next);
    });
  }, []);

  const answer = useCallback((value: boolean) => {
    resolver.current?.(value);
    resolver.current = null;
    setOptions(null);
  }, []);

  const value = useMemo(() => confirm, [confirm]);

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      {options && (
        <Modal labelledBy={titleId} size="small" onClose={() => answer(false)}>
          <h2 id={titleId} className="modal__title">
            {options.title}
          </h2>
          <p className="modal__text">{options.message}</p>
          <div className="modal__actions">
            <button type="button" className="btn btn--secondary" onClick={() => answer(false)}>
              {options.cancelLabel ?? "Keep it"}
            </button>
            <button
              type="button"
              autoFocus
              className={options.tone === "danger" ? "btn btn--danger-solid" : "btn btn--primary"}
              onClick={() => answer(true)}
            >
              {options.confirmLabel ?? "Confirm"}
            </button>
          </div>
        </Modal>
      )}
    </ConfirmContext.Provider>
  );
}
