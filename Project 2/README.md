# Project 2: Logic — Futoshiki Puzzles (CSC14003)

## Project Overview
This project solves **Futoshiki** logic puzzles using multiple AI techniques required by the course, such as:
- Forward Chaining (FC)
- Backward Chaining (BC)
- A* Search
- Backtracking (BT)

The repository is organized to separate:
- `Source/`: implementation code (entrypoint, solvers, logic, utilities)
- `Inputs/`: puzzle instances (`input-01.txt` … `input-10.txt`)
- `Outputs/`: corresponding results (`output-01.txt` … `output-10.txt`)

## Group Members
- Student_ID1 — Full Name — Email
- Student_ID2 — Full Name — Email
- Student_ID3 — Full Name — Email

## Directory Structure
```
Student_ID1_Student_ID2_Student_ID3/
├── Source/
│   ├── main.py
│   ├── solvers/
│   ├── utils/
│   └── logic/
├── Inputs/
├── Outputs/
├── README.md
└── requirements.txt
```

## How to Run
### 1) Create and activate a virtual environment (recommended)
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Run a solver
From the project root (`Student_ID1_Student_ID2_Student_ID3/`):
```bash
python -m Source.main Inputs/input-01.txt -a bt -o Outputs/output-01.txt
```

Algorithms (`-a/--algorithm`):
- `fc`: Forward Chaining
- `bc`: Backward Chaining
- `astar`: A*
- `bt`: Backtracking

## Notes
- The provided parser in `Source/utils/parser.py` is a template. Adjust it to match the exact input format released by the instructor.
- Solver modules are currently stubs and raise `NotImplementedError` until implemented.

