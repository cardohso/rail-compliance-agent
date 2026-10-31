"""When the verifier rejects a rule, the extractor is shown why and revises once.

Found by the second run of core: the model filed the 'if it can be demonstrated' exception as a
relaxation with no conditions, the rule was rejected with a clear message, and the agent asked
again with another focus. The extraction model is deterministic, so it wrote the same rule. The
message has to reach the model that wrote the rule."""

from rail_compliance.models import RequirementDraft, RuleDraft
from rail_compliance.tools.extract import extract_requirement
from tests.factories import passage

HEIGHT = "steps.internal_step_height_mm"
TEXT = (
    "The height of each step may be increased to a maximum of 230 mm if it can be demonstrated "
    "that this achieves a reduction of one in the total number of steps required."
)
P = passage(TEXT, id_="tsi-prm:Annex §4.2.2.11.2#1")


def draft(**rule):
    fields = dict(parameter=HEIGHT, subject="internal_step", comparator="<=", value=230, unit="mm")
    return RequirementDraft(found=True, passage_id=P.id, quote=TEXT,
                            rule=RuleDraft(**{**fields, **rule}))  # fmt: skip


BAD = draft(relaxes=True, contingency="a reduction of one in the total number of steps")
GOOD = draft(contingency="a reduction of one in the total number of steps")


class Sequence:
    """Returns the drafts in order and records every prompt."""

    def __init__(self, *drafts):
        self.drafts, self.users = list(drafts), []

    def extract(self, system, user, schema):
        self.users.append(user)
        return self.drafts[min(len(self.users), len(self.drafts)) - 1]


def test_a_rejected_rule_is_sent_back_with_the_reason_and_the_revision_is_verified():
    llm = Sequence(BAD, GOOD)
    result = extract_requirement([P], HEIGHT, llm)
    assert result.status == "found" and result.requirement.contingency
    assert len(llm.users) == 2
    second = llm.users[1]
    assert llm.users[0] in second  # the same request ...
    assert "rejected" in second and "relaxes to false" in second  # ... plus why it was rejected


def test_it_revises_at_most_once():
    llm = Sequence(BAD, BAD, GOOD)
    result = extract_requirement([P], HEIGHT, llm)
    assert result.status == "unverified" and len(llm.users) == 2


def test_a_rule_that_verifies_is_not_asked_twice():
    llm = Sequence(GOOD, BAD)
    assert extract_requirement([P], HEIGHT, llm).status == "found" and len(llm.users) == 1


def test_not_found_is_not_a_rejection():
    llm = Sequence(RequirementDraft(found=False, note="refers to an external standard"), GOOD)
    result = extract_requirement([P], HEIGHT, llm)
    assert result.status == "not_found" and len(llm.users) == 1


def test_a_revision_that_gives_up_is_respected():
    llm = Sequence(BAD, RequirementDraft(found=False, note="no numeric rule here"))
    result = extract_requirement([P], HEIGHT, llm)
    assert result.status == "not_found" and result.reason == "no numeric rule here"


def test_a_quote_that_is_not_in_the_passage_is_also_sent_back():
    invented = draft(contingency="x").model_copy(update={"quote": "Steps shall be 230 mm."})
    llm = Sequence(invented, GOOD)
    assert extract_requirement([P], HEIGHT, llm).status == "found"
    assert "was not found in the passage" in llm.users[1]
