from ..settings import Settings

class Agent:
    def __init__(self, llm: str | None = None):
        # Use instance override or global setting
        self.llm = llm or Settings.llm
        
    def generate(self):
        # Always use current global setting unless overridden
        model = self.llm or Settings.llm
        temp = Settings.temperature  # Always use global 