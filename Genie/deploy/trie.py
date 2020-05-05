from typing import List

# todo: change to pygtrie to not rely on two trie packages
from pytrie import SortedTrie

TrieValue = int
Seq = List[TrieValue]


class SeqTrie:
    _trie = SortedTrie()

    def update(self, seq: Seq):
        _k = tuple(seq)
        if not self._trie.has_key(_k):
            self._trie.update({tuple(seq): True})

    def check_seq_valid(self, seq: Seq):
        _k = tuple(seq)
        return self._trie.longest_prefix(_k, None) is None


if __name__ == '__main__':
    t = SeqTrie()

    t.update([1, 2])
    t.update([1, 3])
    t.update([1, 2])
    t.update([1, 4])

    assert t.check_seq_valid([1, 5])
    assert not t.check_seq_valid([1, 2, 3])
