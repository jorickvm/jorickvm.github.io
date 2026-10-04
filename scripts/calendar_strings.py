"""Reader-facing JSON strings embedded in calculator article fragments."""
import json
import re

BLOCK = re.compile(r'<script\b[^>]*\bdata-cal-strings[^>]*>(.*?)</script>', re.DOTALL)
PLURALS = {"zero", "one", "two", "few", "many", "other"}
PLACEHOLDER = re.compile(r"\{\w+\}")

def strings(markup):
    blocks = BLOCK.findall(markup)
    if len(blocks) > 1:
        raise ValueError("expected one calendar string block")
    if not blocks:
        return {}
    data = json.loads(blocks[0])
    if not isinstance(data, dict):
        raise ValueError("calendar strings must be an object")
    for key, value in data.items():
        variants = value.values() if isinstance(value, dict) else [value]
        if isinstance(value, dict) and ("other" not in value or set(value) - PLURALS):
            raise ValueError(f"{key}: invalid plural variants")
        if any(not isinstance(v, str) or not v.strip() for v in variants):
            raise ValueError(f"{key}: expected non-empty prose")
    return data

def prose(markup):
    values = strings(markup).values()
    return [v for value in values for v in (value.values() if isinstance(value, dict) else [value])]

REQUIRED_PLURALS = {
    "ja": {"other"}, "ko": {"other"}, "zh-Hant": {"other"}, "zh-Hans": {"other"},
    "ru": {"one", "few", "many", "other"}, "uk": {"one", "few", "many", "other"},
    "pl": {"one", "few", "many", "other"},
    "fr": {"one", "many", "other"}, "es": {"one", "many", "other"},
    "pt": {"one", "many", "other"},
}

def check(english, translated, locale="en"):
    source, target = strings(english), strings(translated)
    if source.keys() != target.keys():
        raise ValueError("calendar string keys differ from English")
    for key, original in source.items():
        if isinstance(original, dict) or isinstance(target[key], dict):
            required = REQUIRED_PLURALS.get(locale, {"one", "other"})
            if not isinstance(target[key], dict) or not required <= target[key].keys():
                raise ValueError(f"{key}: missing plural variants for {locale}")
        original = original.get("other") if isinstance(original, dict) else original
        value = target[key]
        for variant in (value.values() if isinstance(value, dict) else [value]):
            if sorted(PLACEHOLDER.findall(original)) != sorted(PLACEHOLDER.findall(variant)):
                raise ValueError(f"{key}: calendar placeholders differ from English")
            if sorted(re.findall(r"\d+", original)) != sorted(re.findall(r"\d+", variant)):
                raise ValueError(f"{key}: calendar numbers differ from English")
