# Architecture

## 1. What does your memory system store, and why did you structure it that way?
Our memory system is structured as a dual-layer Knowledge Graph (`memory_graph.gml`). We chose a graph structure because it naturally models the relationships between intents, tools, and past executions, allowing for fast, structured retrieval without relying on slow or imprecise vector similarity searches.
- **Capability Memory:** Stores the actual synthesized Python code, tool schemas, and descriptions for capabilities the agent has learned.
- **Execution Memory:** Stores historical execution nodes—recording what instructions were given, what tools were called, the parameters used, and whether the execution was a success or a failure. 

## 2. How does capability synthesis work in your implementation?
When the agent's planner encounters an instruction that cannot be fulfilled by its current tools, it identifies a "capability gap." It then invokes the `CapabilitySynthesizer`. 
The synthesizer prompts an LLM (Llama 3.3 via Groq) to generate a self-contained Python function using the `requests` library to fulfill the specific API requirement. To ensure reliability and avoid common JSON escaping errors, the LLM is instructed to return the Python code within a standard Markdown code block. The system extracts the code using Regex, compiles it dynamically using Python's `compile()` to catch syntax errors, and if successful, registers it permanently into the Capability Memory.

## 3. What is your learning signal, and what does the agent do differently on run N vs run 1?
**Learning Signal:** The agent tracks execution time and capability persistence. The primary learning signal is the successful mapping of an intent to a working, synthesized tool. 
**Run 1 vs Run N:** On Run 1, when the agent receives an instruction, it must spend roughly 6-8 seconds reasoning about the API, synthesizing the Python code, compiling it, and executing it. On Run N, when the agent receives a similar instruction, it completely bypasses the LLM synthesis bottleneck. It searches its Capability Memory, retrieves the exact Python tool that succeeded previously, and executes it immediately. As a result, execution time drops by over 70% (e.g., from ~7.5 seconds down to ~2.1 seconds), and the agent stops repeating initial runtime errors.
