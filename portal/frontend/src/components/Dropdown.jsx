import { useEffect, useId, useRef, useState } from 'react'

// Themed, searchable replacement for <select>: the browser's native option
// list can't be styled to match the portal, and long lists need filtering.
// Opening shows a search box: type to narrow the list, or scroll it.
// Keyboard: Enter/Space/↓ (or just start typing) opens, ↑/↓ move,
// Home/End jump, Enter selects, Esc/Tab closes.
export default function Dropdown({ label, placeholder, value, options, onChange }) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const rootRef = useRef(null)
  const buttonRef = useRef(null)
  const inputRef = useRef(null)
  const listRef = useRef(null)

  const items = [{ value: '', label: placeholder }, ...options.map((o) => ({ value: o, label: o }))]
  const current = items.find((i) => i.value === value) ?? items[0]
  const q = query.trim().toLowerCase()
  // while searching, hide the "Select …" entry and keep only matches
  const visible = q ? items.filter((i) => i.value && i.label.toLowerCase().includes(q)) : items

  // close when clicking anywhere else
  useEffect(() => {
    if (!open) return
    const onDown = (e) => { if (!rootRef.current?.contains(e.target)) close() }
    document.addEventListener('pointerdown', onDown)
    return () => document.removeEventListener('pointerdown', onDown)
  }, [open])

  useEffect(() => { if (open) inputRef.current?.focus() }, [open])

  // keep the highlighted option in view while moving with the keyboard
  useEffect(() => {
    if (!open) return
    listRef.current?.querySelector('[data-active="true"]')?.scrollIntoView({ block: 'nearest' })
  }, [active, open])

  function openList(initialQuery = '') {
    setQuery(initialQuery)
    setActive(initialQuery ? 0 : Math.max(0, items.indexOf(current)))
    setOpen(true)
  }

  function close(refocus = false) {
    setOpen(false)
    setQuery('')
    if (refocus) buttonRef.current?.focus()
  }

  function choose(item) {
    onChange(item.value)
    close(true)
  }

  function onButtonKeyDown(e) {
    if (['Enter', ' ', 'ArrowDown', 'ArrowUp'].includes(e.key)) {
      e.preventDefault()
      openList()
    } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault()
      openList(e.key) // start typing straight away
    }
  }

  function onInputKeyDown(e) {
    const last = visible.length - 1
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(last, a + 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(0, a - 1)) }
    else if (e.key === 'Home') { e.preventDefault(); setActive(0) }
    else if (e.key === 'End') { e.preventDefault(); setActive(Math.max(0, last)) }
    else if (e.key === 'Enter') { e.preventDefault(); if (visible[active]) choose(visible[active]) }
    else if (e.key === 'Escape') { e.preventDefault(); close(true) }
    else if (e.key === 'Tab') close()
  }

  return (
    <div className="filter-field" ref={rootRef}>
      <label id={`${id}-label`} htmlFor={`${id}-button`}>{label}</label>
      <div className="dropdown">
        <button
          id={`${id}-button`}
          ref={buttonRef}
          type="button"
          className={`dropdown-button ${open ? 'is-open' : ''} ${value ? '' : 'is-placeholder'}`}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-labelledby={`${id}-label ${id}-button`}
          onClick={() => (open ? close() : openList())}
          onKeyDown={onButtonKeyDown}
        >
          <span className="dropdown-value">{current.label}</span>
          <svg className="dropdown-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>

        {open && (
          <div className="dropdown-panel">
            <div className="dropdown-search">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path d="M20 20l-3.5-3.5" />
              </svg>
              <input
                ref={inputRef}
                type="text"
                role="combobox"
                aria-label={`Search ${label.toLowerCase()}`}
                aria-expanded="true"
                aria-controls={`${id}-list`}
                aria-autocomplete="list"
                aria-activedescendant={visible[active] ? `${id}-opt-${active}` : undefined}
                placeholder={`Type to search ${label.toLowerCase()}…`}
                value={query}
                onChange={(e) => { setQuery(e.target.value); setActive(0) }}
                onKeyDown={onInputKeyDown}
              />
            </div>

            <ul className="dropdown-list" id={`${id}-list`} role="listbox" aria-labelledby={`${id}-label`} ref={listRef}>
              {visible.length === 0 && <li className="dropdown-empty">No matches for “{query}”</li>}
              {visible.map((item, i) => {
                const selected = item.value === value && Boolean(item.value)
                return (
                  <li
                    key={item.value || '__placeholder'}
                    id={`${id}-opt-${i}`}
                    role="option"
                    aria-selected={selected}
                    data-active={i === active}
                    className={`dropdown-option ${i === active ? 'is-active' : ''} ${selected ? 'is-selected' : ''} ${item.value ? '' : 'is-placeholder'}`}
                    onPointerEnter={() => setActive(i)}
                    onPointerDown={(e) => e.preventDefault()} // keep focus in the search box
                    onClick={() => choose(item)}
                  >
                    <span>{item.label}</span>
                    {selected && (
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M5 12l5 5L20 7" />
                      </svg>
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
