import re
from abc import ABC
from argparse import ArgumentParser, _AppendConstAction, Namespace
from functools import partial
from json import loads
from pathlib import Path
from typing import Iterator, Iterable, List, Type, Callable, Union, Text, Sequence, Any, Optional, Tuple

Test = Path


class Selector(Iterable[Test]):
    base: Iterable[Test]

    def __init__(self) -> None:
        super().__init__()

    def __iter__(self) -> Iterator[Test]:
        for i in self.base:
            if self.check(i):
                yield i
        return

    def check(self, p: Path) -> bool:
        raise NotImplementedError()

    def chain_after(self, g: Iterable[Test]) -> Iterable[Test]:
        self.base = g
        return self


class SimpleSelectorMixin:
    @classmethod
    def action(cls):
        class _Inner(_AppendConstAction):
            def __init__(self, **kwargs) -> None:
                super().__init__(const=None, **kwargs)

            def __call__(self, parser: ArgumentParser, namespace: Namespace, values: Union[Text, Sequence[Any], None],
                         option_string: Optional[Text] = ...) -> None:
                self.const = cls()
                super().__call__(parser, namespace, values, option_string)

        return _Inner


class MatchAnySelector(Selector, SimpleSelectorMixin):
    def __iter__(self) -> Iterator[Test]:
        for i in self.base:
            yield i
            return

    def check(self, p: Path) -> bool:
        return False


class AttributedSelector(Selector, ABC):
    def __init__(self, ap: ArgumentParser) -> None:
        super().__init__()
        self.ap = ap

    @classmethod
    def generate_selector_with_ap(cls, ap: ArgumentParser) -> Callable[[str], Selector]:
        return partial(cls, ap=ap)


class CheckingResultAttributeSelector(AttributedSelector):
    def __init__(self, attribute_query: str, ap: ArgumentParser) -> None:
        super().__init__(ap)

        opts = attribute_query.split('=')
        if len(opts) != 2:
            self.ap.error('{} not a valid attribute')
        attr, value = opts
        if value in ('True', 'true'):
            value = True
        elif value in ('False', 'false'):
            value = False
        elif re.match(r'^\d+$', value) is not None:
            try:
                value = int(value)
            except ValueError:
                pass
        self.attr = attr
        self.value = value

    def check(self, p: Path) -> bool:
        _f = p / 'checking_result.json'
        if _f.exists():
            _d = loads(_f.read_text())
            # todo: nested attribute
            if self.attr in _d and _d[self.attr]:
                return True
        return False


class PrunedBySelector(AttributedSelector):
    def check(self, p: Path) -> bool:
        raise NotImplementedError


def match(output: Path, *selectors: Selector) -> List[Path]:
    g = (m for s in output.glob('seed-tests/seed-test-*') for m in s.glob('mutant-*'))
    for s in selectors:
        g = s.chain_after(g)
    return list(g)


if __name__ == '__main__':
    ap = ArgumentParser(description='Search for specific seed/mutant')

    ap.add_argument('--checking-result-attribute', '-json', dest='selectors',
                    action='append', type=CheckingResultAttributeSelector.generate_selector_with_ap(ap))
    ap.add_argument('--pruned-by', dest='selectors',
                    action='append', type=PrunedBySelector.generate_selector_with_ap(ap))

    ap.add_argument('-one', dest='selectors', action=MatchAnySelector.action())

    ap.add_argument('--output', '-o', required=True)

    args = ap.parse_args()

    print('Selectors: {}'.format(args.selectors))

    print(match(Path(args.output), *args.selectors))
