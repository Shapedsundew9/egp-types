"""Common functions for EGP types."""
from random import choice, randint, uniform
from string import ascii_letters

from .egp_typing import EndPointType

from .ep_type import asint, ep_type_lookup, inst


def random_constant_str(typ: EndPointType) -> str:
    """Return a random constant string."""
    if typ == asint("bool"):
        return choice(("True", "False"))
    if typ == asint("int"):
        return str(randint(-100, 100))
    if typ == asint("float"):
        return str(uniform(-100, 100))
    if typ == asint("str"):
        return '"' + "".join(choice(ascii_letters) for _ in range(randint(1, 10))) + '"'
    return ep_type_lookup["instanciation"][typ][inst.DEFAULT.value]
