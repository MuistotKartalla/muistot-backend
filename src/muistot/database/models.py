from typing import Tuple, Iterable, Any, Union

from pymysql.cursors import DictCursor


class ResultSet:
    """Mapping for results from database

    This will lead to the following behaving correctly:

    >>> result = ResultSet([('column_1', 1), ('column_2', 'b')])
    >>> print([*result])
    [1, 'b']
    >>> print({**result})
    {'column_1': 1, 'column_2': 'b'}
    >>> c1, c2 = result
    >>> print(c1)
    1
    >>> print(c2)
    b
    """

    def __init__(self, items: Iterable[Tuple[str, Any]]):
        super(ResultSet, self).__init__()
        self.dict = dict()
        self.list = list()
        for k, v in items:
            self.dict[k] = v
            self.list.append(v)

    def __getitem__(self, item: Union[str, int]):
        """Maps item to a value

        - Integer access means positional access [0,len(result)[
        - Str is viewed as a column key
        """
        if isinstance(item, int):
            return self.list[item]
        else:
            return self.dict[item]

    def __iter__(self):
        """Return all values from result
        """
        return self.list.__iter__()

    def __len__(self) -> int:
        """Results length e.i. number of columns
        """
        return len(self.dict)

    def __repr__(self):
        """Dict.__repr__
        """
        return self.dict.__repr__()

    def __str__(self):
        """Dict.__str__
        """
        return self.dict.__str__()

    def __contains__(self, item):
        """Checks for value in result values
        """
        return item in self.list

    def keys(self):
        """Returns a view of result columns
        """
        return self.dict.keys()


class ResultSetCursor(DictCursor):
    """Custom cursor for using ResultSet results
    """
    dict_type = ResultSet
