"""Guides are presentation metadata; Frozen prompt rules and validators stay unchanged."""
import hashlib
import json

from investment_system.prompt_library import fill as fill_module
from investment_system.prompt_library.catalog import load_catalog
from investment_system.prompt_library.ui import JS, catalog_payload


def test_every_active_prompt_variable_has_an_explicit_guide():
    variables = {v["name"] for prompt in catalog_payload(load_catalog())["prompts"] for v in prompt["variables"]}
    assert len(variables) == 34
    guides = getattr(fill_module, "VARIABLE_GUIDES", None)
    assert guides is not None, "UI variable guides have not been implemented"
    assert set(guides) == variables


def test_all_guides_have_complete_korean_and_english_input_help():
    guides = getattr(fill_module, "VARIABLE_GUIDES", {})
    assert len(guides) == 34
    for guide in guides.values():
        assert set(guide) == {"label", "description", "placeholder", "source"}
        for localized in guide.values():
            assert set(localized) == {"ko-KR", "en-US"}
            assert all(isinstance(text, str) and text.strip() for text in localized.values())


def test_embedded_variable_guides_are_explicit_metadata_for_the_declared_variable():
    guides = getattr(fill_module, "VARIABLE_GUIDES", {})
    for prompt in catalog_payload(load_catalog())["prompts"]:
        for variable in prompt["variables"]:
            assert "guide" in variable, "The form payload has no explicit input guide"
            assert variable["guide"] == guides[variable["name"]]


def test_guides_preserve_frozen_bodies_required_kinds_and_owners():
    cat = load_catalog()
    assert cat.sha256 == "f0a6ed9005e22b8fa534d51135cc3e734aa9577150438a35d65823a4c283e68e"
    projection = [
        {"id": prompt["prompt_id"], "body": prompt["body"],
         "variables": [{key: variable[key] for key in ("name", "required", "kind", "owner")}
                       for variable in prompt["variables"]]}
        for prompt in catalog_payload(cat)["prompts"]
    ]
    encoded = json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    assert hashlib.sha256(encoded).hexdigest() == "775961c836ccd8e6e5fce417efd22a44a5400e840f0e1823c13a353b31e79b14"


def test_guide_layer_does_not_modify_the_existing_browser_validator():
    assert hashlib.sha256(JS.encode()).hexdigest() == "f4c053425b5805f516c5a0e25647c63012d475929264705993b8fe9ad7e82602"
