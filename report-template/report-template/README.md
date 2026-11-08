# Group Assignment Report (Midterm) — FDA, NEU

## Usage
1. **Overleaf:** zip the `report-template` folder -> *New Project -> Upload Project* -> Menu -> Compiler: **XeLaTeX**.
2. **Local:** `latexmk -xelatex main.tex` (TeX Live with XeLaTeX).
3. Fill in the group information at the top of `main.tex` (title, members, repo, demo).
4. Write content in `chapters/*.tex`; put images in `figures/`; add sources to `references.bib`.
5. Delete all "Guidance — delete before submitting" boxes (`\guide{...}`) and submit `main.pdf`.

## Structure
- `fdareport.cls` — document class (colours, fonts, logos, cover page). **Do not edit.**
- `main.tex` — cover, declaration, contributions, table of contents.
- `chapters/` — 4 sections + appendix.
- `logos/` — NEU and FDA logos.

## Formatting rules
- A4, 3 cm left margin, 2–2.5 cm elsewhere; 13pt text, 1.3 line spacing.
- Every figure/table needs a caption and must be referenced in the text (`\ref{...}`).
- Quote only key code; keep full code on GitHub.
