import uvicorn

from .config import load_settings
from .main import create_app

if __name__ == "__main__":
    s = load_settings()
    uvicorn.run(create_app(s), host=s.server_host, port=s.server_port)
