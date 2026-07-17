from PySide6.QtCore import QCoreApplication

from clearcue.config import AppConfig, ConfigStore
from clearcue.services.session_controller import SessionController
from clearcue.storage.database import Database


NOISY_CAREER_CHANGE_QUESTION = (
    "Given that you are making a career change here, especially with finishing a "
    "master's degree in education, if a position becomes available in your current "
    "field down here in the Jackson-boat area. How do you approach being offered "
    "this job versus being offered a position in your field and... position becomes "
    "available in your current field down here in the Jacksonville area. How do you "
    "approach being offered this job versus being offered a position in your field? "
    "And I'm asking that in the now. in the future. Thank you. Shh."
)


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


def test_cancelled_answer_deltas_are_ignored(tmp_path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    controller = SessionController(
        Database(tmp_path / "session.db"),
        ConfigStore(tmp_path / "settings.json"),
        AppConfig(save_transcripts=False),
    )
    received = []
    controller.answer_delta.connect(lambda question, delta: received.append((question, delta)))
    controller._answer_request_id = 4
    controller._handle_answer_delta(3, "old question", "stale")
    controller._handle_answer_delta(4, "new question", "current")
    app.processEvents()
    assert received == [("new question", "current")]
    controller.cancel_answer()
    controller._handle_answer_delta(4, "new question", "late")
    assert received == [("new question", "current")]
    controller.shutdown()


def test_live_transcript_bolds_question_candidate_and_reverts_remark(tmp_path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    controller = SessionController(
        Database(tmp_path / "session.db"),
        ConfigStore(tmp_path / "settings.json"),
        AppConfig(auto_generate=False, save_transcripts=False),
    )
    states = []
    controller.live_transcript_changed.connect(
        lambda committed, regular, question: states.append(
            (tuple(committed), regular, question)
        )
    )

    controller._handle_transcript(
        "Interviewer",
        "We build accessibility tools. Tell me about",
    )
    assert states[-1][1] == "We build accessibility tools."
    assert states[-1][2] == "Tell me about"

    controller._question_timer.stop()
    controller._finalize_pending_question()
    assert states[-1][0][-1] == (
        "We build accessibility tools. Tell me about",
        False,
    )

    controller._handle_transcript("Interviewer", "We build accessibility tools.")
    assert states[-1][2] == ""
    controller._question_timer.stop()
    controller._finalize_pending_question()
    assert states[-1][0][-1] == ("We build accessibility tools.", False)
    app.processEvents()
    controller.shutdown()


def test_noisy_tail_keeps_question_bold_and_auto_answers_reconstructed_question(
    tmp_path,
) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    controller = SessionController(
        Database(tmp_path / "session.db"),
        ConfigStore(tmp_path / "settings.json"),
        AppConfig(auto_generate=True, save_transcripts=False),
    )
    states = []
    answers = []
    controller.live_transcript_changed.connect(
        lambda committed, regular, question: states.append(tuple(committed))
    )
    controller.ask = lambda question, style=None: answers.append(question)

    controller._handle_transcript("Interviewer", NOISY_CAREER_CHANGE_QUESTION)
    assert any(
        emphasized and text.startswith("How do you approach")
        for text, emphasized in states[-1]
    )
    controller._question_timer.stop()
    controller._finalize_pending_question()
    assert len(answers) == 1
    assert "career change" in answers[0].lower()
    assert "jacksonville" in answers[0].lower()
    assert "both now and in the future" in answers[0].lower()
    app.processEvents()
    controller.shutdown()
