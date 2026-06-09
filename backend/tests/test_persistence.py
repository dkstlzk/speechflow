from backend.app.services.persistence.summaries import (
    save_summary,
    get_summary,
)
from backend.app.services.persistence.actions import (
    save_action_items,
    list_action_items,
)


from backend.app.services.persistence.session_repository import create_session

def test_summary_roundtrip(db_session):
    session = create_session(db_session, "test", "test.wav")
    session.id = 9999
    db_session.commit()

    save_summary(
        9999,
        "test summary",
        "test mom",
    )

    result = get_summary(9999)

    assert result is not None
    assert result["summary"] == "test summary"
    assert result["mom"] == "test mom"


def test_action_items_roundtrip(db_session):
    session = create_session(db_session, "test", "test.wav")
    session.id = 9998
    db_session.commit()

    save_action_items(
        9998,
        [
            "item one",
            "item two",
        ],
    )

    result = list_action_items(9998)

    assert len(result) == 2
    assert result[0]["text"] == "item one"
    assert result[1]["text"] == "item two"