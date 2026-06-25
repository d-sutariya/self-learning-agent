import logging
import os
from datetime import datetime
from src.config import Config

def setup_logger(name: str) -> logging.Logger:
    """Sets up a production-ready logger that writes to both console and file."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console Handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File Handler
        log_file = os.path.join(Config.LOGS_DIR, f"agent_{datetime.now().strftime('%Y%m%d')}.log")
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
    return logger

# Globally patch requests to log external API calls
import requests

_original_request = requests.Session.request

def _patched_request(self, method, url, **kwargs):
    api_logger = setup_logger("external_api")
    api_logger.info(f"API Request: {method} {url}")
    
    # Log safe headers and payload
    if 'headers' in kwargs:
        safe_headers = {k: v for k, v in kwargs['headers'].items() if k.lower() != 'authorization'}
        api_logger.debug(f"Request Headers: {safe_headers}")
    if 'json' in kwargs or 'data' in kwargs:
        api_logger.debug(f"Request Payload: {kwargs.get('json') or kwargs.get('data')}")
        
    response = _original_request(self, method, url, **kwargs)
    
    api_logger.info(f"API Response: {response.status_code} for {url}")
    try:
        # Log response body (truncated to 1000 chars to avoid overwhelming logs)
        body = response.text
        if len(body) > 1000:
            body = body[:1000] + "... [TRUNCATED]"
        api_logger.debug(f"Response Body: {body}")
    except Exception:
        api_logger.debug("Response Body: <Unable to decode>")
        
    return response

requests.Session.request = _patched_request
