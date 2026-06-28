import os
import sys
import time
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.config import Config
from src.core.agent import PlatformAgent

def run_instruction(agent, instruction_num, instruction_text, config):
    print(f"\n{'='*60}")
    print(f"🚀 INSTRUCTION {instruction_num}: '{instruction_text}'")
    print(f"{'='*60}")
    
    start_time = time.time()
    try:
        agent.run(instruction_text, config=config)
    except Exception as e:
        print(f"Run threw an exception: {e}")
    finally:
        elapsed = time.time() - start_time
        print(f"Instruction {instruction_num} completed in {elapsed:.2f} seconds.")

def main():
    try:
        Config.validate()
    except Exception as e:
        print(f"Error validating config: {e}")
        return

    # Clear memory graph for a clean demo
    graph_path = os.path.join(Config.DATA_DIR, "memory_graph.gml")
    if os.path.exists(graph_path):
        os.remove(graph_path)
        print("Cleared previous Knowledge Graph Memory for a fresh demo.")

    agent = PlatformAgent()
    config = {"configurable": {"thread_id": "demo_session_final"}}
    
    # Requirement: 3 Sequential Instructions that build on each other
    instructions = [
        "Authenticate with GitHub and fetch my user profile.",
        "Fetch the repository details for 'News-Sentiment-Analyzer-TTS'.",
        "Get the list of open issues for the 'News-Sentiment-Analyzer-TTS' repository."
    ]
    
    print("\n--- Starting Sequential Demo ---")
    print("This demo proves persistent memory: Subsequent instructions reuse capabilities and learned constraints from previous instructions.")
    
    for i, inst in enumerate(instructions, 1):
        # We loop twice per instruction to allow the agent to correct any immediate API parameter constraints
        print(f"\n[Running Execution Loop for Instruction {i}]")
        for attempt in range(1, 3):
            print(f"\nAttempt {attempt}/2...")
            start_time = time.time()
            agent.run(inst, config=config)
            elapsed = time.time() - start_time
            print(f"Attempt {attempt} finished in {elapsed:.2f}s")
            
        time.sleep(1) # Small pause for readability

if __name__ == "__main__":
    main()
