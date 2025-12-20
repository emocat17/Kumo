import os
from datetime import datetime

class Logger:
    def __init__(self, log_dir: str):
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, f'{ts}.log')

    def _ts(self) -> str:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def log(self, msg: str):
        line = f'[{self._ts()}] {msg}'
        try:
            print(line)
        except Exception:
            pass
        try:
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except Exception:
            pass
