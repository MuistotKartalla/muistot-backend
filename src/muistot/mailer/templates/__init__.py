from enum import Enum
from functools import cache
from html import escape
from importlib.resources import read_text
from typing import Dict


class Templates(Enum):
    TEMPLATE = "zoner_template.html"


class LoginTemplateAttributes(Enum):
    LANGUAGE = "${{LANGUAGE}}"
    SUBJECT = "${{SUBJECT}}"
    TITLE = "${{TITLE}}"
    LINK = "${{LINK}}"
    BUTTON = "${{BUTTON}}"


@cache
def get_template(template: Templates):
    return read_text("muistot.mailer.templates", template.value, encoding="utf8")


def get_filled_template(template: Templates, data: Dict[LoginTemplateAttributes, str]):
    template = get_template(template)
    for k, v in data.items():
        template = template.replace(k.value, escape(v))
    return template


def get_login_template(lang: str, user: str, link: str):
    if lang.lower() == "fi":
        data = {
            LoginTemplateAttributes.LANGUAGE: "fi",
            LoginTemplateAttributes.SUBJECT: "Muistotkartalla Kirjautuminen",
            LoginTemplateAttributes.TITLE: f"Hei {user}! Tässä kirjautumislinkkisi palveluun",
            LoginTemplateAttributes.BUTTON: "Kirjaudu Sisään",
            LoginTemplateAttributes.LINK: link
        }
    else:
        data = {
            LoginTemplateAttributes.LANGUAGE: "en",
            LoginTemplateAttributes.SUBJECT: "Muistotkartalla Login",
            LoginTemplateAttributes.TITLE: f"Hi {user}! Here is your login link",
            LoginTemplateAttributes.BUTTON: "Log In",
            LoginTemplateAttributes.LINK: link
        }
    return get_filled_template(Templates.TEMPLATE, data)
