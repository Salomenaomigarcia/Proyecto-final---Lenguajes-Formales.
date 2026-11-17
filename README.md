# Formal Languages and Compilers — Final Project

**Course / group:** Lenguajes Formales - C2666-SI2002-4369  
**Team members:** Matías Mora Posada and Salomé Naomi García Tabares  
**Language:** Python 3 (CPython; verified with Python 3.13.5)

## Project overview

This project implements the following algorithms and concepts from *Compilers: Principles, Techniques, and Tools* (2nd edition, 2006), also known as the Dragon Book:

1. **FIRST and FOLLOW sets** for context-free grammars, including epsilon (`e`) productions (Section 4.4.2).
2. **LL(1) predictive parsing:** FIRST/FOLLOW-based table construction, conflict detection, and non-recursive parsing with a stack (Sections 4.4.3–4.4.4).
3. **SLR(1) bottom-up parsing:** LR(0) items, `CLOSURE`, `GOTO`, canonical states, `ACTION`/`GOTO` tables, conflict detection, and shift-reduce parsing (Sections 4.5–4.6).
4. **Syntax-directed definition (SDD):** a custom grammar, synthesized and inherited attributes, annotated parse trees, dependency graphs, topological evaluation, and cycle detection (Sections 5.1–5.2).

All parsing algorithms are implemented using the Python standard library. The project does **not** rely on parser generators or external parsing packages.

## Submission contents

```text
.
├── main.py
├── README.md
└── Informe_Final_Lenguajes_Formales.pdf
```

The PDF report contains the theoretical references, examples, tables, execution results, semantic rules, test cases, and the three original handwritten figures documenting the SDD.

## Environment and requirements

- **Programming language:** Python 3; tested with **CPython 3.13.5**.
- **Tools:** Python interpreter and command-line terminal. Visual Studio Code can be used as an optional editor; its local installed version is not required to run the program and has not been independently verified here.
- **Dependencies:** Python standard library only (`sys`, `platform`). No `pip install`, build step, or virtual environment is necessary.

From a terminal in the directory containing `main.py`, check the interpreter:

```bash
python --version
```

On macOS/Linux, use `python3` instead of `python` if your system requires it. On Windows, the `py` launcher also works.

## Running Items 1 and 2 (FIRST/FOLLOW, LL(1), SLR(1))

Run the default mode:

```bash
python main.py
```

The input format is:

1. A positive integer `n` (the number of nonterminals).
2. Exactly `n` production lines, such as `A -> aA e`.
3. If the grammar is both LL(1) and SLR(1), choose `T` for LL(1), `B` for SLR(1), or `Q` to quit.
4. Enter one test string per line; **a completely empty line** finishes the current batch of test strings.

Input conventions: `S` is the start symbol; uppercase single characters represent nonterminals; terminals are other single characters. The symbol `e` represents epsilon and is not an ordinary terminal; `$` is reserved for the end-of-input marker. To test the **empty string**, type a line containing only `e`. Do not type `$` in the input strings.

### Interactive example

Use this grammar:

```text
3
S -> xAB
A -> aA e
B -> bB c
```

Both LL(1) and SLR(1) apply. Choose `T` and enter the following strings:

```text
T
xaabc
xc
xab

Q
```

The expected answers to the three strings are, in order, `yes`, `yes`, `no`. The blank line before `Q` returns to parser selection.

### Optional command-line flags

| Command | Purpose |
|---|---|
| `python main.py --sets` | Prints FIRST/FOLLOW sets in the required order, then continues with the normal parser flow. |
| `python main.py --table` | Prints the LL(1) table and LR(0)/SLR(1) states and tables. |
| `python main.py --trace` | Shows parser actions step by step during recognition. |
| `python main.py --demo` | Runs built-in demonstrations without interactive input. |
| `python main.py --test` | Runs the included automated checks. |
| `python main.py --info` | Prints the operating system and Python version of the current machine. |

Flags such as `--sets --table --trace` can be combined in the normal grammar-input mode.

## Running Item 3 (the custom SDD)

The SDD mode uses a **built-in custom grammar**, so **do not enter `n` or production lines** in this mode:

```text
S -> A
A -> aA | bB
B -> cB | dC
C -> fC | g
```

The language is `a*bc*df*g`. The inherited attribute `A.level` counts the leading `a` characters; the synthesized attribute `score` gives the length of the accepted string plus that count.

Run:

```bash
python main.py --sdd
```

Type test strings, one per line; finish with an empty line:

```text
bdg
abccdg
aabccdfg
bd

```

For accepted strings, the program prints an **annotated parse tree**, a valid **topological evaluation order**, and the final `S.score`; invalid strings yield `no`. For `aabccdfg`, the final result is `S.score = 10`.

To also print dependency graph vertices and edges:

```bash
python main.py --sdd --graph
```

To demonstrate circular dependency detection (without modifying the original SDD data):

```bash
python main.py --cycle-demo
```

Expected output includes:

```text
Temporary change: S.score = S.score + 1
Circular SDD: dependency graph contains a cycle
```

## Tests and documentation

Execute:

```bash
python main.py --test
```

In the documented verification using CPython 3.13.5, all **20 built-in checks passed** (`20 pruebas, 0 fallaron`). The suite covers epsilon/FIRST/FOLLOW behavior, LL(1)/SLR(1) recognition, left recursion, grammar rejection, terminal symbols, the examples from the assignment, SDD calculations, deep recursion, dependency order, circularity, and undefined attributes. Passing these tests is not a formal proof for all possible grammars.

The PDF report explains the algorithms, presents an example of the LL(1) table and step-by-step recognition, and reproduces the handwritten SDD material. The report also supplies a corrected numeric attribute-value table to resolve a discrepancy in one of the handwritten sheets.

## AI assistance and academic responsibility

**Note:** AI was used to identify, fix, and optimize the problems found in the source code. It was also used as a tool to give this README document better form, formatting, and context.

## Reference

Aho, A. V., Lam, M. S., Sethi, R., & Ullman, J. D. (2006). *Compilers: Principles, Techniques, and Tools* (2nd ed.). Pearson/Addison-Wesley. Relevant sections: 4.4.2–4.4.4, 4.5, 4.6.2–4.6.4, 5.1, and 5.2.
