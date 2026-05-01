from pydantic import BaseModel
from typing import Literal
import uuid, datetime

class A2AMessage(BaseModel):
    message_id: str = ""
    sender: Literal["proponent", "opponent", "judge", "orchestrator"]
    receiver: Literal["proponent", "opponent", "judge", "orchestrator"]
    round_number: int
    message_type: Literal["argument", "rebuttal", "score", "verdict"]
    content: str
    evidence: list[str] = []
    timestamp: str = ""

    def model_post_init(self, _):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.datetime.utcnow().isoformat()