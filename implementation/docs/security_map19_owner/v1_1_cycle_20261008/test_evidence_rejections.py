"""Meaningful counterexamples for identity, foreign instrument and PIT mistakes."""
import copy
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

import verify_mapping
from verify_mapping import verify
from synthetic_mapping_evidence import build


class EvidenceRejections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        root = Path(directory.name)
        cls.document = build(root)
        override = patch.object(verify_mapping, "ROOT", root)
        override.start()
        cls.addClassCleanup(override.stop)

    def rejected(self, mutation):
        document = copy.deepcopy(self.document)
        mutation(document)
        with self.assertRaises(ValueError):
            verify(document)

    def test_independent_identity_only_evidence_passes(self):
        self.assertEqual(verify(self.document)["current_target_refs"], "19/19")

    def test_generated_xml_contains_no_price_share_or_value_fields(self):
        import gzip
        import xml.etree.ElementTree as ET
        pin = self.document["source_pins"]["frozen_nport_original_replay"]
        data = gzip.decompress((verify_mapping.ROOT / pin["replay_path"]).read_bytes())
        tags = {element.tag for element in ET.fromstring(data).iter()}
        self.assertEqual(tags, {"syntheticIdentityEvidence", "invstOrSec", "name", "title", "cusip", "assetCat", "curCd", "invCountry", "lei", "isin"})

    def test_missing_explicit_fixture_fails_closed(self):
        document = copy.deepcopy(self.document)
        document["source_pins"]["frozen_nport_original_replay"]["replay_path"] = "missing-independent-fixture"
        with self.assertRaisesRegex(ValueError, "NOT_AVAILABLE"):
            verify(document)

    def test_default_archived_evidence_is_explicitly_unavailable(self):
        self.assertEqual(verify()["status"], "NOT_AVAILABLE")

    def test_cik_cannot_be_security_identity(self):
        self.rejected(lambda d: d["rows"][5].update(security_ref={"scheme": "CIK", "value": "0001045810"}))

    def test_alphabet_class_c_rejected_even_with_same_issuer(self):
        def mutate(d):
            row = d["rows"][11]
            row["security_ref"]["value"] = row["security_id"] = "US02079K1079"
            row["c39_security_identity"].update(security_id="US02079K1079", share_class="C",
                                               identifiers=[["ISIN", "US02079K1079"], ["CUSIP", "02079K107"]])
            row["security_evidence"].update(cusip="02079K107", title="ALPHABET INC")
        self.rejected(mutate)

    def test_asml_euronext_security_cannot_replace_nasdaq_form(self):
        def mutate(d):
            row = d["rows"][0]
            row["security_ref"]["value"] = row["security_id"] = "NL0010273215"
            row["c39_security_identity"].update(security_id="NL0010273215", identifiers=[["ISIN", "NL0010273215"]])
        self.rejected(mutate)

    def test_asml_not_assumed_adr(self):
        self.rejected(lambda d: d["rows"][0].update(share_form="ADR"))

    def test_tokyo_otc_adr_cannot_replace_user_tse8035(self):
        self.rejected(lambda d: d["rows"][3].update(security_ref={"scheme": "EXCHANGE_CODE", "exchange": "OTC", "code": "TELWY"}))

    def test_hanmi_code_preserves_leading_zero(self):
        self.rejected(lambda d: d["rows"][4]["security_ref"].update(code="42700"))

    def test_foreign_pair_is_not_fabricated_isin_or_full_hierarchy(self):
        self.rejected(lambda d: d["rows"][4].update(security_id="KRX:042700"))

    def test_frozen_source_tampering_rejected(self):
        self.rejected(lambda d: d["source_pins"]["frozen_nport_original_replay"].update(sha256="0" * 64))

    def test_source_target_weight_rewrite_rejected(self):
        self.rejected(lambda d: d["rows"][0]["target_row"].update(weight_units=950))

    def test_listing_history_is_not_claimed_from_current_ref(self):
        self.rejected(lambda d: d["rows"][0].update(dated_listing_identity={"valid_from": "2024-12-31"}))

    def test_mapping_is_not_backdated(self):
        def mutate(d):
            d["mapping_effective_from"] = d["mapping_available_at"] = "2024-12-31T00:00:00+00:00"
        self.rejected(mutate)


if __name__ == "__main__":
    unittest.main()
