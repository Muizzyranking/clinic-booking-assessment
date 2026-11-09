import { useEffect, useRef, type ReactNode } from "react";

interface Props {
  /** Id of the element that titles the dialog. */
  labelledBy: string;
  onClose: () => void;
  children: ReactNode;
  size?: "small" | "medium";
}

/**
 * A native <dialog> opened with showModal(): focus is trapped, Escape closes it
 * and everything behind it becomes inert. Clicking the backdrop closes it too.
 */
export function Modal({ labelledBy, onClose, children, size = "medium" }: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (dialog && !dialog.open) dialog.showModal();
  }, []);

  return (
    <dialog
      ref={ref}
      className={`modal modal--${size}`}
      aria-labelledby={labelledBy}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="modal__body">{children}</div>
    </dialog>
  );
}
