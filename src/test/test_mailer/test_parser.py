import pytest
from muistoja.mailer.parse import *


@pytest.mark.parametrize('text,expected,default', [
    (
            r"""
             DEFAULT = A
            Test = {
                content: '''\{b\}'''
                subject: a
                from: a.bc
            }
            
            a = {
                content: 
                    '''
\\{a
'''
            from: b
             subject: a
            }
            """,
            {
                'test': MailConfig(sender='a.bc', subject='a', content='{b}'),
                'a': MailConfig(sender='b', subject='a', content=r'\{a')
            },
            'a'
    )
])
def test_parse(text: str, expected: Dict[str, MailConfig], default):
    cfg = parse(text)
    assert cfg == expected
    if default is not None:
        assert cfg[None] == expected[default]
