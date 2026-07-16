from PySide6.QtCore import QCoreApplication

from clearcue.config import AppConfig, ConfigStore
from clearcue.services.session_controller import SessionController
from clearcue.storage.database import Database


def test_question_fragments_form_live_and_auto_answer_once_after_pause(tmp_path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    config = AppConfig(auto_generate=True, save_transcripts=False)
    controller = SessionController(
        Database(tmp_path / "session.db"),
        ConfigStore(tmp_path / "settings.json"),
        config,
    )
    forming = []
    answers = []
    controller.question_ready.connect(forming.append)
    controller.ask = lambda question, style=None: answers.append(question)

    controller._handle_transcript("Interviewer", "Tell me about")
    controller._handle_transcript("Interviewer", "yourself")
    app.processEvents()
    assert answers == []

    controller._question_timer.stop()
    controller._finalize_pending_question()
    assert forming[-1] == "Tell me about yourself?"
    assert answers == ["Tell me about yourself?"]
    controller.shutdown()
