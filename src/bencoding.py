"""
Grammar describing bencoding in Augmented Backus Naur Form:

<BE>    ::= <DICT> | <LIST> | <STR> | <INT> 

<DICT>  ::= "d" 1 * (<STR> <BE>) "e"

<LIST>  ::= "l" 1 * <BE>         "e"

<STR>   ::= <NUM> ":" n * <CHAR>; where n equals the <NUM>
<CHAR>  ::= %

<INT>   ::= "i"     <SNUM>       "e"
<SNUM>  ::= "-" <NUM> / <NUM>
<NUM>   ::= 1 * <DIGIT>
<DIGIT> ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
"""

from typing import Union, Dict, List

BencodedValue = Union[bytes, int, List['BencodedValue'], Dict[bytes, 'BencodedValue']]

class Decoder:
    """ Class that acts as a bencoding decoder """
    def __init__(self, bencoded_data):
        if not bencoded_data:
            raise ValueError("Empty data provided")
        if not isinstance(bencoded_data, bytes):
            raise TypeError("Given argument is not a bytes object")

        self._data = bencoded_data
        self._index = 0
        self._char = chr(bencoded_data[0])

    @staticmethod
    def decode(bencoded_data) -> BencodedValue:
        """ Decodes file in bencoding format """
        decoder = Decoder(bencoded_data)

        result = decoder._decode_bencode() # pylint: disable=protected-access

        # Ensure we've consumed all data at the top level
        if decoder._char is not None: # pylint: disable=protected-access
            raise ValueError("Extra data found after valid bencoding")

        return result

    def _consume(self, expected_char: str) -> None:
        if self._char == expected_char:
            self._index += 1

            if self._index < len(self._data):
                self._char = chr(self._data[self._index])
            else:
                # We've reached the EOF
                self._char = None
        else:
            raise ValueError(f"Expected '{expected_char}' at position {self._index}, "
                             f"got '{self._char}'")

    # <BE>    ::= <DICT> | <LIST> | <INT> | <STR>
    def _decode_bencode(self) -> BencodedValue:
        value = None

        if self._char == "d":
            value = self._decode_dict()
        elif self._char == "l":
            value = self._decode_list()
        elif self._char == "i":
            value = self._decode_int()
        elif self._char and self._char.isdigit():
            value = self._decode_str()
        else:
            raise ValueError("Given data does not follow bencoding format")

        return value

    # <DICT>  ::= "d" 1 * (<STR> <BE>) "e"
    def _decode_dict(self) -> dict:
        self._consume("d")
        dictionary = {}
        while True:
            if self._char is None:
                raise ValueError("Unexpected end of data while parsing dictionary")

            key = self._decode_str()
            value = self._decode_bencode()

            dictionary[key] = value

            if self._char == "e":
                break
        self._consume("e")
        return dictionary


    # <LIST>  ::= "l" 1 * <BE>         "e"
    def _decode_list(self) -> list:
        self._consume("l")
        b_list = []
        while True:
            if self._char is None:
                raise ValueError("Unexpected end of data while parsing list")

            b_list.append(self._decode_bencode())

            if self._char == "e":
                break
        self._consume("e")
        return b_list

    # <STR>   ::= <NUM> ":" n * <CHAR>; where n equals the <NUM>
    def _decode_str(self) -> bytes:
        num = self._decode_num()
        self._consume(":")

        byte_data = bytearray()
        for _ in range(num):
            byte_val = self._decode_char()
            byte_data.append(byte_val)
        return bytes(byte_data)

    # <CHAR>  ::= % (anything)
    def _decode_char(self) -> bytes:
        byte_val = self._data[self._index]

        # We've got to manually perform the tasks of the _consume method

        self._index += 1
        if self._index < len(self._data):
            self._char = chr(self._data[self._index])
        else:
            # We've reached the EOF
            self._char = None

        return byte_val


    # <INT>   ::= "i"     <SNUM>       "e"
    def _decode_int(self) -> int:
        self._consume("i")
        value = self._decode_snum()
        self._consume("e")
        return value

    # <SNUM>  ::= "-" <NUM> / <NUM>
    def _decode_snum(self) -> int:
        value = None
        if self._char and self._char.isdigit():
            value = self._decode_num()
        elif self._char == "-":
            self._consume("-")
            if self._char == "0":
                raise ValueError("Negative zero not allowed in bencoding")
            value = - self._decode_num()
        else:
            raise ValueError("Given data does not follow bencoding format")
        return value

    # <NUM>   ::= 1 * <DIGIT>
    def _decode_num(self) -> int:
        num = ""
        # Handle leading zeros (invalid in bencoding except for "0")
        if self._char == "0":
            num += str(self._decode_digit())
            if self._char and self._char.isdigit():
                raise ValueError("Leading zeros not allowed in bencoding integers")
        else:
            while self._char and self._char.isdigit():
                num += str(self._decode_digit())

        if not num:
            raise ValueError("Expected at least one digit in the bencoding integer")
        return int(num)

    # <DIGIT> ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
    def _decode_digit(self) -> int:
        for num in range(10):
            if self._char == str(num):
                self._consume(str(num))
                return num
        raise ValueError("Given data does not follow bencoding format")

