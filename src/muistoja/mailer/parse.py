import re
from collections import UserDict
from dataclasses import dataclass
from typing import Dict, Mapping


@dataclass(frozen=True)
class MailConfig:
    sender: str
    subject: str
    content: str


class MailMap(UserDict[str, MailConfig]):

    def __init__(self, *, default: MailConfig = None, **items: Dict[str, MailConfig]):
        super(MailMap, self).__init__()
        self.update({k.lower(): v for k, v in items.items()})
        if default is not None:
            self._default = default

    def __missing__(self, key) -> MailConfig:
        if not hasattr(self, '_default'):
            raise KeyError(key)
        return self._default

    def __getitem__(self, item: str) -> MailConfig:
        return super(MailMap, self).__getitem__(item.lower() if item is not None else item)

    def __contains__(self, item: str) -> bool:
        return super(MailMap, self).__contains__(item.lower() if item is not None else None)


DEFAULT = re.compile(r'^\s*?DEFAULT\s*?=\s*?(?P<lang>\w+)\s*?$', re.MULTILINE)
ENTRY = re.compile(r'(?P<lang>\w+(?:-\w+)?)\s*?=\s*?{(?P<value>(?:[^{}]|(?<=\\)[{}])+)}', re.MULTILINE)
FROM = re.compile(r'^\s*?from:\s*?(?P<value>.+?)$', re.MULTILINE)
SUBJECT = re.compile(r'^\s*?subject:\s*?(?P<value>.+?)$', re.MULTILINE)
CONTENT = re.compile(r'^\s*?content:\s*?\'{3}\n?(?P<value>(?:.*?\n?)*?)\'{3}', re.MULTILINE)
VALUE = 'value'
LANG = 'lang'


def strip(_str: str):
    return _str.strip().replace(
        r'\\{', r'\\\{'
    ).replace(
        r'\\}', r'\\\}'
    ).replace(
        r'\{', '{'
    ).replace(
        r'\}', '}'
    ).replace(
        r'\\', '\\'
    )


def read_file(file: str) -> str:
    with open(file, 'r') as f:
        return '\n'.join(f.readlines())


def parse(content: str) -> Mapping[str, MailConfig]:
    try:
        default = DEFAULT.search(content).group(LANG).strip().lower()
    except AttributeError:
        raise SyntaxError('Failed to find default')

    out = dict()
    for m in ENTRY.finditer(content):
        entry = m.group(VALUE)
        lang = m.group(LANG).strip().lower()

        _from = FROM.search(entry).group(VALUE)
        _subject = SUBJECT.search(entry).group(VALUE)
        _content = CONTENT.search(entry).group(VALUE)

        if any(o is None for o in [_from, _subject, _content]):
            raise SyntaxError('Failed to parse')

        out[lang] = MailConfig(
            sender=strip(_from),
            subject=strip(_subject),
            content=strip(_content)
        )
    return MailMap(default=out[default], **out)


def parse_file(file: str) -> Mapping[str, MailConfig]:
    return parse(read_file(file))
