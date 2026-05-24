from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generator, Optional, Tuple


@dataclass
class _Node:
    key: Any
    value: Any
    height: int = 1
    left: Optional["_Node"] = None
    right: Optional["_Node"] = None


class AVLTree:
    def __init__(self) -> None:
        self._root: Optional[_Node] = None

    @staticmethod
    def _height(node: Optional[_Node]) -> int:
        return node.height if node else 0

    def _update_height(self, node: _Node) -> None:
        node.height = 1 + max(self._height(node.left), self._height(node.right))

    def _balance_factor(self, node: _Node) -> int:
        return self._height(node.left) - self._height(node.right)

    def _rotate_right(self, y: _Node) -> _Node:
        x = y.left
        assert x is not None
        t2 = x.right

        x.right = y
        y.left = t2

        self._update_height(y)
        self._update_height(x)
        return x

    def _rotate_left(self, x: _Node) -> _Node:
        y = x.right
        assert y is not None
        t2 = y.left

        y.left = x
        x.right = t2

        self._update_height(x)
        self._update_height(y)
        return y

    def _rebalance(self, node: _Node) -> _Node:
        self._update_height(node)
        bf = self._balance_factor(node)

        if bf > 1:
            assert node.left is not None
            if self._balance_factor(node.left) < 0:
                node.left = self._rotate_left(node.left)
            return self._rotate_right(node)

        if bf < -1:
            assert node.right is not None
            if self._balance_factor(node.right) > 0:
                node.right = self._rotate_right(node.right)
            return self._rotate_left(node)

        return node

    def insert(self, key: Any, value: Any) -> None:
        self._root = self._insert(self._root, key, value)

    def _insert(self, node: Optional[_Node], key: Any, value: Any) -> _Node:
        if node is None:
            return _Node(key=key, value=value)
        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            node.value = value
            return node
        return self._rebalance(node)

    def get(self, key: Any) -> Any:
        current = self._root
        while current:
            if key < current.key:
                current = current.left
            elif key > current.key:
                current = current.right
            else:
                return current.value
        return None

    def contains(self, key: Any) -> bool:
        return self.get(key) is not None

    def delete(self, key: Any) -> None:
        self._root = self._delete(self._root, key)

    def _delete(self, node: Optional[_Node], key: Any) -> Optional[_Node]:
        if node is None:
            return None

        if key < node.key:
            node.left = self._delete(node.left, key)
        elif key > node.key:
            node.right = self._delete(node.right, key)
        else:
            if node.left is None:
                return node.right
            if node.right is None:
                return node.left

            successor = self._min_node(node.right)
            node.key, node.value = successor.key, successor.value
            node.right = self._delete(node.right, successor.key)

        return self._rebalance(node)

    def _min_node(self, node: _Node) -> _Node:
        current = node
        while current.left is not None:
            current = current.left
        return current

    def inorder(self, start: Any = None, end: Any = None) -> Generator[Tuple[Any, Any], None, None]:
        yield from self._inorder(self._root, start, end)

    def _inorder(self, node: Optional[_Node], start: Any, end: Any) -> Generator[Tuple[Any, Any], None, None]:
        if node is None:
            return

        if start is None or node.key >= start:
            yield from self._inorder(node.left, start, end)

        in_low = start is None or node.key >= start
        in_high = end is None or node.key <= end
        if in_low and in_high:
            yield (node.key, node.value)

        if end is None or node.key <= end:
            yield from self._inorder(node.right, start, end)
