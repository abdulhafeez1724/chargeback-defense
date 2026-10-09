"""Naya reason/evidence type add ho to har jagah (policy, PDF, form) update hona chahiye."""

import re
from pathlib import Path

from domain.entities import DisputeReason, EvidenceType
from domain.evidence_policy import required_for
from infrastructure.pdf_renderer import _CLAIM, _EVIDENCE_LABEL, _INTRO

_APP_HTML = (Path(__file__).parent.parent / "presentation/web/app.html").read_text()


def _js_keys(const_name: str) -> set[str]:
    block = re.search(rf"const {const_name} = \{{(.*?)\}};", _APP_HTML, re.S)
    assert block, const_name
    return set(re.findall(r"^\s*(\w+):", block.group(1), re.M))


def test_every_reason_has_policy_and_intro() -> None:
    for reason in DisputeReason:
        assert required_for(reason)
        assert reason in _INTRO


def test_every_evidence_type_has_label_and_claim() -> None:
    assert set(_EVIDENCE_LABEL) == set(EvidenceType)
    assert set(_CLAIM) == set(EvidenceType)


def test_form_lists_match_domain() -> None:
    assert _js_keys("LABELS") == {t.value for t in EvidenceType}
    assert _js_keys("REASONS") == {r.value for r in DisputeReason}
