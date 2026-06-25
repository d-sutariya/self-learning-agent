import os
import sys

# Ensure src is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import Config
from src.core.agent import PlatformAgent
from src.core.utils import setup_logger

logger = setup_logger(__name__)

def main():
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        print(f"Error: {e}")
        print("Please check your .env file.")
        return

    agent = PlatformAgent()
    
    print("\n" + "="*50)
    print("🤖 Autonomous Platform Intelligence Agent")
    print("="*50)
    print("Ready to execute GitHub instructions.")
    print("Type 'exit' to quit.\n")
    
    # We use a static thread_id for this demo, 
    # but in production, you'd generate a new one per session
    config = {"configurable": {"thread_id": "session_1"}}
    
    while True:
        try:
            instruction = input("User Instruction > ")
            if instruction.lower().strip() in ['exit', 'quit']:
                break
            if not instruction.strip():
                continue
                
            agent.run(instruction, config=config)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            print(f"\nAn error occurred: {e}\n")

if __name__ == "__main__":
    main()
