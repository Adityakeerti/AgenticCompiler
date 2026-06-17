# Agentic Compiler

The Agentic Compiler is a custom programming language compiler augmented with a Reinforcement Learning (RL) based AI agent that automatically intercepts and fixes structural errors in your code.

This project consists of three main components:
1. **The Agentic (RL) Pipeline** (Python)
2. **The Core Compiler** (Java)
3. **The Visualizer** (React)

---

## 1. Run the Agentic Compiler (The AI Auto-Fixer)
This is the core feature of the project. It uses a Python RL agent to automatically fix `.cpy` files that fail to compile.

First, install the required dependencies:
```cmd
cd agentic_pipeline
pip install -r requirements.txt
```

Run the agent to fix a file:
```cmd
python run_agent.py --file ../Compiler/hello.cpy
```

Or run the agent in interactive mode:
```cmd
python run_agent.py --interactive
```

---

## 2. Run the Standard Compiler (Without AI)
If you want to manually compile and run a `.cpy` file using the base Java compiler, use the provided batch script:

```cmd
cd Compiler
.\cpy.bat compile run hello.cpy
```

---

## 3. Run the React Visualizer
To view the frontend visualizer interface:

```cmd
cd visualizer
npm install
npm run dev
```
This will start a local development server for the UI.
