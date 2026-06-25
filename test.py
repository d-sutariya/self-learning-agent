import os
import sys

# Ensure src is in the python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.config import Config
from src.core.agent import PlatformAgent
import time

def main():
    try:
        Config.validate()
    except Exception as e:
        print(f"Error validating config: {e}")
        return

    agent = PlatformAgent()
    config = {"configurable": {"thread_id": "loop_test_session_1"}}
    
    instruction = "Get the list of open issues in the 'News-Sentiment-Analyzer-TTS' repository for the authenticated user."
    
    print(f"\n--- Running agent 10 times for instruction: '{instruction}' ---")
    
    for i in range(1, 4):
        print(f"\n[{i}/10] Executing run...")
        start_time = time.time()
        try:
            agent.run(instruction, config=config)
        except Exception as e:
            print(f"Run {i} threw an exception: {e}")
        finally:
            elapsed = time.time() - start_time
            print(f"Run {i} completed in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    main()
