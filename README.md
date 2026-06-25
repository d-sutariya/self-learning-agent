# Autonomous Platform Intelligence Agent

This repository contains an autonomous, self-improving platform agent that integrates with the GitHub API. Rather than relying on hardcoded API wrappers or static tools, this agent is designed to **dynamically synthesize its own capabilities at runtime**, execute them, and learn from its mistakes using a Persistent Knowledge Graph Memory.

## 🚀 Key Features

* **Dynamic Capability Synthesis:** Uses an LLM (Llama 3.3 via Groq) to write raw `requests` based Python scripts on the fly to interact with the GitHub API when a required tool is missing.
* **Persistent Knowledge Graph Memory:** Uses `NetworkX` (serialized to `.gml`) to explicitly map relationships between Executions, Tools, and runtime API Errors (Constraints).
* **Self-Learning Loop:** When an API call fails (e.g., `401 Bad Credentials`, Missing Parameters), the agent securely catches the error, halts execution gracefully, and explicitly records the error to the Knowledge Graph. On subsequent runs, the Planner reads these past constraints and successfully changes its parameter generation to succeed.
* **Robust Error Handling & Logging:** External API requests and responses are intercepted and logged to `logs/agent_YYYYMMDD.log` using standard Python logging, while Authorization headers are safely stripped.

## 🛠️ Project Structure

```text
├── src/
│   ├── core/
│   │   ├── agent.py       # Core LangGraph execution, planning, and routing
│   │   ├── memory.py      # NetworkX Knowledge Graph wrapper for storing capabilities and constraints
│   │   ├── schema.py      # Pydantic schemas for data structures
│   │   ├── synthesis.py   # LLM prompt and engine for dynamically writing API scripts
│   │   └── utils.py       # Intercept logging and setup
│   ├── config.py          # Environment and path configurations
│   └── main.py            # CLI entry point (optional)
├── test.py                # 10-iteration stress test showing the self-learning loop in action
├── ARCHITECTURE.md        # Detailed breakdown of Graph Memory and Synthesis
└── DEMO.md                # Walkthrough script for the 15-minute presentation
```

## ⚙️ Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/d-sutariya/self-learning-agent.git
   cd self-learning-agent
   ```

2. **Set up the virtual environment:**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Rename `.env.example` to `.env` and fill in your keys:
   ```env
   GROQ_API_KEY=your_groq_api_key
   GITHUB_TOKEN=your_github_classic_or_fine_grained_token
   ```
   *(Note: Fine-grained GitHub tokens must have explicit repository read access to work with specific repos).*

## 🧪 Running the Demo

To see the agent dynamically synthesize a capability, fail due to a missing parameter, learn from the graph database, and succeed on the next execution, run the loop test:

```bash
python test.py
```

Check the generated `logs/agent_YYYYMMDD.log` file to view the full request/response interception, including the API payload, HTTP status codes, and the LLM synthesizing the Python code!

---

*This project was completed as part of the Watermelon Software Recruitment Assignment.*
