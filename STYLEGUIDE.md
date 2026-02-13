# Styleguide (Tailwind)

Dieses Dokument definiert die aktuellen UI‑Standards für das Stärkenanalyse‑Tool. Es ist die verbindliche Referenz für alle kommenden Designanpassungen.

## Grundprinzipien

- **Konsistenz vor Individualität**: Bestehende Muster wiederverwenden.
- **Tailwind‑First**: Keine neuen Bootstrap‑Klassen einführen.
- **Semantische Farben**: Status‑Farben nur für Status verwenden.
- **Kompetenz‑Tags sind eindeutig** (siehe unten).

---

## Design Tokens

### Farben

- **Primary**: `indigo-600` (Hover: `indigo-700`)
- **Secondary**: `gray-600` (Hover: `gray-700`)
- **Success**: `green-600` (Hover: `green-700`)
- **Warning**: `yellow-600` (Hover: `yellow-700`)
- **Danger**: `red-600` (Hover: `red-700`)
- **Surface**: `white` / `gray-50`
- **Border**: `gray-200` / `gray-300`
- **Text**: `gray-900` (Headings), `gray-700` (Body), `gray-500` (Muted)

### Typografie

- **Page Title**: `text-3xl font-bold text-gray-900`
- **Section Title**: `text-xl font-semibold text-gray-900`
- **Body**: `text-sm text-gray-700`
- **Muted**: `text-xs text-gray-500`

### Spacing & Radius

- **Card Padding**: `p-6`
- **Form Spacing**: `space-y-4`
- **Radius**: `rounded-lg` (Cards), `rounded-md` (Inputs/Buttons)

### Shadow

- **Cards**: `shadow-md`
- **Modals**: `shadow-xl`

---

## Komponenten

### Buttons

- **Primary**
  - `inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700`
- **Secondary (Neutral)**
  - `inline-flex items-center rounded-md bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-200`
- **Destructive**
  - `inline-flex items-center rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700`
- **Outline**
  - `inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50`

### Inputs

- **Text/Number**
  - `rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500`

- **Select**
  - gleiche Klassen wie Input

- **Textarea**
  - gleiche Klassen wie Input

### Cards

- **Standard Card**
  - Container: `rounded-lg border border-gray-200 bg-white shadow-sm`
  - Header: `border-b border-gray-200 px-6 py-4`
  - Body: `px-6 py-5`

### Tables

- **Table**
  - Wrapper: `overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm`
  - Table: `min-w-full divide-y divide-gray-200 text-sm`
  - Head: `bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500`
  - Row hover: `hover:bg-gray-50`

### Alerts

- **Success**: `border-green-200 bg-green-50 text-green-700`
- **Warning**: `border-yellow-200 bg-yellow-50 text-yellow-700`
- **Error**: `border-red-200 bg-red-50 text-red-700`
- **Info**: `border-blue-200 bg-blue-50 text-blue-700`

---

## Kompetenz‑Tags (verbindlich)

- **Soziale Kompetenzen** → `bg-blue-100 text-blue-700`
- **Verbale Kompetenzen** → `bg-purple-100 text-purple-700`
- **Fallback/Andere** → `bg-gray-100 text-gray-700`

Diese Farben sind **systemweit** zu verwenden (Referenz‑Karten, Tabellen, Tags etc.).

---

## Anwendung (Checkliste)

Bei jeder neuen UI‑Änderung:

1. **Buttons/Input/Tag** gegen diesen Guide prüfen
2. **Keine neuen Farben** ohne Update dieses Dokuments
3. **Kompetenz‑Tags** immer nach obigem Schema

---

## Gültigkeit

Dieser Styleguide ist die **verbindliche Basis** für die laufende Tailwind‑Konsolidierung.
