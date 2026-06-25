import networkx as nx
import os
import json
from typing import Dict, Any, List, Optional
from src.config import Config
from src.core.utils import setup_logger
from src.core.schema import CapabilitySchema, ExecutionTrace

logger = setup_logger(__name__)

class KnowledgeGraphMemory:
    def __init__(self):
        self.graph_file = Config.GRAPH_MEMORY_FILE
        self.graph = self._load_graph()
        
    def _load_graph(self) -> nx.DiGraph:
        """Loads the graph from disk if it exists, otherwise returns a new Directed Graph."""
        if os.path.exists(self.graph_file):
            try:
                g = nx.read_gml(self.graph_file)
                logger.info(f"Loaded existing knowledge graph from {self.graph_file} with {g.number_of_nodes()} nodes.")
                return g
            except Exception as e:
                logger.error(f"Failed to load graph: {e}. Starting fresh.")
                return nx.DiGraph()
        else:
            logger.info("No existing graph found. Creating a new one.")
            return nx.DiGraph()
            
    def save_graph(self):
        """Persists the graph to disk."""
        try:
            # GML only supports int, float, str. Convert dicts/lists to JSON strings
            graph_to_save = self.graph.copy()
            for node, data in graph_to_save.nodes(data=True):
                for k, v in data.items():
                    if isinstance(v, (dict, list)):
                        graph_to_save.nodes[node][k] = json.dumps(v)
            nx.write_gml(graph_to_save, self.graph_file)
            logger.debug(f"Graph saved to {self.graph_file}")
        except Exception as e:
            logger.error(f"Failed to save graph: {e}")

    # --- Capability Memory ---

    def add_capability(self, capability: CapabilitySchema):
        """Registers a new capability (tool) in the graph."""
        node_id = f"TOOL_{capability.name}"
        self.graph.add_node(
            node_id, 
            type="capability",
            name=capability.name,
            description=capability.description,
            parameters=json.dumps(capability.parameters),
            code=capability.code,
            success_rate=1.0,
            execution_count=0
        )
        # Add constraints as separate nodes linked to the tool
        for constraint in capability.constraints:
            self.add_constraint(node_id, constraint)
        self.save_graph()
        logger.info(f"Added new capability: {capability.name}")

    def get_capability(self, name: str) -> Optional[CapabilitySchema]:
        """Retrieves a capability by name."""
        node_id = f"TOOL_{name}"
        if self.graph.has_node(node_id):
            data = self.graph.nodes[node_id]
            # Get constraints
            constraints = [
                self.graph.nodes[n]['description'] 
                for n in self.graph.successors(node_id) 
                if self.graph.nodes[n].get('type') == 'constraint'
            ]
            
            # Parse parameters if it's a string (from loaded GML)
            params = data['parameters']
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except:
                    params = {}

            return CapabilitySchema(
                name=data['name'],
                description=data['description'],
                parameters=params,
                code=data['code'],
                constraints=constraints
            )
        return None

    def get_all_capabilities(self) -> List[CapabilitySchema]:
        """Returns all registered capabilities."""
        caps = []
        for node, data in self.graph.nodes(data=True):
            if data.get('type') == 'capability':
                caps.append(self.get_capability(data['name']))
        return caps

    def update_capability_stats(self, name: str, success: bool):
        """Updates the success rate of a capability based on execution outcome."""
        node_id = f"TOOL_{name}"
        if self.graph.has_node(node_id):
            data = self.graph.nodes[node_id]
            exec_count = data.get('execution_count', 0)
            current_rate = data.get('success_rate', 1.0)
            
            # Simple moving average for success rate
            new_count = exec_count + 1
            val = 1.0 if success else 0.0
            new_rate = ((current_rate * exec_count) + val) / new_count
            
            self.graph.nodes[node_id]['execution_count'] = new_count
            self.graph.nodes[node_id]['success_rate'] = new_rate
            self.save_graph()

    def add_constraint(self, tool_node_id: str, constraint_desc: str):
        """Adds a constraint node and links it to a tool."""
        constraint_id = f"CONSTRAINT_{hash(constraint_desc)}"
        self.graph.add_node(
            constraint_id,
            type="constraint",
            description=constraint_desc
        )
        self.graph.add_edge(tool_node_id, constraint_id, relation="HAS_CONSTRAINT")
        self.save_graph()
        logger.info(f"Added constraint to {tool_node_id}: {constraint_desc}")

    # --- Execution Memory ---

    def record_execution(self, trace: ExecutionTrace):
        """Records an execution trace in the graph."""
        exec_id = f"EXEC_{trace.task_id}_{hash(str(trace.inputs))}"
        self.graph.add_node(
            exec_id,
            type="execution",
            task_id=trace.task_id,
            tool_name=trace.tool_name,
            inputs=json.dumps(trace.inputs),
            status=trace.status,
            result=trace.result or "",
            error_message=trace.error_message or "",
            latency_ms=trace.latency_ms or 0
        )
        
        # Link execution to the tool it used
        tool_node_id = f"TOOL_{trace.tool_name}"
        if self.graph.has_node(tool_node_id):
            self.graph.add_edge(exec_id, tool_node_id, relation="USED_TOOL")
            
        self.update_capability_stats(trace.tool_name, trace.status == 'success')
        self.save_graph()
        logger.info(f"Recorded execution {exec_id} (Status: {trace.status})")
