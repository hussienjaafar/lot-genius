from backend.lotgenius.gating import passes_evidence_gate


def test_gate_high_trust_id_bypass():
    r = passes_evidence_gate(
        {}, sold_comps_count_180d=0, has_secondary_signal=False, has_high_trust_id=True
    )
    assert r.passed and r.core_included


def test_gate_pass_on_comps_and_secondary():
    r = passes_evidence_gate(
        {}, sold_comps_count_180d=3, has_secondary_signal=True, has_high_trust_id=False
    )
    assert r.passed and r.core_included


def test_gate_fail_without_secondary():
    r = passes_evidence_gate(
        {}, sold_comps_count_180d=4, has_secondary_signal=False, has_high_trust_id=False
    )
    assert not r.passed and not r.core_included and "secondary:no" in r.tags


def test_gate_fail_without_comps():
    r = passes_evidence_gate(
        {}, sold_comps_count_180d=2, has_secondary_signal=True, has_high_trust_id=False
    )
    assert not r.passed and not r.core_included and "comps:<3" in r.tags
