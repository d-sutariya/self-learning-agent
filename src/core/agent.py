import json
import sqlite3
from typing import TypedDict, List, Dict, Any, Literal
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from src.config import Config
from src.core.utils import setup_logger
from src.core.memory import KnowledgeGraphMemory
from src.core.synthesis import CapabilitySynthesizer
from src.core.schema import ExecutionTrace
import os

logger = setup_logger(__name__)

# State definition
class AgentState(TypedDict):
    instruction: str
    subtasks: List[Dict[str, Any]]
    current_index: int
    results: List[Dict[str, Any]]
    status: str
    error: str

class PlatformAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile", 
            api_key=Config.GROQ_API_KEY,
            temperature=0.1
        )
        self.memory = KnowledgeGraphMemory()
        self.synthesizer = CapabilitySynthesizer()
        
        # Build LangGraph
        workflow = StateGraph(AgentState)
        workflow.add_node("planner", self._plan_node)
        workflow.add_node("executor", self._execute_node)
        workflow.add_node("reporter", self._report_node)
        
        workflow.set_entry_point("planner")
        workflow.add_conditional_edges(
            "planner",
            self._route_after_plan,
            {
                "execute": "executor",
                "report": "reporter"
            }
        )
        workflow.add_conditional_edges(
            "executor",
            self._route_after_execute,
            {
                "continue": "executor",
                "report": "reporter"
            }
        )
        workflow.add_edge("reporter", END)
        
        # Set up Sqlite Checkpointing
        db_path = os.path.join(Config.DATA_DIR, "checkpoints.sqlite")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.checkpointer = SqliteSaver(self.conn)
        
        self.app = workflow.compile(checkpointer=self.checkpointer)

    def _plan_node(self, state: AgentState) -> Dict[str, Any]:
        """Decomposes the natural language instruction into subtasks."""
        logger.info(f"Planning for instruction: {state['instruction']}")
        
        # Inject memory of past errors/constraints into the planner
        all_caps = self.memory.get_all_capabilities()
        constraints_str = ""
        for cap in all_caps:
            if cap.constraints:
                constraints_str += f"- {cap.name} constraints: {', '.join(cap.constraints)}\n"
                
        prompt = f"""
        You are an AI planner for GitHub automation. 
        Decompose this instruction into sequential subtasks: "{state['instruction']}"
        
        Known capability constraints you MUST respect:
        {constraints_str or 'None yet.'}
        
        Respond with ONLY a JSON array of objects, each containing:
        - "intent": clear description of the action
        - "tool_hint": (optional) a guess at the tool name needed
        - "params": dictionary of ALL REQUIRED parameters explicitly extracted from the instruction (e.g. "repository", "owner", etc.). Do not leave this empty if the instruction contains specific target names or IDs.
        """
        
        try:
            response = self.llm.invoke(prompt)
            json_str = response.content.strip()
            if json_str.startswith("```json"): json_str = json_str[7:]
            if json_str.endswith("```"): json_str = json_str[:-3]
            
            subtasks = json.loads(json_str)
            return {"subtasks": subtasks, "current_index": 0, "results": [], "status": "planning_success"}
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return {"subtasks": [], "status": "planning_failed", "error": str(e)}

    def _route_after_plan(self, state: AgentState) -> Literal["execute", "report"]:
        if state["status"] == "planning_failed" or not state["subtasks"]:
            return "report"
        return "execute"

    def _execute_node(self, state: AgentState) -> Dict[str, Any]:
        """Executes the current subtask."""
        idx = state["current_index"]
        task = state["subtasks"][idx]
        intent = task["intent"]
        params = task.get("params", {})
        if params is None:
            params = {}
        
        logger.info(f"Executing subtask {idx+1}/{len(state['subtasks'])}: {intent}")
        
        # 1. Match intent to existing capabilities (Simplistic keyword match for now)
        matched_tool = None
        for cap in self.memory.get_all_capabilities():
            # In a real system, we'd use embedding similarity here
            if task.get("tool_hint") and task["tool_hint"].lower() in cap.name.lower():
                matched_tool = cap
                break
                
        # 2. Synthesize if missing
        if not matched_tool:
            logger.warning(f"No tool found for '{intent}'. Initiating synthesis.")
            success, result = self.synthesizer.synthesize(intent)
            if success:
                self.memory.add_capability(result)
                matched_tool = result
            else:
                logger.error(f"Synthesis failed: {result}")
                return self._fail_execution(state, intent, "Synthesis Failed")

        # 3. Execute the tool
        try:
            # We use eval here for the generated code. 
            # In production, this needs a secure sandbox.
            loc = {}
            exec(matched_tool.code, globals(), loc)
            func = loc['run']
            
            import time
            start = time.time()
            result = func(params)
            latency = int((time.time() - start) * 1000)
            
            # Record Success
            trace = ExecutionTrace(
                task_id=f"TASK_{hash(state['instruction'])}",
                tool_name=matched_tool.name,
                inputs=params,
                status="success",
                result=str(result),
                latency_ms=latency
            )
            self.memory.record_execution(trace)
            
            results = state["results"] + [{"task": intent, "status": "success", "output": result}]
            return {"results": results, "current_index": idx + 1, "status": "executing"}
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Execution failed: {error_msg}")
            
            # Self-Learning: Extract constraint on failure
            if "422" in error_msg or "Validation" in error_msg or "rate limit" in error_msg.lower():
                constraint = f"Discovered runtime constraint: {error_msg}"
                self.memory.add_constraint(f"TOOL_{matched_tool.name}", constraint)
                
            # Record Failure
            trace = ExecutionTrace(
                task_id=f"TASK_{hash(state['instruction'])}",
                tool_name=matched_tool.name,
                inputs=params,
                status="error",
                error_message=error_msg
            )
            self.memory.record_execution(trace)
            return self._fail_execution(state, intent, error_msg)

    def _fail_execution(self, state: AgentState, intent: str, error: str) -> Dict[str, Any]:
        results = state["results"] + [{"task": intent, "status": "failed", "error": error}]
        # We handle partial failure gracefully by stopping further execution and reporting
        return {"results": results, "status": "partial_failure", "error": error}

    def _route_after_execute(self, state: AgentState) -> Literal["continue", "report"]:
        if state["status"] == "partial_failure" or state["current_index"] >= len(state["subtasks"]):
            return "report"
        return "continue"

    def _report_node(self, state: AgentState) -> Dict[str, Any]:
        """Generates the structured execution report."""
        logger.info("Generating execution report.")
        report = {
            "instruction": state["instruction"],
            "overall_status": state["status"],
            "steps_completed": len([r for r in state["results"] if r["status"] == "success"]),
            "total_steps": len(state["subtasks"]),
            "details": state["results"]
        }
        
        if state.get("error"):
            report["critical_error"] = state["error"]
            
        print("\n--- STRUCTURED EXECUTION REPORT ---")
        print(json.dumps(report, indent=2))
        print("-----------------------------------\n")
        
        return {"status": "completed"}

    def run(self, instruction: str, config: dict = None):
        logger.info(f"Starting agent run for: {instruction}")
        initial_state = {
            "instruction": instruction,
            "subtasks": [],
            "current_index": 0,
            "results": [],
            "status": "started",
            "error": ""
        }
        for s in self.app.stream(initial_state, config=config):
            pass 
