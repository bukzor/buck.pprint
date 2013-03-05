Python's standard library contains a pretty print module (`pprint`), but it's
output is in a very odd style.  This project is a fairly straightforward fork
which aim to create output suitable for use in python code with standard
formatting.

I copied both pprint.py and test_pprint.py from the cpython (2.6) code base,
and made the minimal changes to make things work, and all the tests pass. The
result should be equally reliable as the stdlib pprint library.


    >>> example_obj = {1:2, 3:4, 'range':range(3)}
    >>> example_obj['range'].append(range(5))
    >>> example_obj['range'].append(range(20))

    >>> import buck.pprint
    >>> buck.pprint.pprint(example_obj)
    {
        1: 2,
        3: 4,
        'range': [
            0,
            1,
            2,
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        ],
    }

This is how I'd format this object in my own code. Below is the formatting that
the standard pprint gives. I believe you'll agree that it's not a style you've
ever seen in real python code.

    >>> import pprint
    >>> pprint.pprint(example_obj)
    {1: 2,
     3: 4,
     'range': [0,
               1,
               2,
               [0, 1, 2, 3, 4],
               [0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19]]}
