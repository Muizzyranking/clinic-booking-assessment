import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

export interface SelectOption {
  value: string;
  label: string;
}

interface Props {
  label: string;
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
}

/**
 * A styled replacement for <select>, built as the ARIA "select-only combobox":
 * the button keeps focus, arrow keys move through the list, Enter picks,
 * Escape closes, and typing jumps to a matching option.
 */
export function Select({ label, value, options, onChange }: Props) {
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const typing = useRef({ text: "", timer: 0 });
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const selectedIndex = Math.max(
    0,
    options.findIndex((option) => option.value === value),
  );
  const selected = options[selectedIndex];

  useEffect(() => {
    if (!open) return;
    const away = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);

  useEffect(() => {
    if (open) list.current?.children[active]?.scrollIntoView({ block: "nearest" });
  }, [open, active]);

  function show() {
    setActive(selectedIndex);
    setOpen(true);
  }

  function choose(index: number) {
    const option = options[index];
    if (option) onChange(option.value);
    setOpen(false);
  }

  function jumpTo(letter: string) {
    window.clearTimeout(typing.current.timer);
    typing.current.text += letter.toLowerCase();
    typing.current.timer = window.setTimeout(() => (typing.current.text = ""), 600);
    const text = typing.current.text;
    const from = text.length === 1 ? active + 1 : active;
    const ordered = [...options.keys()].map((_, step) => (from + step) % options.length);
    const match = ordered.find((index) => options[index]?.label.toLowerCase().startsWith(text));
    if (match !== undefined) {
      if (!open) setOpen(true);
      setActive(match);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const last = options.length - 1;
    // A space in the middle of typing ("Dr E…") is part of the search, not a pick.
    if (event.key === " " && typing.current.text) {
      event.preventDefault();
      jumpTo(" ");
      return;
    }
    if (!open) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
        event.preventDefault();
        show();
      } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey) {
        jumpTo(event.key);
      }
      return;
    }
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        setActive((current) => Math.min(current + 1, last));
        break;
      case "ArrowUp":
        event.preventDefault();
        setActive((current) => Math.max(current - 1, 0));
        break;
      case "Home":
        event.preventDefault();
        setActive(0);
        break;
      case "End":
        event.preventDefault();
        setActive(last);
        break;
      case "Enter":
      case " ":
        event.preventDefault();
        choose(active);
        break;
      case "Escape":
        event.preventDefault();
        event.stopPropagation();
        setOpen(false);
        break;
      case "Tab":
        setOpen(false);
        break;
      default:
        if (event.key.length === 1 && !event.ctrlKey && !event.metaKey) jumpTo(event.key);
    }
  }

  return (
    <div className="field select" ref={root}>
      <span className="field__label" id={`${id}-label`}>
        {label}
      </span>
      <button
        type="button"
        id={`${id}-button`}
        className="select__button"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-labelledby={`${id}-label ${id}-button`}
        aria-activedescendant={open ? `${id}-option-${active}` : undefined}
        onClick={() => (open ? setOpen(false) : show())}
        onKeyDown={onKeyDown}
      >
        <span>{selected?.label}</span>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M6 9.5l6 6 6-6" />
        </svg>
      </button>
      {open && (
        <ul
          className="select__list"
          id={`${id}-list`}
          role="listbox"
          aria-labelledby={`${id}-label`}
          ref={list}
          onMouseDown={(event) => event.preventDefault()}
        >
          {options.map((option, index) => (
            <li
              key={option.value}
              id={`${id}-option-${index}`}
              role="option"
              aria-selected={option.value === value}
              className={
                "select__option" +
                (index === active ? " is-active" : "") +
                (option.value === value ? " is-selected" : "")
              }
              onMouseMove={() => setActive(index)}
              onClick={() => choose(index)}
            >
              {option.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
